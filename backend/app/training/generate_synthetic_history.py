"""
Generate a synthetic historical traffic CSV for the 5 EDSA/Roxas
segments, matching the exact column format produced by
collect_tomtom.py (Timestamp, Node, Speed, Flow, free_flow_speed,
confidence, road_closure).

WHY THIS EXISTS:
TomTom's free-tier Flow Segment Data API only returns the CURRENT
traffic state -- there is no historical bulk download. To actually
exercise build_dataset.py and train.py (and produce a real trained
checkpoint with a real loss curve) before enough live data has been
collected, this script generates plausible synthetic time series with:
  - Daily rush-hour congestion patterns (two dips in speed: AM and PM
    rush hours), realistic for EDSA/Roxas corridors.
  - Weekday vs weekend differences (weekends have lighter traffic).
  - Random noise so the model has something non-trivial to learn.
  - A few random "incident" dips (sudden severe slowdowns) to mimic
    accidents/closures, paired with synthetic incident records.

THIS IS CLEARLY SYNTHETIC DATA FOR PIPELINE/TRAINING-FLOW VALIDATION
ONLY. It should be replaced with real collected TomTom data as soon as
enough history accumulates (see collect_tomtom.py + Task Scheduler).
Disclose this in any presentation/report.

Usage:
    python generate_synthetic_history.py --days 14
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from segments import SEGMENTS, NODE_IDS

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
TRAFFIC_OUTPUT = OUTPUT_DIR / "tomtom_traffic_synthetic.csv"
INCIDENTS_OUTPUT = OUTPUT_DIR / "tomtom_incidents_synthetic.jsonl"

CSV_COLUMNS = [
    "Timestamp",
    "Node",
    "Speed",
    "Flow",
    "free_flow_speed",
    "confidence",
    "road_closure",
]

RESAMPLE_MINUTES = 5

# Free-flow speed per segment (kph). EDSA segments are generally
# faster (wider road) than Roxas Blvd segments in this toy model.
FREE_FLOW_SPEED = {
    "seg_01": 60.0,  # EDSA - North Ave / Munoz
    "seg_02": 55.0,  # EDSA - Ortigas Ave Jct
    "seg_03": 50.0,  # EDSA - Taft Ave / Pasay
    "seg_04": 45.0,  # Roxas Blvd - Manila Bay
    "seg_05": 45.0,  # Roxas Blvd - Macapagal Jct
}

# Random seed for reproducibility
random.seed(42)


def congestion_factor(hour: float, is_weekend: bool) -> float:
    """Return a value in [0, 1] where 1 = free flow, 0 = gridlock.

    Two congestion troughs on weekdays: AM rush (~7-9) and PM rush
    (~17-20). Weekends have a single, milder midday dip.
    """
    if not is_weekend:
        am_dip = math.exp(-((hour - 8.0) ** 2) / (2 * 1.2 ** 2))
        pm_dip = math.exp(-((hour - 18.5) ** 2) / (2 * 1.5 ** 2))
        dip = max(am_dip, pm_dip)
        factor = 1.0 - 0.65 * dip
    else:
        midday_dip = math.exp(-((hour - 14.0) ** 2) / (2 * 3.0 ** 2))
        factor = 1.0 - 0.25 * midday_dip

    return max(0.15, min(1.0, factor))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14, help="Number of days of synthetic history to generate")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    end_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end_time -= timedelta(minutes=end_time.minute % RESAMPLE_MINUTES)
    start_time = end_time - timedelta(days=args.days)

    num_steps = int((end_time - start_time).total_seconds() // (RESAMPLE_MINUTES * 60))

    # Pick a few random incident windows (sudden speed drops)
    incident_windows = []
    for _ in range(max(1, args.days // 3)):
        offset_steps = random.randint(0, num_steps - 1)
        duration_steps = random.randint(2, 6)  # 10-30 min
        seg = random.choice(NODE_IDS)
        incident_windows.append((offset_steps, offset_steps + duration_steps, seg))

    rows = []
    incident_records = []

    for step in range(num_steps + 1):
        ts = start_time + timedelta(minutes=RESAMPLE_MINUTES * step)
        hour = ts.hour + ts.minute / 60.0
        is_weekend = ts.weekday() >= 5

        for seg in SEGMENTS:
            node_id = seg["id"]
            ffs = FREE_FLOW_SPEED[node_id]

            factor = congestion_factor(hour, is_weekend)

            # Apply incident dip if this segment/time falls in a window
            for (w_start, w_end, w_seg) in incident_windows:
                if w_seg == node_id and w_start <= step < w_end:
                    factor *= 0.35  # severe slowdown
                    if step == w_start:
                        incident_records.append({
                            "source": "synthetic_incident",
                            "title": "ACCIDENT",
                            "text": f"Synthetic accident causing severe slowdown near {seg['name']}",
                            "published_at": ts.isoformat(),
                            "location": seg["name"],
                            "keywords": ["accident", "collision"],
                            "traffic_related": True,
                            "embedding_text": f"ACCIDENT Synthetic accident causing severe slowdown near {seg['name']}",
                            "geometry": None,
                            "start_time": ts.isoformat(),
                            "end_time": (ts + timedelta(minutes=RESAMPLE_MINUTES * (w_end - w_start))).isoformat(),
                            "collected_at": ts.isoformat(),
                        })

            # Add gaussian noise (+/- ~5% of free flow speed)
            noise = random.gauss(0, 0.05 * ffs)
            current_speed = max(3.0, ffs * factor + noise)

            flow_proxy = max(0.0, min(1.0, current_speed / ffs))

            rows.append({
                "Timestamp": ts.isoformat(),
                "Node": node_id,
                "Speed": round(current_speed, 2),
                "Flow": round(flow_proxy, 4),
                "free_flow_speed": ffs,
                "confidence": 1.0,
                "road_closure": False,
            })

    with open(TRAFFIC_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with open(INCIDENTS_OUTPUT, "w", encoding="utf-8") as f:
        for rec in incident_records:
            f.write(json.dumps(rec) + "\n")

    print(f"[generate_synthetic_history] wrote {len(rows)} rows "
          f"({num_steps + 1} timesteps x {len(SEGMENTS)} segments) to {TRAFFIC_OUTPUT}")
    print(f"[generate_synthetic_history] wrote {len(incident_records)} synthetic incidents to {INCIDENTS_OUTPUT}")
    print(f"[generate_synthetic_history] time range: {start_time.isoformat()} to {end_time.isoformat()}")


if __name__ == "__main__":
    main()
