import importlib.util
import os

# Import ingestion.py (the file) directly, bypassing the ingestion/ folder package
_spec = importlib.util.spec_from_file_location(
    "ingestion_module",
    os.path.join(os.path.dirname(__file__), "..", "app", "ingestion.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
normalize_event = _mod.normalize_event


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
    assert "flood" in event["embedding_text"].lower()


def test_normalize_event_non_traffic():
    raw = {
        "source": "news_api",
        "title": "Local festival in Quezon City",
        "text": "A community event was held at the barangay hall.",
        "published_at": "2026-06-12T10:00:00+08:00",
        "location": "",
        "keywords": [],
    }
    event = normalize_event(raw)
    assert event["traffic_related"] is False
    assert event["source"] == "news_api"


def test_normalize_event_missing_fields():
    event = normalize_event({})
    assert event["source"] == "unknown"
    assert event["traffic_related"] is False
    assert event["embedding_text"] == ""
