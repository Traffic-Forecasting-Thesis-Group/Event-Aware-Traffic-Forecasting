from __future__ import annotations

from .ingestion import normalize_event


def ingest_unstructured_events(raw_events: list[dict]) -> dict:
    """Normalize and store event payloads for the fusion pipeline."""
    return {
        "count": len(raw_events),
        "events": [normalize_event(item) for item in raw_events],
    }
