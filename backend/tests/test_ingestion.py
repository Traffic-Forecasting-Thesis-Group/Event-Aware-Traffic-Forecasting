from backend.app.ingestion import normalize_event


def test_normalize_event_creates_canonical_fields():
    raw = {
        "source": "gdelt",
        "title": "Flooding causes traffic delays on EDSA",
        "text": "Heavy rain led to severe congestion near EDSA and Roxas Boulevard.",
        "published_at": "2026-06-12T08:30:00+08:00",
        "location": "EDSA, Manila",
        "keywords": ["flood", "traffic", "EDSA"],
    }

    event = normalize_event(raw)

    assert event["source"] == "gdelt"
    assert event["title"] == raw["title"]
    assert event["location"] == "EDSA, Manila"
    assert event["traffic_related"] is True
    assert event["embedding_text"].lower().find("flood") >= 0
