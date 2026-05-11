#!/usr/bin/env python3
"""
Fetch recent X posts using the same approach as the reference test script.

Usage:
    python ml/scripts/test_x_fetch_posts.py

Notes:
- Requires X_BEARER_TOKEN in backend/.env or environment.
- Uses X Recent Search endpoint and writes CSV output.
- Output files include timestamp: x_recent_posts_translated_YYYYMMDD_HHMM.csv
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
# Minimal Tagalog/Taglish detection helpers
FILIPINO_MARKERS = {
    "ako",
    "ka",
    "ko",
    "mo",
    "siya",
    "kami",
    "tayo",
    "kayo",
    "sila",
    "ng",
    "nang",
    "sa",
    "ang",
    "mga",
    "ito",
    "yan",
    "yun",
    "hindi",
    "di",
    "wala",
    "may",
    "sana",
    "kasi",
    "pero",
    "lang",
    "rin",
    "din",
    "naman",
    "pa",
    "na",
    "ba",
    "po",
    "grabe",
    "sobrang",
    "bakit",
    "paano",
    "saan",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", str(text).lower())


def is_tagalog_like(text: str, lang_field: str) -> bool:
    if str(lang_field).lower() == "tl":
        return True
    tokens = tokenize(text)
    filipino_count = sum(1 for t in tokens if t in FILIPINO_MARKERS)
    return filipino_count >= 2

from pathlib import Path
import sys

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / "backend" / ".env"

# Load env from backend/.env if present.
load_dotenv(dotenv_path=ENV_PATH, override=False)

BEARER_TOKEN = os.getenv("X_BEARER_TOKEN") or os.getenv("TWARC_BEARER_TOKEN")
if not BEARER_TOKEN:
    raise ValueError("Missing X_BEARER_TOKEN or TWARC_BEARER_TOKEN in env or backend/.env")

OUTPUT_DIR = BASE_DIR / "ml" / "outputs" / "x_fetch"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Generate timestamp for filenames (YYYYMMDD_HHMM format)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M")

RAW_OUTPUT = OUTPUT_DIR / f"x_recent_posts_{TIMESTAMP}.csv"
TRANSLATED_OUTPUT = OUTPUT_DIR / f"x_recent_posts_translated_{TIMESTAMP}.csv"
TRAIN_JSONL_OUTPUT = OUTPUT_DIR / f"x_train_taglish_en_{TIMESTAMP}.jsonl"

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

MAX_TOTAL_RETURNED_POSTS = 100
MAX_RESULTS_PER_REQUEST = 100
REQUEST_SLEEP_SECONDS = 2

DEFAULT_QUERY = "(traffic OR accident OR flood OR road closed OR reroute OR MMDA) (Manila OR \"Metro Manila\" OR EDSA OR C5) lang:en"
QUERY = os.getenv("X_SEARCH_QUERY", DEFAULT_QUERY)

# Optional: provide multiple queries via X_SEARCH_QUERY_LIST (semicolon-separated)
# to avoid X API rule length limits (512 chars per query).
QUERY_LIST_ENV = os.getenv("X_SEARCH_QUERY_LIST", "")
QUERY_LIST = [q.strip() for q in QUERY_LIST_ENV.split(";") if q.strip()]

if not QUERY_LIST:
    if len(QUERY) > 512:
        print("Warning: X_SEARCH_QUERY exceeds 512 chars; using fallback queries.")
        QUERY_LIST = [
            "(MMDA OR #mmda OR @MMDA) lang:en",
            "(traffic OR accident OR flood OR road closed OR reroute) (Manila OR \"Metro Manila\" OR EDSA OR C5) lang:en",
        ]
    else:
        QUERY_LIST = [QUERY]

# Optional translation (Tagalog/Taglish -> English)
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
try:
    from app.preprocessing.taglish_translator import TaglishTranslator

    TRANSLATOR = TaglishTranslator()
except Exception:
    TRANSLATOR = None


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}


def fetch_recent_posts() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    total_saved = 0
    for query in QUERY_LIST:
        if total_saved >= MAX_TOTAL_RETURNED_POSTS:
            break

        print(f"\nQuery: {query}")
        next_token: str | None = None

        while total_saved < MAX_TOTAL_RETURNED_POSTS:
            remaining = MAX_TOTAL_RETURNED_POSTS - total_saved
            if remaining < 10:
                print("Remaining budget below 10; stopping to avoid invalid max_results.")
                break
            params = {
                "query": query,
                "max_results": min(MAX_RESULTS_PER_REQUEST, remaining),
                "tweet.fields": "created_at,lang",
            }
            if next_token:
                params["next_token"] = next_token

            response = requests.get(SEARCH_URL, headers=headers(), params=params, timeout=30)

            if response.status_code == 429:
                print("Rate limit hit. Sleeping for 15 minutes.")
                time.sleep(15 * 60)
                continue

            if response.status_code != 200:
                print(f"Request failed: {response.status_code}")
                print(response.text)
                # Skip to the next query on invalid request (e.g., rule length).
                break

            payload = response.json()
            data = payload.get("data", [])
            meta = payload.get("meta", {})

            if not data:
                print("No posts returned.")
                break

            for post in data:
                post_id = str(post.get("id", ""))
                if not post_id or post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                rows.append(
                    {
                        "x_post_id": post_id,
                        "created_at": post.get("created_at", ""),
                        "lang": post.get("lang", ""),
                        "raw_text": post.get("text", ""),
                    }
                )
                total_saved += 1

            print(f"Returned: {len(data)} | Saved: {total_saved}/{MAX_TOTAL_RETURNED_POSTS}")

            next_token = meta.get("next_token")
            if not next_token:
                break

            time.sleep(REQUEST_SLEEP_SECONDS)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["x_post_id", "raw_text"])
        df.to_csv(RAW_OUTPUT, index=False, encoding="utf-8-sig")
        print(f"Saved: {RAW_OUTPUT}")
        
        # Translate Tagalog/Taglish posts when translator is available.
        if TRANSLATOR is not None:
            translate_mask = df.apply(
                lambda row: is_tagalog_like(row.get("raw_text", ""), row.get("lang", "")),
                axis=1,
            )
            translate_texts = df.loc[translate_mask, "raw_text"].tolist()
            translated = []
            if translate_texts:
                translated = TRANSLATOR.translate_texts(translate_texts, use_ner=True)

            df["translated_text"] = ""
            if translated:
                df.loc[translate_mask, "translated_text"] = translated

            df.to_csv(TRANSLATED_OUTPUT, index=False, encoding="utf-8-sig")
            print(f"Saved: {TRANSLATED_OUTPUT}")

            # Export JSONL for Colab fine-tuning (Taglish/Tagalog -> English)
            train_rows = []
            for _, row in df[translate_mask].iterrows():
                src = str(row.get("raw_text", "")).strip()
                tgt = str(row.get("translated_text", "")).strip()
                if src and tgt:
                    train_rows.append({"tl": src, "en": tgt})

            if train_rows:
                pd.DataFrame(train_rows).to_json(
                    TRAIN_JSONL_OUTPUT,
                    orient="records",
                    lines=True,
                    force_ascii=False,
                )
                print(f"Saved: {TRAIN_JSONL_OUTPUT}")
    else:
        print("No posts saved.")

    return df


if __name__ == "__main__":
    fetch_recent_posts()
