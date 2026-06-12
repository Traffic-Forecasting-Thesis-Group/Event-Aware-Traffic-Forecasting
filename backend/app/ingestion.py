from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw event record into the canonical traffic-event schema."""
    text = " ".join([str(raw_event.get("title", "")), str(raw_event.get("text", ""))]).strip()
    source = str(raw_event.get("source", "unknown")).lower()
    location = str(raw_event.get("location") or "")
    published_at = raw_event.get("published_at")

    try:
        if isinstance(published_at, str):
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            published_at = dt.astimezone(timezone.utc).isoformat()
    except Exception:
        published_at = str(published_at) if published_at is not None else None

    traffic_related = any(keyword in text.lower() for keyword in ("traffic", "congestion", "road", "jam", "flood", "accident", "delay"))

    return {
        "source": source,
        "title": raw_event.get("title", ""),
        "text": raw_event.get("text", ""),
        "published_at": published_at,
        "location": location,
        "keywords": list(raw_event.get("keywords", []) or []),
        "traffic_related": bool(traffic_related),
        "embedding_text": text,
    }
