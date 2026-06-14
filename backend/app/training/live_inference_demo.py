"""
Live inference demo — D2STGNN with full unstructured event fusion.

Pipeline:
  1. Fetch live TomTom traffic data for all 5 EDSA/Roxas segments
  2. Fetch + NLP-score unstructured events (RSS/GDELT/X via IngestionService,
     or from a hardcoded sample list if live sources are unavailable)
  3. Encode scored events → [1, E, C] embedding tensor via fusion.py
  4. Run D2STGNN forward() with real event_embeddings (not None)
  5. Print forecast table with event context

Usage:
    # Default — uses hardcoded sample events (no extra API keys needed):
    python live_inference_demo.py

    # With live event sources (requires RSS/GDELT/X keys in .env):
    python live_inference_demo.py --live-events

    # Explicitly use sample events:
    python live_inference_demo.py --sample-events
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import torch

# ---------------------------------------------------------------------------
# Path setup — must happen before any app.* imports
# ---------------------------------------------------------------------------
TRAINING_DIR = Path(__file__).resolve().parent          # backend/app/training
BACKEND_DIR  = TRAINING_DIR.parents[1]                  # backend/
APP_DIR      = TRAINING_DIR.parent                      # backend/app/
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(TRAINING_DIR))

from app.d2stgnn_external import D2STGNN                # noqa: E402
from app.fusion import encode_events_to_embeddings      # noqa: E402
from app.event_pipeline import (                        # noqa: E402
    fetch_and_score_events,
    run_live_event_pipeline,
)
from segments import SEGMENTS, NODE_IDS, NUM_NODES      # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ARTIFACT_DIR    = TRAINING_DIR.parents[2] / "artifacts" / "model_registry"
PROCESSED_DIR   = TRAINING_DIR.parents[2] / "data" / "processed"
CHECKPOINT_PATH = ARTIFACT_DIR / "d2stgnn_tomtom_best.pt"

# ---------------------------------------------------------------------------
# TomTom
# ---------------------------------------------------------------------------
TOMTOM_API_KEY  = os.environ.get("TOMTOM_API_KEY", "")
TOMTOM_BASE_URL = (
    "https://api.tomtom.com/traffic/services/4"
    "/flowSegmentData/absolute/10/json"
)

SEQ_LENGTH    = 12
NUM_FEAT_TOTAL = 6
DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------------------------------------------------------------------
# Sample events for demo mode (no extra API keys needed)
# ---------------------------------------------------------------------------
_SAMPLE_EVENTS = [
    {
        "source": "mmda_twitter",
        "title": "MMDA Traffic Alert",
        "text": (
            "Heavy traffic along EDSA Ortigas due to stalled vehicle. "
            "Expect delays."
        ),
        "location": "EDSA-Ortigas",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "keywords": ["heavy traffic", "stalled", "EDSA", "Ortigas"],
    },
    {
        "source": "rappler_rss",
        "title": "Flash floods reported near Roxas Boulevard",
        "text": (
            "Flood waters rising along Roxas Boulevard near CCP complex "
            "due to heavy rainfall."
        ),
        "location": "Roxas Boulevard",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "keywords": ["flood", "roxas", "rainfall", "CCP"],
    },
    {
        "source": "gdelt",
        "title": "Road closure EDSA Taft",
        "text": (
            "MMDA implements road closure on EDSA Taft Avenue section "
            "for emergency repair."
        ),
        "location": "EDSA-Taft",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "keywords": ["road closure", "EDSA", "Taft", "MMDA"],
    },
]


# ---------------------------------------------------------------------------
# TomTom fetch
# ---------------------------------------------------------------------------

def fetch_live_segment(
    client: httpx.Client, lat: float, lon: float
) -> dict | None:
    params = {
        "point": f"{lat},{lon}",
        "key": TOMTOM_API_KEY,
        "unit": "KMPH",
    }
    try:
        response = client.get(TOMTOM_BASE_URL, params=params, timeout=20.0)
        response.raise_for_status()
        data = response.json()["flowSegmentData"]
        return {
            "current_speed":   data.get("currentSpeed"),
            "free_flow_speed": data.get("freeFlowSpeed"),
            "road_closure":    data.get("roadClosure", False),
        }
    except Exception as exc:
        print(f"  [warn] fetch failed for ({lat},{lon}): {exc}")
        return None


def load_norm_stats() -> dict:
    path = PROCESSED_DIR / "norm_stats.json"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run build_dataset.py first.")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live D2STGNN inference with NLP event fusion"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--live-events", action="store_true",
        help="Fetch live events from RSS/GDELT/X (requires .env API keys)",
    )
    group.add_argument(
        "--sample-events", action="store_true",
        help="Use hardcoded sample events (no API keys needed, good for demo)",
    )
    args = parser.parse_args()

    # Default to sample events when neither flag is given
    use_live = args.live_events

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    if not TOMTOM_API_KEY:
        raise SystemExit("TOMTOM_API_KEY environment variable is not set.")
    if not CHECKPOINT_PATH.exists():
        raise SystemExit(
            f"Missing checkpoint: {CHECKPOINT_PATH}. Run train.py first."
        )

    # ------------------------------------------------------------------
    # Load model
    # ------------------------------------------------------------------
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
    model_args = checkpoint["model_args"]
    num_nodes  = checkpoint["num_nodes"]

    adj_path = PROCESSED_DIR / "adj_mx.npy"
    adj      = torch.tensor(np.load(adj_path), dtype=torch.float32).to(DEVICE)
    adjs     = [adj for _ in range(model_args["k_s"])]

    model = D2STGNN(num_nodes=num_nodes, adjs=adjs, **model_args).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    norm_stats = load_norm_stats()
    speed_mean = norm_stats["speed"]["mean"]
    speed_std  = norm_stats["speed"]["std"]
    flow_mean  = norm_stats["flow"]["mean"]
    flow_std   = norm_stats["flow"]["std"]

    # ------------------------------------------------------------------
    # Step 1 — Fetch live TomTom data
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    tod = (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0
    dow = now.weekday() / 7.0

    print(f"\n[live_inference_demo] fetching live TomTom data at {now.isoformat()}...")
    rows = np.zeros((NUM_NODES, NUM_FEAT_TOTAL), dtype=np.float32)

    with httpx.Client() as client:
        for i, seg in enumerate(SEGMENTS):
            live = fetch_live_segment(client, seg["lat"], seg["lon"])
            if live is None or live["current_speed"] is None:
                print(f"  {seg['name']}: NO DATA (using 0)")
                speed_raw, flow_raw, valid = 0.0, 0.0, 0.0
            else:
                speed_raw = float(live["current_speed"])
                ffs       = live["free_flow_speed"] or 1.0
                flow_raw  = max(0.0, min(1.0, speed_raw / ffs))
                valid     = 1.0
                closure   = " [ROAD CLOSED]" if live.get("road_closure") else ""
                print(
                    f"  {seg['name']}: speed={speed_raw:.1f} kph, "
                    f"free_flow={ffs:.1f} kph{closure}"
                )

            rows[i, 0] = (speed_raw - speed_mean) / speed_std
            rows[i, 1] = (flow_raw  - flow_mean)  / flow_std
            rows[i, 2] = 0.0    # density placeholder
            rows[i, 3] = valid
            rows[i, 4] = tod
            rows[i, 5] = dow

    # Build [1, seq_length, N, 6] by repeating the single live snapshot
    history        = np.tile(rows[np.newaxis, np.newaxis, :, :], (1, SEQ_LENGTH, 1, 1))
    history_tensor = torch.tensor(history, dtype=torch.float32).to(DEVICE)
    future_tensor  = torch.zeros_like(history_tensor)

    # ------------------------------------------------------------------
    # Step 2 — Fetch + NLP-score unstructured events
    # ------------------------------------------------------------------
    print("\n[live_inference_demo] loading unstructured events...")

    if use_live:
        print("  fetching from live sources (RSS/GDELT/X)...")
        try:
            # run_live_event_pipeline returns already-normalized+scored events.
            # We pass them directly — fetch_and_score_events detects pre-scored
            # events and skips re-normalization to avoid the double-scoring bug.
            scored_events = asyncio.run(run_live_event_pipeline(limit_per_source=10))
            if not scored_events:
                print("  [warn] no events from live sources, falling back to sample events.")
                scored_events = fetch_and_score_events(_SAMPLE_EVENTS)
        except Exception as exc:
            print(f"  [warn] live event fetch failed: {exc}. Falling back to sample events.")
            scored_events = fetch_and_score_events(_SAMPLE_EVENTS)
    else:
        print("  (using hardcoded sample events — run with --live-events for real sources)")
        scored_events = fetch_and_score_events(_SAMPLE_EVENTS)

    print(f"  {len(scored_events)} traffic-relevant events (trust >= 0.5):")
    for ev in scored_events[:5]:
        print(
            f"    [{ev.get('nlp_stage', '?'):>20}] "
            f"trust={ev.get('trust_score', 0):.2f} | "
            f"{ev.get('event_type', '?'):>15} | "
            f"{ev['embedding_text'][:60]}"
        )
    if not scored_events:
        print(
            "  (no traffic events found — "
            "model will use learnable fallback embeddings)"
        )

    # ------------------------------------------------------------------
    # Step 3 — Encode events → [1, E, C] embedding tensor
    # ------------------------------------------------------------------
    # c_dim must match D2STGNN._c_dim:
    #   _forecast_dim (256) * gap * seq_length
    c_dim = 256 * model_args["gap"] * model_args["seq_length"]

    event_emb_np     = encode_events_to_embeddings(
        scored_events, c_dim=c_dim, max_events=384
    )
    event_emb_tensor = torch.tensor(
        event_emb_np, dtype=torch.float32
    ).to(DEVICE)

    print(
        f"\n[live_inference_demo] event embedding tensor: "
        f"{list(event_emb_tensor.shape)}  (c_dim={c_dim})"
    )

    # ------------------------------------------------------------------
    # Step 4 — Model forward pass WITH event embeddings
    # ------------------------------------------------------------------
    with torch.no_grad():
        forecast = model(
            history_data=history_tensor,
            future_data=future_tensor,
            batch_seen=0,
            epoch=0,
            train=False,
            event_embeddings=event_emb_tensor,   # ← real NLP-scored embeddings
        )

    # forecast: [1, seq_length, N, 1], normalized speed
    forecast_np  = forecast.squeeze(0).squeeze(-1).cpu().numpy()  # [seq_length, N]
    forecast_kph = forecast_np * speed_std + speed_mean

    # ------------------------------------------------------------------
    # Step 5 — Print results
    # ------------------------------------------------------------------
    header = " | ".join(f"{s['name'][:18]:>18}" for s in SEGMENTS)
    print(f"\n[live_inference_demo] forecast (denormalized speed, kph):")
    print(f"{'step':>6} | {header}")
    for step in range(forecast_kph.shape[0]):
        row = forecast_kph[step]
        vals = " | ".join(f"{v:>18.2f}" for v in row)
        print(f"{step + 1:>6} | {vals}")

    print(
        f"\n[live_inference_demo] fusion active: "
        f"{len(scored_events)} events → CrossModal attention applied inside D2STGNN"
    )
    print(
        f"[live_inference_demo] checkpoint: "
        f"epoch {checkpoint['epoch']}, val_mae={checkpoint['val_mae']:.4f}"
    )


if __name__ == "__main__":
    main()
