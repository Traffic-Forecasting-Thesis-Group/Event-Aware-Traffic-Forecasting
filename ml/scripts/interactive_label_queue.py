from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def _preview(text: str, width: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= width:
        return t
    return t[: width - 3] + "..."


def _pick_text(row: pd.Series) -> str:
    translated_val = row.get("translated_text")
    raw_val = row.get("raw_text")

    translated = "" if pd.isna(translated_val) else str(translated_val).strip()
    raw = "" if pd.isna(raw_val) else str(raw_val).strip()
    return translated if translated else raw


def main() -> None:
    queue_path = Path("ml/data/manual_label_queue.csv")
    if not queue_path.exists():
        raise FileNotFoundError(f"Queue file not found: {queue_path}")

    df = pd.read_csv(queue_path)
    if "reliability_label" not in df.columns:
        df["reliability_label"] = pd.NA
    if "event_label" not in df.columns:
        df["event_label"] = pd.NA
    if "annotator_name" not in df.columns:
        df["annotator_name"] = ""
    if "annotation_time" not in df.columns:
        df["annotation_time"] = pd.NA
    if "notes" not in df.columns:
        df["notes"] = ""

    df["reliability_label"] = pd.to_numeric(df["reliability_label"], errors="coerce")
    df["event_label"] = pd.to_numeric(df["event_label"], errors="coerce")
    df["annotator_name"] = df["annotator_name"].fillna("").astype(str)
    df["annotation_time"] = df["annotation_time"].fillna("").astype(str)
    df["notes"] = df["notes"].fillna("").astype(str)
    unlabeled_idx = df[df["reliability_label"].isna()].index.tolist()

    if not unlabeled_idx:
        print("All rows are already labeled. Nothing to do.")
        return

    print(f"Queue: {queue_path}")
    print(f"Rows total: {len(df)}")
    print(f"Rows unlabeled: {len(unlabeled_idx)}")
    print("\nCommands: 1=traffic/event, 0=not useful, s=skip, q=quit+save")

    for n, idx in enumerate(unlabeled_idx, start=1):
        row = df.loc[idx]
        post_id = row.get("post_id", f"row_{idx}")
        created_at = row.get("created_at", "")
        source_type = row.get("source_type", "")
        text = _pick_text(row)

        print("\n" + "-" * 80)
        print(f"[{n}/{len(unlabeled_idx)}] post_id={post_id} | source={source_type} | created_at={created_at}")
        print(_preview(text))

        while True:
            choice = input("label [1/0/s/q]: ").strip().lower()
            if choice in {"1", "0"}:
                label = int(choice)
                df.at[idx, "reliability_label"] = label
                df.at[idx, "event_label"] = 1 if label == 1 else 0
                if not str(df.at[idx, "annotator_name"]).strip():
                    df.at[idx, "annotator_name"] = "manual_interactive"
                df.at[idx, "annotation_time"] = datetime.now().isoformat(timespec="seconds")
                if not str(df.at[idx, "notes"]).strip():
                    df.at[idx, "notes"] = "manual interactive labeling"
                break
            if choice == "s":
                break
            if choice == "q":
                df.to_csv(queue_path, index=False)
                remaining = int(pd.to_numeric(df["reliability_label"], errors="coerce").isna().sum())
                print(f"Saved and quit. Remaining unlabeled rows: {remaining}")
                return
            print("Invalid input. Use 1, 0, s, or q.")

    df.to_csv(queue_path, index=False)
    remaining = int(pd.to_numeric(df["reliability_label"], errors="coerce").isna().sum())
    print(f"Done. Saved {queue_path}. Remaining unlabeled rows: {remaining}")


if __name__ == "__main__":
    main()
