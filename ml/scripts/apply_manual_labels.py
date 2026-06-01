from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def main() -> None:
    base = Path("ml/data")
    base_file = base / "merged_training_with_pool.csv"
    queue_file = base / "manual_label_queue.csv"
    out_file = base / "merged_training_final.csv"
    out_binary = base / "merged_training_final_binary.csv"

    if not base_file.exists():
        raise FileNotFoundError(f"Missing base file: {base_file}")
    if not queue_file.exists():
        raise FileNotFoundError(f"Missing queue file: {queue_file}")

    df = pd.read_csv(base_file)
    q = pd.read_csv(queue_file)

    required = {"post_id", "reliability_label"}
    missing = required - set(q.columns)
    if missing:
        raise ValueError(f"Queue file missing required columns: {sorted(missing)}")

    q["reliability_label"] = pd.to_numeric(q["reliability_label"], errors="coerce")
    labeled_q = q[q["reliability_label"].isin([0, 1, 2])].copy()

    if "annotator_name" not in labeled_q.columns:
        labeled_q["annotator_name"] = "manual_annotator"
    labeled_q["annotator_name"] = labeled_q["annotator_name"].fillna("manual_annotator")

    if "annotation_time" not in labeled_q.columns:
        labeled_q["annotation_time"] = datetime.now().isoformat(timespec="seconds")
    labeled_q["annotation_time"] = labeled_q["annotation_time"].fillna(datetime.now().isoformat(timespec="seconds"))

    # Keep event_label consistent with reliability for binary event detection flow.
    labeled_q["event_label"] = labeled_q["reliability_label"].apply(lambda x: 0 if x == 0 else 1)

    # Update matching post_id rows in base dataframe.
    update_cols = [c for c in ["event_label", "reliability_label", "annotator_name", "annotation_time", "notes"] if c in labeled_q.columns]
    labeled_q = labeled_q[["post_id", *update_cols]].drop_duplicates(subset=["post_id"], keep="last")

    merged = df.merge(labeled_q, on="post_id", how="left", suffixes=("", "_new"))
    for col in update_cols:
        new_col = f"{col}_new"
        if new_col in merged.columns:
            merged[col] = merged[new_col].combine_first(merged[col])
            merged = merged.drop(columns=[new_col])

    merged.to_csv(out_file, index=False)

    # Binary-ready export for DistilBERT/RoBERTa notebook paths that require labels in {0,1}.
    binary_df = merged.copy()
    binary_df["reliability_label"] = pd.to_numeric(binary_df["reliability_label"], errors="coerce")
    binary_df = binary_df[binary_df["reliability_label"].notna()].copy()
    binary_df["reliability_label"] = binary_df["reliability_label"].clip(upper=1).astype(int)
    binary_df.to_csv(out_binary, index=False)

    rel = pd.to_numeric(merged["reliability_label"], errors="coerce")
    print(f"Saved: {out_file}")
    print(f"Saved binary-ready file: {out_binary}")
    print(f"Rows total: {len(merged)}")
    print("Reliability counts:")
    print(rel.value_counts(dropna=False).sort_index().to_string())


if __name__ == "__main__":
    main()
