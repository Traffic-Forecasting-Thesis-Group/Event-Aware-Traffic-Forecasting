"""
event_pipeline.py — Unstructured event ingestion + NLP scoring pipeline.

Wires together:
  1. Raw event dicts (from GDELT, RSS, X/Twitter, MMDA)
  2. TransformerTieredNLPFilter (DistilBERT → RoBERTa) for trust scoring
  3. Output: list of fusion-ready event dicts for encode_events_to_embeddings()

Usage (standalone / from live_inference_demo.py):
    from app.event_pipeline import fetch_and_score_events
    events = fetch_and_score_events(raw_events)

Or to pull live events from RSS/GDELT/X and score them:
    from app.event_pipeline import run_live_event_pipeline
    import asyncio
    events = asyncio.run(run_live_event_pipeline())
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Traffic keyword lists (mirrors fusion.py vocab for consistency)
# ---------------------------------------------------------------------------
_TRAFFIC_KEYWORDS = [
    "traffic", "congestion", "road", "jam", "flood", "accident",
    "delay", "closure", "incident", "construction", "rally", "protest",
    "rain", "typhoon", "storm", "signal", "detour", "edsa",
    "roxas", "mmda", "ambulance", "fire", "emergency", "slow", "heavy",
    "bangga", "baha", "sarado", "trapik",  # Tagalog traffic terms
]


def _is_traffic_related(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in _TRAFFIC_KEYWORDS)


def _clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[@#][\w_]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw event dict into the canonical fusion schema."""
    title = str(raw.get("title") or "")
    text = str(raw.get("text") or raw.get("content") or "")
    embedding_text = _clean_text(f"{title} {text}")
    keywords = list(raw.get("keywords") or [])
    source = str(raw.get("source") or "unknown").lower()
    location = str(raw.get("location") or raw.get("location_hint") or "")
    published_at = raw.get("published_at") or raw.get("timestamp")

    try:
        if isinstance(published_at, str):
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            published_at = dt.astimezone(timezone.utc).isoformat()
        elif isinstance(published_at, datetime):
            published_at = published_at.astimezone(timezone.utc).isoformat()
        else:
            published_at = datetime.now(timezone.utc).isoformat()
    except Exception:
        published_at = datetime.now(timezone.utc).isoformat()

    traffic_related = _is_traffic_related(embedding_text + " " + " ".join(keywords))

    return {
        "source": source,
        "title": title,
        "text": text,
        "embedding_text": embedding_text,
        "keywords": keywords,
        "location": location,
        "published_at": published_at,
        "traffic_related": bool(traffic_related),
        "trust_score": None,  # filled in by NLP scoring step
    }


# ---------------------------------------------------------------------------
# NLP scoring — uses TransformerTieredNLPFilter when available,
# falls back to keyword heuristic so the pipeline never crashes
# ---------------------------------------------------------------------------

def _heuristic_trust_score(text: str) -> float:
    """Keyword-based trust score fallback (no model required)."""
    strong = ["accident", "bangga", "collision", "crash", "pileup", "sarado"]
    medium = ["traffic", "roadblock", "flood", "stalled", "gridlock", "trapik"]
    lowered = text.lower()
    if any(t in lowered for t in strong):
        return 0.9
    if any(t in lowered for t in medium):
        return 0.75
    return 0.2


