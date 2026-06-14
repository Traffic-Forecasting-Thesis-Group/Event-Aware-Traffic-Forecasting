"""
TomTom Flow Segment Data collector.

Polls the TomTom Traffic Flow Segment Data API for each segment in
segments.py and appends one row per segment per run to
data/raw/tomtom_traffic.csv.

Run this on a schedule (every 5 minutes) via Windows Task Scheduler
or cron. Each run makes exactly len(SEGMENTS) API calls.

Usage (one-shot, for testing):
    python collect_tomtom.py

Scheduled usage (Windows Task Scheduler):
    Program: C:\\path\\to\\.venv\\Scripts\\python.exe
    Arguments: C:\\path\\to\\backend\\app\\training\\collect_tomtom.py
    Trigger: every 5 minutes
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from segments import SEGMENTS

# ---- Configuration ----------------------------------------------------
# Set this via environment variable, do NOT hardcode your key in source.
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "")
TOMTOM_BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "tomtom_traffic.csv"

CSV_COLUMNS = [
    "Timestamp",
    "Node",
    "Speed",
    "Flow",
    "free_flow_speed",
    "confidence",
    "road_closure",
]


def fetch_segment(client: httpx.Client, lat: float, lon: float) -> dict | None:
    """Call TomTom Flow Segment Data API for a single point.

    Returns the relevant fields, or None on failure.
    """
    params = {
        "point": f"{lat},{lon}",
        "key": TOMTOM_API_KEY,
        "unit": "KMPH",
    }
    try:
        response = client.get(TOMTOM_BASE_URL, params=params, timeout=20.0)
        response.raise_for_status()
    except Exception as exc:
        print(f"[collect_tomtom] request failed for ({lat},{lon}): {exc}")
        return None

    try:
        payload = response.json()
        data = payload["flowSegmentData"]
    except Exception as exc:
        print(f"[collect_tomtom] bad payload for ({lat},{lon}): {exc}")
        return None

    return {
        "current_speed": data.get("currentSpeed"),
        "free_flow_speed": data.get("freeFlowSpeed"),
        "confidence": data.get("confidence"),
        "road_closure": data.get("roadClosure", False),
    }


def estimate_flow(current_speed: float | None, free_flow_speed: float | None) -> float:
    """Proxy 'flow' metric since the free tier has no direct flow/volume field.

    We derive a congestion ratio: 1.0 = free flow (no congestion),
    0.0 = fully stopped. This is NOT a true vehicle-flow count, but
    gives D2STGNN a second informative channel correlated with demand.
    """
    if not current_speed or not free_flow_speed or free_flow_speed == 0:
        return 0.0
    ratio = current_speed / free_flow_speed
    return max(0.0, min(1.0, ratio))


def main() -> None:
    if not TOMTOM_API_KEY:
        raise SystemExit(
            "TOMTOM_API_KEY environment variable is not set. "
            "Set it before running this script."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = OUTPUT_FILE.exists()

    timestamp = datetime.now(timezone.utc).isoformat()

    rows = []
    with httpx.Client() as client:
        for seg in SEGMENTS:
            result = fetch_segment(client, seg["lat"], seg["lon"])
            if result is None:
                # Skip this segment this round; do not write a bad row.
                continue

            current_speed = result["current_speed"]
            free_flow_speed = result["free_flow_speed"]
            flow_proxy = estimate_flow(current_speed, free_flow_speed)

            rows.append({
                "Timestamp": timestamp,
                "Node": seg["id"],
                "Speed": current_speed if current_speed is not None else "",
                "Flow": flow_proxy,
                "free_flow_speed": free_flow_speed if free_flow_speed is not None else "",
                "confidence": result["confidence"] if result["confidence"] is not None else "",
                "road_closure": result["road_closure"],
            })

    if not rows:
        print("[collect_tomtom] no rows collected this run.")
        return

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"[collect_tomtom] wrote {len(rows)} rows at {timestamp}")


if __name__ == "__main__":
    main()
