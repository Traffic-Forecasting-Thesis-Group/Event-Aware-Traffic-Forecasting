"""
TomTom Traffic Incidents collector.

Polls the TomTom Traffic Incidents API for a bounding box covering all
segments in segments.py, and appends normalized incident records to
data/raw/tomtom_incidents.jsonl (one JSON object per line).

These records feed into app/fusion.py's encode_events_to_embeddings(),
matching the same shape (title/text/keywords/traffic_related/embedding_text)
already produced by app/ingestion.py's normalize_event().

"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from segments import SEGMENTS

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "")
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "tomtom_incidents.jsonl"

# Padding (degrees) around segment points to build a bounding box.
# ~0.05 deg ~= 5.5km, generous enough to cover EDSA corridor segments.
BBOX_PADDING = 0.05

_TRAFFIC_KEYWORDS = {
    "ACCIDENT": ["accident", "collision", "crash"],
    "ROAD_CLOSED": ["road closure", "closure", "closed"],
    "ROAD_WORKS": ["construction", "roadwork", "road works"],
    "JAM": ["traffic", "congestion", "jam"],
    "FLOODING": ["flood", "flooding"],
    "DANGEROUS_CONDITIONS": ["hazard", "dangerous"],
    "LANE_RESTRICTION": ["lane closure", "lane restriction"],
}


def compute_bbox() -> str:
    lats = [s["lat"] for s in SEGMENTS]
    lons = [s["lon"] for s in SEGMENTS]
    min_lat, max_lat = min(lats) - BBOX_PADDING, max(lats) + BBOX_PADDING
    min_lon, max_lon = min(lons) - BBOX_PADDING, max(lons) + BBOX_PADDING
    # TomTom expects: minLon,minLat,maxLon,maxLat
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


def incident_category_to_keywords(category: str) -> list[str]:
    return _TRAFFIC_KEYWORDS.get(category, [category.lower().replace("_", " ")])


def main() -> None:
    if not TOMTOM_API_KEY:
        raise SystemExit("TOMTOM_API_KEY environment variable is not set.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    params = {
        "key": TOMTOM_API_KEY,
        "bbox": compute_bbox(),
        "fields": "{incidents{type,geometry{type,coordinates},properties{iconCategory,events{description,code,iconCategory},startTime,endTime}}}",
        "language": "en-GB",
    }

    with httpx.Client() as client:
        try:
            response = client.get(TOMTOM_INCIDENTS_URL, params=params, timeout=20.0)
            response.raise_for_status()
        except Exception as exc:
            print(f"[collect_tomtom_incidents] request failed: {exc}")
            return

        try:
            payload = response.json()
        except Exception as exc:
            print(f"[collect_tomtom_incidents] bad payload: {exc}")
            return

    incidents = payload.get("incidents", [])
    now = datetime.now(timezone.utc).isoformat()

    written = 0
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for inc in incidents:
            props = inc.get("properties", {})
            events = props.get("events", [])
            descriptions = [e.get("description", "") for e in events if e.get("description")]
            category = str(props.get("iconCategory", "UNKNOWN"))
            text = "; ".join(descriptions) if descriptions else category

            record = {
                "source": "tomtom_incidents",
                "title": category,
                "text": text,
                "published_at": props.get("startTime") or now,
                "location": "",
                "keywords": incident_category_to_keywords(category),
                "traffic_related": True,
                "embedding_text": f"{category} {text}".strip(),
                "geometry": inc.get("geometry"),
                "start_time": props.get("startTime"),
                "end_time": props.get("endTime"),
                "collected_at": now,
            }
            f.write(json.dumps(record) + "\n")
            written += 1

    print(f"[collect_tomtom_incidents] wrote {written} incidents at {now}")


if __name__ == "__main__":
    main()
