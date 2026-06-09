from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


POSITIVE_TERMS = {
    "accident", "collision", "crash", "stalled", "breakdown", "road closure",
    "lane closure", "lane occupied", "traffic advisory", "traffic alert", "gridlock",
    "congestion", "flood", "baha", "habagat", "heavy rain", "typhoon", "storm",
    "reroute", "blocked", "road work", "roadwork", "construction", "flyover"
}

NEGATIVE_TERMS = {
    "senate", "impeachment", "election", "campaign", "church", "opinion",
    "concert ticket", "internet traffic", "sports fest", "animal shelter"
}

PH_LOCATION_TERMS = {
    "metro manila", "manila", "quezon city", "edsa", "c5", "commonwealth",
    "katipunan", "ortigas", "guadalupe", "pasay", "makati", "taguig", "navotas",
    "valenzuela", "san juan", "caloocan", "muntinlupa"
}


def _has_any(text: str, terms: set[str]) -> bool:
    return any(t in text for t in terms)


def _label_text(text: str, source_type: str) -> tuple[object, object, str]:
    lower = (text or "").lower()

    if _has_any(lower, POSITIVE_TERMS):
        if source_type in {"social_media", "gdelt", "news_api", "inquirer"}:
            if _has_any(lower, PH_LOCATION_TERMS) or source_type in {"social_media", "inquirer"}:
                return 1, 1, "auto: traffic/event signal"

    if _has_any(lower, NEGATIVE_TERMS) and not _has_any(lower, POSITIVE_TERMS):
        return 0, 0, "auto: non-traffic context"

    return pd.NA, pd.NA, ""


def _normalize_x_live_ingestion(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["post_id"] = [f"xlive_{i}" for i in range(len(df))]
    out["created_at"] = df.get("timestamp", pd.NA)
    out["lang"] = "en"
    out["raw_text"] = df.get("original_text", "")
    out["translated_text"] = df.get("cleaned_text", "")
    out["source_type"] = df.get("source", "").astype(str).str.lower()
    out["source_file"] = path.name
    out["event_label"] = pd.NA
    out["reliability_label"] = pd.NA
    out["annotator_name"] = ""
    out["annotation_time"] = pd.NA
    out["notes"] = ""
    return out


def _normalize_check_gdelt_news(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["post_id"] = df.get("post_id")
    out["created_at"] = df.get("created_at")
    out["lang"] = df.get("lang", "en")
    out["raw_text"] = df.get("raw_text", "")
    out["translated_text"] = df.get("translated_text", "")
    out["source_type"] = df.get("source_type", "gdelt")
    out["source_file"] = path.name
    out["event_label"] = pd.NA
    out["reliability_label"] = pd.to_numeric(df.get("reliability_label", pd.NA), errors="coerce")
    out["annotator_name"] = df.get("annotator_name", "").fillna("")
    out["annotation_time"] = df.get("annotation_time", pd.NA)
    out["notes"] = df.get("notes", "").fillna("")
    return out


def _normalize_x_multi_source(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["post_id"] = df.get("post_id")
    out["created_at"] = df.get("created_at")
    out["lang"] = df.get("lang", "en")
    out["raw_text"] = df.get("raw_text", "")
    out["translated_text"] = df.get("translated_text", "")
    out["source_type"] = df.get("source_type", "")
    out["source_file"] = df.get("source_file", path.name).fillna(path.name)
    out["event_label"] = pd.NA
    out["reliability_label"] = pd.to_numeric(df.get("reliability_label", pd.NA), errors="coerce")
    out["annotator_name"] = df.get("annotator_name", "").fillna("")
    out["annotation_time"] = df.get("annotation_time", pd.NA)
    out["notes"] = df.get("notes", "").fillna("")
    return out


def _auto_label(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now().isoformat(timespec="seconds")
    unlabeled_mask = pd.to_numeric(df["reliability_label"], errors="coerce").isna()

    for idx, row in df[unlabeled_mask].iterrows():
        text = str(row.get("raw_text") or row.get("translated_text") or "")
        source_type = str(row.get("source_type") or "").lower()
        event_label, reliability_label, note = _label_text(text, source_type)
        if pd.isna(reliability_label):
            continue
        df.at[idx, "event_label"] = event_label
        df.at[idx, "reliability_label"] = reliability_label
        df.at[idx, "annotator_name"] = "auto_pool_labeler"
        df.at[idx, "annotation_time"] = now
        df.at[idx, "notes"] = note

    labeled_mask = pd.to_numeric(df["reliability_label"], errors="coerce").notna()
    df.loc[labeled_mask & (pd.to_numeric(df["reliability_label"], errors="coerce") == 0), "event_label"] = 0
    df.loc[labeled_mask & (pd.to_numeric(df["reliability_label"], errors="coerce") > 0), "event_label"] = 1
    return df


def main() -> None:
    base = Path("ml/data")
    p_live = base / "x_live_ingestion_20260530_1605.csv"
    p_gdelt = base / "check_gdelt_news.csv"
    p_multi = base / "x_multi_source_training.csv"

    frames = []
    if p_live.exists():
        frames.append(_normalize_x_live_ingestion(p_live))
    if p_gdelt.exists():
        frames.append(_normalize_check_gdelt_news(p_gdelt))
    if p_multi.exists():
        frames.append(_normalize_x_multi_source(p_multi))

    if not frames:
        raise FileNotFoundError("No input pool files found in ml/data")

    pool = pd.concat(frames, ignore_index=True, sort=False)
    pool = _auto_label(pool)
    pool = pool.drop_duplicates(subset=["post_id"], keep="first")

    cols = [
        "post_id", "created_at", "lang", "raw_text", "translated_text", "source_type",
        "source_file", "event_label", "reliability_label", "annotator_name",
        "annotation_time", "notes"
    ]
    for col in cols:
        if col not in pool.columns:
            pool[col] = pd.NA

    out_pool = base / "pool_labeled_merged.csv"
    pool[cols].to_csv(out_pool, index=False)

    merged_main_path = base / "merged_training_for_model.csv"
    if merged_main_path.exists():
        main_df = pd.read_csv(merged_main_path)
        for col in cols:
            if col not in main_df.columns:
                main_df[col] = pd.NA
        final_df = pd.concat([main_df[cols], pool[cols]], ignore_index=True, sort=False)
        final_df = final_df.drop_duplicates(subset=["post_id"], keep="first")
    else:
        final_df = pool[cols].copy()

    out_final = base / "merged_training_with_pool.csv"
    final_df.to_csv(out_final, index=False)

    rel = pd.to_numeric(final_df["reliability_label"], errors="coerce")
    print(f"Saved pool-labeled file: {out_pool} ({len(pool)} rows)")
    print(f"Saved final merged file: {out_final} ({len(final_df)} rows)")
    print("Final reliability counts:")
    print(rel.value_counts(dropna=False).sort_index().to_string())


if __name__ == "__main__":
    main()