async def _score_with_nlp_filter(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Score events using TransformerTieredNLPFilter (DistilBERT → RoBERTa).
    Falls back to heuristic scoring if the NLP models are unavailable
    (e.g. not downloaded yet, or running offline).
    """
    try:
        from app.nlp.service import TransformerTieredNLPFilter
        from app.schemas.ingestion import CleanedTextItem

        nlp_filter = TransformerTieredNLPFilter()

        cleaned_items = [
            CleanedTextItem(
                source=ev["source"],
                original_text=ev["text"],
                cleaned_text=ev["embedding_text"],
                translated_text=None,
                location_hint=ev["location"] or None,
                language_hint="taglish",
                timestamp=datetime.fromisoformat(ev["published_at"]),
            )
            for ev in events
        ]

        decisions = await nlp_filter.verify_batch(cleaned_items)

        scored = []
        for ev, decision in zip(events, decisions):
            ev = dict(ev)
            if decision.signal is not None:
                ev["trust_score"] = float(decision.signal.trust_score)
                ev["nlp_stage"] = decision.stage
                ev["event_type"] = decision.signal.event
            else:
                ev["trust_score"] = _heuristic_trust_score(ev["embedding_text"])
                ev["nlp_stage"] = "heuristic_fallback"
                ev["event_type"] = "Unknown"
            scored.append(ev)

        return scored

    except Exception as exc:
        logger.warning(
            f"[event_pipeline] NLP filter unavailable ({exc}), "
            "using heuristic trust scores."
        )
        scored = []
        for ev in events:
            ev = dict(ev)
            ev["trust_score"] = _heuristic_trust_score(ev["embedding_text"])
            ev["nlp_stage"] = "heuristic_fallback"
            ev["event_type"] = "Unknown"
            scored.append(ev)
        return scored


def _run_async_safe(coro) -> Any:
    """
    Run an async coroutine safely regardless of whether there is already
    a running event loop (e.g. inside FastAPI / Celery / Jupyter).

    - Synchronous scripts (live_inference_demo.py): asyncio.run() is used.
    - Already-running loop (FastAPI route, Celery, Jupyter):
      a new thread is spun up so the coroutine runs in a fresh loop,
      avoiding 'This event loop is already running' RuntimeError.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # No running loop — safe to call asyncio.run() directly
        return asyncio.run(coro)

    # There IS a running loop (FastAPI/Celery/Jupyter).
    # Run in a separate thread with its own event loop.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def fetch_and_score_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize + NLP-score a list of raw event dicts.

    Safe to call from both synchronous scripts and async contexts
    (FastAPI routes, Celery workers, Jupyter notebooks).

    Args:
        raw_events: list of raw dicts from GDELT, RSS, X, MMDA, etc.
                    Also accepts already-scored dicts (trust_score present)
                    without re-processing them.

    Returns:
        Filtered, scored list ready for encode_events_to_embeddings(),
        containing only traffic-related events with trust_score >= 0.5.
    """
    if not raw_events:
        return []

    # If events are already fully scored (from run_live_event_pipeline),
    # skip normalization + re-scoring and go straight to filtering.
    already_scored = all(
        ev.get("trust_score") is not None and ev.get("embedding_text") is not None
        for ev in raw_events
    )

    if already_scored:
        filtered = [
            ev for ev in raw_events
            if ev.get("traffic_related") and (ev.get("trust_score") or 0.0) >= 0.5
        ]
        logger.info(
            f"[event_pipeline] {len(raw_events)} pre-scored events → "
            f"{len(filtered)} traffic-relevant (trust>=0.5)"
        )
        return filtered

    # Fresh raw events — normalize then score
    normalized = [_normalize_event(ev) for ev in raw_events]
    scored = _run_async_safe(_score_with_nlp_filter(normalized))

    filtered = [
        ev for ev in scored
        if ev.get("traffic_related") and (ev.get("trust_score") or 0.0) >= 0.5
    ]

    logger.info(
        f"[event_pipeline] {len(raw_events)} raw → "
        f"{len(normalized)} normalized → "
        f"{len(filtered)} traffic-relevant (trust>=0.5)"
    )
    return filtered


async def run_live_event_pipeline(limit_per_source: int = 10) -> list[dict[str, Any]]:
    """
    Pull live events from all configured sources (RSS, GDELT, X, MMDA),
    normalize, translate, and NLP-score them.

    Returns fusion-ready filtered events (trust_score already set).
    Requires API keys to be configured in .env.
    Falls back gracefully if sources are unavailable.
    """
    try:
        from app.ingestion.service import IngestionService

        service = IngestionService()
        collection = await service.collect_unstructured(limit_per_source=limit_per_source)
        cleaned = await service.preprocess_texts(collection.items)

        raw_events = [
            {
                "source": item.source,
                "title": "",
                "text": item.cleaned_text,
                "location": item.location_hint or "",
                "published_at": item.timestamp.isoformat(),
                "keywords": [],
            }
            for item in cleaned
        ]

        # Normalize + score (raw_events have no trust_score yet)
        normalized = [_normalize_event(ev) for ev in raw_events]
        scored = await _score_with_nlp_filter(normalized)

        filtered = [
            ev for ev in scored
            if ev.get("traffic_related") and (ev.get("trust_score") or 0.0) >= 0.5
        ]

        logger.info(
            f"[event_pipeline] live pipeline: {len(collection.items)} collected → "
            f"{len(filtered)} traffic-relevant (trust>=0.5)"
        )
        return filtered

    except Exception as exc:
        logger.warning(
            f"[event_pipeline] Live collection failed: {exc}. "
            "Returning empty event list."
        )
        return []


def ingest_unstructured_events(raw_events: list[dict]) -> dict:
    """
    Normalize and score raw events. Returns fusion-ready payload.
    Backward-compatible shim for main.py /api/events/ingest endpoint.
    """
    scored = fetch_and_score_events(raw_events)
    return {
        "count": len(scored),
        "events": scored,
    }
