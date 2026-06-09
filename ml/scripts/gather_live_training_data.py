#!/usr/bin/env python3
"""Collect live training data from the backend ingestion pipeline.

This script pulls the configured unstructured sources, applies the existing
cleaning + translation pipeline, and writes a CSV that is ready for annotation
or model training.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path
import sys

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

from app.ingestion.service import IngestionService


async def collect_rows(limit_per_source: int) -> pd.DataFrame:
    service = IngestionService()
    collected = await service.collect_unstructured(limit_per_source=limit_per_source)
    cleaned = await service.preprocess_texts(collected.items)

    rows: list[dict[str, object]] = []
    for item in cleaned:
        rows.append(
            {
                "source": item.source,
                "original_text": item.original_text,
                "cleaned_text": item.cleaned_text,
                "translated_text": item.translated_text,
                "location_hint": item.location_hint,
                "language_hint": item.language_hint,
                "timestamp": item.timestamp.isoformat(),
            }
        )

    return pd.DataFrame(rows)


def build_output_path(output: str | None) -> Path:
    if output:
        return Path(output)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Path("ml/data") / f"x_live_ingestion_{stamp}.csv"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Collect live training data from backend ingestion")
    parser.add_argument("--limit-per-source", type=int, default=25, help="Rows to collect from each source")
    parser.add_argument("--output", help="Output CSV path")
    args = parser.parse_args()

    frame = await collect_rows(args.limit_per_source)
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
