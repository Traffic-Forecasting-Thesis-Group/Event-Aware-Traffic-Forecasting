#!/usr/bin/env python3
"""Create a high-confidence binary-labeled batch from multi-source posts.

This is a bootstrap helper, not a replacement for manual annotation.
It only labels rows with high-confidence patterns and leaves the rest unlabeled.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


MMDA_EVENT_TERMS = [
    "mmda alert",
    "road crash",
    "multiple collision",
    "collision",
    "stalled",
    "lane occupied",
    "managing traffic",
    "flood",
    "rallyist",
    "rally",
    "road closure",
]

NOISE_TERMS = [
    "what about",
    "why",
    "i'm waiting",
    "im waiting",
    "stuck for hours",
]

GDELT_RELIABLE_TERMS = [
    "roads closed",
    "road closed",
    "traffic",
    "accident",
    "collision",
    "flood",
    "rally",
    "protest",
    "transport strike",
]

PH_LOC_TERMS = [
    "metro manila",
    "manila",
    "quezon city",
    "edsa",
    "makati",
    "pasig",
    "taguig",
    "ncr",
]


def has_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def bootstrap_label(row: pd.Series) -> tuple[object, str]:
    text = str(row.get("raw_text", "") or "")
    source = str(row.get("source_type", "") or "").lower()
    lower = text.lower()

    if source == "social_media":
        if has_any(lower, MMDA_EVENT_TERMS):
            return 1, "auto: mmda/event signal"
        if "?" in text or has_any(lower, NOISE_TERMS):
            return 0, "auto: question/subjective noise"
        return pd.NA, ""

    if source == "gdelt":
        if has_any(lower, GDELT_RELIABLE_TERMS) and has_any(lower, PH_LOC_TERMS):
            return 1, "auto: gdelt traffic/event + PH location"
        if has_any(lower, ["web traffic", "history", "church", "signature drive", "asean summit"]):
            return 0, "auto: gdelt non-traffic context"
        return pd.NA, ""

    if source == "news_api":
        if has_any(lower, GDELT_RELIABLE_TERMS) and has_any(lower, PH_LOC_TERMS):
            return 1, "auto: news event + PH location"
        return pd.NA, ""

    return pd.NA, ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap high-confidence binary labels")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", default="", help="Output CSV path")
    parser.add_argument("--annotator", default="auto_bootstrap", help="Annotator name")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    df = pd.read_csv(in_path)

    if "x_post_id" in df.columns and "post_id" not in df.columns:
        df = df.rename(columns={"x_post_id": "post_id"})

    for col in ["post_id", "created_at", "raw_text", "source_type"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    for col, default in [
        ("translated_text", ""),
        ("reliability_label", pd.NA),
        ("annotator_name", ""),
        ("annotation_time", pd.NA),
        ("notes", ""),
    ]:
        if col not in df.columns:
            df[col] = default

    # Ensure writable dtypes for metadata columns that may be inferred as float.
    df["annotator_name"] = df["annotator_name"].fillna("").astype(str)
    df["annotation_time"] = df["annotation_time"].fillna("").astype(str)
    df["notes"] = df["notes"].fillna("").astype(str)

    already_labeled = pd.to_numeric(df["reliability_label"], errors="coerce").notna()
    now = datetime.now().isoformat(timespec="seconds")

    auto_labeled = 0
    for idx, row in df[~already_labeled].iterrows():
        label, note = bootstrap_label(row)
        if pd.isna(label):
            continue
        df.loc[idx, "reliability_label"] = int(label)
        df.loc[idx, "annotator_name"] = args.annotator
        df.loc[idx, "annotation_time"] = now
        df.loc[idx, "notes"] = note
        auto_labeled += 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path("ml/data") / f"x_labeled_batch_{timestamp}_{args.annotator}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    labeled = pd.to_numeric(df["reliability_label"], errors="coerce").notna()
    print(f"Saved: {out_path}")
    print(f"Rows total: {len(df)}")
    print(f"Rows auto-labeled this run: {auto_labeled}")
    print(f"Rows labeled overall: {int(labeled.sum())}")
    print(f"Reliable (1): {int((pd.to_numeric(df['reliability_label'], errors='coerce') == 1).sum())}")
    print(f"Unreliable (0): {int((pd.to_numeric(df['reliability_label'], errors='coerce') == 0).sum())}")


if __name__ == "__main__":
    main()
