#!/usr/bin/env python3
"""Collect major Metro Manila event data for DistilBERT/RoBERTa training.

This collector focuses on positive, high-signal event posts only. It pulls from
News API, GDELT, and the configured X sources for MMDA / DPWH / Metro Manila LGUs,
then keeps only rows that match major-event heuristics for traffic disruptions,
road closures, accidents, rallies, mall events, concerts, political events, and
holidays in Metro Manila.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterable

import httpx
import pandas as pd

BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(BACKEND_PATH / ".env")

from app.core.config import get_settings
from app.ingestion.adapters import GDELTAdapter, MMDAAdapter, NewsAPIAdapter, XSearchAdapter
from app.ingestion.service import IngestionService


METRO_MANILA_TERMS = [
    "metro manila",
    "ncr",
    "manila",
    "quezon city",
    "qc",
    "makati",
    "pasig",
    "taguig",
    "caloocan",
    "valenzuela",
    "navotas",
    "malabon",
    "muntinlupa",
    "paranaque",
    "parañaque",
    "pasay",
    "san juan",
    "mandaluyong",
    "marikina",
    "pateros",
    "edsa",
    "c5",
    "commonwealth",
    "ortigas",
    "slex",
    "nlex",
    "skyway",
    "taft",
    "espana",
    "españa",
    "roxas boulevard",
    "bgc",
    "bonifacio global city",
    "araneta",
    "smart araneta",
    "mall of asia arena",
    "moa arena",
    "philippine arena",
    "sm mall of asia",
    "glorietta",
    "greenbelt",
    "trinoma",
    "sm megamall",
    "festival mall",
]

MAJOR_EVENT_RULES: list[tuple[str, list[str]]] = [
    (
        "traffic / road incident",
        [
            "accident",
            "collision",
            "crash",
            "hit-and-run",
            "stalled",
            "breakdown",
            "road closure",
            "road closed",
            "lane closure",
            "roadwork",
            "construction",
            "reroute",
            "congestion",
            "gridlock",
            "baha",
            "flooding",
            "traffic advisory",
            "traffic alert",
            "road crash",
            "road incident",
            "blocked",
            "one lane occupied",
            "lane occupied",
            "traffic advisory",
        ],
    ),
    (
        "rally / protest",
        [
            "rally",
            "protest",
            "strike",
            "parade",
            "procession",
            "motorcade",
            "march",
            "demonstration",
            "mass action",
        ],
    ),
    (
        "mall event",
        [
            "mall sale",
            "grand sale",
            "clearance sale",
            "sale event",
            "mall event",
            "bazaar",
            "promo",
            "opening",
            "launch",
        ],
    ),
    (
        "concert / arena event",
        [
            "concert",
            "arena concert",
            "show",
            "gig",
            "live performance",
            "music festival",
        ],
    ),
    (
        "political event",
        [
            "political",
            "campaign rally",
            "debate",
            "miting de avance",
            "proclamation",
            "election",
            "canvassing",
            "forum",
        ],
    ),
    (
        "holiday / long weekend",
        [
            "holiday",
            "long weekend",
            "holy week",
            "christmas",
            "new year",
            "new year's",
            "undas",
            "all saints",
            "all souls",
            "easter",
            "labor day",
            "bonifacio day",
            "independence day",
        ],
    ),
    (
        "weather / flood alert",
        [
            "flood alert",
            "flood advisory",
            "flood warning",
            "heavy rain",
            "rainfall",
            "rain advisory",
            "rain warning",
            "habagat",
            "weather alert",
            "weather advisory",
            "thunderstorm",
            "typhoon",
            "storm",
        ],
    ),
]

X_TARGET_USERNAMES = [
    "MMDA",
    "DPWHph",
    "PNP_HPG",
    "PIOCaloocan",
    "CaloocanCityLGU",
    "Malabon_City",
    "Navotas_City",
    "valenzuelacity",
    "QCGov",
    "sanjuancityncr",
    "officialmunti",
    "ILoveParanaque",
    "PasayPIO",
]

X_FLOOD_QUERY = (
    '(flood OR baha OR rainfall OR rain OR ulan OR habagat OR "weather alert" OR '
    '"weather advisory" OR "flood alert" OR "flood warning" OR thunderstorm OR typhoon) '
    '("Metro Manila" OR NCR OR Manila OR EDSA OR "Quezon City" OR Makati OR Pasig OR '
    'Taguig OR Marikina OR Navotas OR Malabon OR Muntinlupa OR Parañaque OR Pasay OR '
    'San Juan OR Caloocan OR Valenzuela) lang:en -is:retweet'
)


def build_x_query_for_handle(handle: str) -> str:
    handle = handle.lstrip("@")
    return (
        f"(from:{handle} OR @{handle}) "
        "(traffic OR accident OR flood OR congestion OR collision OR road closure OR roadwork OR "
        "construction OR reroute OR advisory OR warning OR suspended OR cancelled OR class suspension OR "
        "heavy rain OR baha OR stranded OR evacuation) "
        "lang:en -is:retweet"
    )


def has_metro_manila_context(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in METRO_MANILA_TERMS)


def classify_major_event(text: str) -> tuple[str | None, str | None]:
    lowered = text.lower()
    for category, terms in MAJOR_EVENT_RULES:
        for term in terms:
            if term in lowered:
                return category, term

    return None, None


async def fetch_news_rows(settings, limit: int) -> pd.DataFrame:
    news_query = settings.news_api_query or "traffic OR accident OR flood OR road closure"
    queries = [
        news_query,
        '("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati) AND (rally OR protest OR strike OR parade OR procession OR political OR election)',
        '("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati) AND (concert OR "mall sale" OR "mall event" OR "arena concert" OR sale OR promo)',
        '("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati) AND (holiday OR "long weekend" OR "holy week" OR christmas OR new year)',
    ]
    domains = ",".join(
        [
            "abs-cbn.com",
            "news.abs-cbn.com",
            "tv5.com.ph",
            "news.tv5.com.ph",
            "mb.com.ph",
            "philstar.com",
            "onenews.ph",
            "gmanetwork.com",
            "inquirer.net",
            "rappler.com",
        ]
    )

    results: list[dict[str, object]] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            params = {
                "q": query,
                "sortBy": "publishedAt",
                "pageSize": str(min(limit, 100)),
                "apiKey": settings.news_api_key,
                "language": "en",
                "searchIn": "title,description,content",
            }
            domain_params = {**params, "domains": domains}
            response = await client.get(settings.news_api_url, params=domain_params)
            if response.status_code == 400:
                response = await client.get(settings.news_api_url, params=params)
            if response.status_code == 429:
                response = await client.get(settings.news_api_url, params=params)
            if response.status_code == 401:
                break
            response.raise_for_status()
            payload = response.json()
            results.extend(payload.get("articles", []))

    seen_urls: set[str] = set()
    rows: list[dict[str, object]] = []
    for article in results:
        url = str(article.get("url", ""))
        if url in seen_urls:
            continue
        seen_urls.add(url)

        source_name = str(article.get("source", {}).get("name", "news_api"))
        title = str(article.get("title", "")).strip()
        description = str(article.get("description", "")).strip()
        content = str(article.get("content", "")).strip()
        text = " ".join(part for part in [title, description, content] if part).strip()
        category, keyword = classify_major_event(text)
        if not category or not has_metro_manila_context(text):
            continue

        rows.append(
            {
                "post_id": f"news_api_{len(rows)}",
                "created_at": article.get("publishedAt", datetime.now().isoformat()),
                "source_type": "news_api",
                "source_name": source_name,
                "raw_text": f"[{source_name}] {text}",
                "source_url": url,
                "major_event_type": category,
                "major_event_flag": 1,
                "major_event_keyword": keyword,
            }
        )

    return pd.DataFrame(rows)


async def fetch_gdelt_rows(settings, limit: int, timespan: str) -> pd.DataFrame:
    queries = [
        '(traffic OR accident OR flood OR congestion OR collision OR rally OR protest OR concert OR holiday OR sale OR political) ("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati OR Pasig OR Taguig) sourcelang:English',
        '("road closure" OR roadwork OR construction OR reroute OR stalled OR breakdown OR parade OR procession OR motorcade) ("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati OR Pasig OR Taguig) sourcelang:English',
    ]

    results: list[dict[str, object]] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            params = {
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": str(min(limit, 250)),
                "sort": "DateDesc",
                "timespan": timespan,
            }
            if settings.gdelt_api_key:
                params["key"] = settings.gdelt_api_key

            response = None
            for attempt in range(1, 4):
                response = await client.get(settings.gdelt_api_url, params=params)
                if response.status_code != 429:
                    break
                if attempt < 3:
                    await asyncio.sleep(6)

            if response is None or response.status_code == 429:
                continue

            response.raise_for_status()
            payload = response.json()
            results.extend(payload.get("articles", []))

    seen_keys: set[tuple[str, str]] = set()
    rows: list[dict[str, object]] = []
    for article in results:
        title = str(article.get("title", "")).strip()
        url = str(article.get("url", "")).strip()
        if not title:
            continue
        key = (title, url)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        text = f"[GDELT] {title}"
        if url:
            text = f"{text} (Source: {url})"
        category, keyword = classify_major_event(text)
        if not category or not has_metro_manila_context(text):
            continue

        rows.append(
            {
                "post_id": f"gdelt_{len(rows)}",
                "created_at": article.get("seendate") or article.get("pubdate") or article.get("datetime") or datetime.now().isoformat(),
                "source_type": "gdelt",
                "source_name": "gdelt",
                "raw_text": text,
                "source_url": url,
                "major_event_type": category,
                "major_event_flag": 1,
                "major_event_keyword": keyword,
            }
        )

    return pd.DataFrame(rows)


async def _twitter_json(client: httpx.AsyncClient, url: str, headers: dict[str, str], params: dict[str, str] | None = None) -> dict[str, object] | None:
    response = None
    for attempt in range(1, 4):
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 429:
            break
        if attempt < 3:
            await asyncio.sleep(6)

    if response is None or response.status_code in {401, 403, 404, 429}:
        return None

    response.raise_for_status()
    return response.json()


async def fetch_x_rows(service: IngestionService, limit: int) -> pd.DataFrame:
    settings = service.settings
    if not settings.x_bearer_token:
        return pd.DataFrame()

    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    rows: list[dict[str, object]] = []

    async with httpx.AsyncClient(timeout=settings.source_timeout_seconds) as client:
        query_jobs = [(handle, build_x_query_for_handle(handle)) for handle in X_TARGET_USERNAMES]
        query_jobs.append(("x_flood_search", X_FLOOD_QUERY))

        for source_name, query in query_jobs:
            search_adapter = XSearchAdapter(
                api_url=settings.x_search_api_url,
                bearer_token=settings.x_bearer_token,
                query=query,
            )
            search_items = await search_adapter.fetch(client, limit)

            for item in search_items[:limit]:
                base_text = item.text
                category, keyword = classify_major_event(base_text)
                if not category or not has_metro_manila_context(base_text):
                    continue

                rows.append(
                    {
                        "post_id": f"{source_name}_{len(rows)}",
                        "created_at": item.timestamp.isoformat(),
                        "source_type": "x_search",
                        "source_name": source_name,
                        "source_handle": source_name if source_name != "x_flood_search" else "",
                        "raw_text": item.text,
                        "major_event_type": category,
                        "major_event_flag": 1,
                        "major_event_keyword": keyword,
                    }
                )

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    if "created_at" in frame.columns:
        frame = frame.sort_values("created_at", ascending=False).reset_index(drop=True)
    return frame


def normalize_frames(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]
    if not non_empty:
        return pd.DataFrame()

    combined = pd.concat(non_empty, ignore_index=True)
    if "source_type" in combined.columns and "raw_text" in combined.columns:
        combined = combined.drop_duplicates(subset=["source_type", "raw_text"], keep="first")

    if "created_at" in combined.columns:
        combined = combined.sort_values("created_at", ascending=False).reset_index(drop=True)

    return combined


def build_output_path(output: str | None) -> Path:
    if output:
        return Path(output)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Path("ml/data") / f"major_event_training_{stamp}.csv"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Collect major Metro Manila event data for training")
    parser.add_argument("--limit-per-source", type=int, default=50, help="Maximum rows to fetch per source")
    parser.add_argument(
        "--sources",
        default="news,gdelt,x",
        help="Comma-separated sources to collect: news,gdelt,x",
    )
    parser.add_argument(
        "--gdelt-timespan",
        default=os.getenv("GDELT_TIMESPAN", "30d"),
        help="GDELT lookback window, for example 7d or 30d",
    )
    parser.add_argument("--output", help="Output CSV path")
    args = parser.parse_args()

    settings = get_settings()
    service = IngestionService()

    requested_sources = {source.strip().lower() for source in args.sources.split(",") if source.strip()}

    news_df = await fetch_news_rows(settings, args.limit_per_source) if "news" in requested_sources else pd.DataFrame()
    gdelt_df = await fetch_gdelt_rows(settings, args.limit_per_source, args.gdelt_timespan) if "gdelt" in requested_sources else pd.DataFrame()
    x_df = await fetch_x_rows(service, args.limit_per_source) if "x" in requested_sources else pd.DataFrame()

    frame = normalize_frames([news_df, gdelt_df, x_df])
    output_path = build_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    print(f"saved={output_path}")
    print(f"total_items={len(frame)}")
    if not frame.empty and "source_type" in frame.columns:
        print("by_source=")
        print(frame["source_type"].value_counts().to_string())
    if not frame.empty and "major_event_type" in frame.columns:
        print("by_major_event_type=")
        print(frame["major_event_type"].value_counts().to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))