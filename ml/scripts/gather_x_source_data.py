#!/usr/bin/env python3
"""Collect live X search data for the traffic training set.

This script uses the existing XSearchAdapter with the expanded Metro Manila
transport / LGU query and writes a CSV that can be labeled or merged into the
training workflow.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path
import sys

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
from app.ingestion.adapters import XSearchAdapter


async def fetch_x_rows(limit: int) -> pd.DataFrame:
    settings = get_settings()
    if not settings.x_bearer_token:
        raise RuntimeError("X_BEARER_TOKEN is not set in backend/.env")

    adapter = XSearchAdapter(
        api_url=settings.x_search_api_url,
        bearer_token=settings.x_bearer_token,
        query=settings.x_search_query,
    )

    async with httpx.AsyncClient(timeout=settings.source_timeout_seconds) as client:
        items = await adapter.fetch(client, limit=limit)

    rows: list[dict[str, object]] = []
    for item in items:
        rows.append(
            {
                "source": item.source,
                "text": item.text,
                "location_hint": item.location_hint,
                "timestamp": item.timestamp.isoformat(),
            }
        )

    return pd.DataFrame(rows)


def build_output_path(output: str | None) -> Path:
    if output:
        return Path(output)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Path("ml/data") / f"x_live_source_{stamp}.csv"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Collect live X source data for training")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of posts to fetch")
    parser.add_argument("--output", help="Output CSV path")
    args = parser.parse_args()

    frame = await fetch_x_rows(args.limit)
    output_path = build_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    print(f"saved={output_path}")
    print(f"total_items={len(frame)}")
    if not frame.empty and "source" in frame.columns:
        print("by_source=")
        print(frame["source"].value_counts().to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
