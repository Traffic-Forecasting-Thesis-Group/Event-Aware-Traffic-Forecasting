from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    try:
        import joblib
        import pandas as pd
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, classification_report, f1_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
    except Exception as exc:
        raise SystemExit(f"Missing training dependencies: {exc}")

    parser = argparse.ArgumentParser(description="Train a binary reliability classifier from labeled traffic data")
    parser.add_argument("--input", default="ml/data/merged_training_for_model.csv", help="Merged labeled CSV")
    parser.add_argument("--output-dir", default="ml/models/binary_reliability", help="Directory for model artifacts")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)
    if "translated_text" not in df.columns:
        raise ValueError("Input CSV must contain translated_text")
    if "reliability_label" not in df.columns:
        raise ValueError("Input CSV must contain reliability_label")

    df = df.copy()
    df["text"] = df["translated_text"].fillna(df.get("raw_text", "")).astype(str)
    df["reliability_label"] = pd.to_numeric(df["reliability_label"], errors="coerce")
    df = df.dropna(subset=["text", "reliability_label"]).copy()
    df["reliability_label"] = df["reliability_label"].astype(int)

    # Current notebook expects binary labels. Treat label 2 as high-confidence positive.
    df["binary_label"] = df["reliability_label"].clip(upper=1)

    labeled = df[df["binary_label"].isin([0, 1])].copy()
    if len(labeled) < 20:
        raise ValueError("Not enough labeled rows for training after binary conversion.")

    X_train, X_test, y_train, y_test = train_test_split(
        labeled["text"],
        labeled["binary_label"],
        test_size=args.test_size,
        random_state=args.seed,
        stratify=labeled["binary_label"],
    )

    model = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(max_features=25000, ngram_range=(1, 2), min_df=2)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, out_dir / "reliability_binary_model.joblib")

    metrics = {
        "rows_total": int(len(df)),
        "rows_used": int(len(labeled)),
        "binary_positive": int((labeled["binary_label"] == 1).sum()),
        "binary_negative": int((labeled["binary_label"] == 0).sum()),
        "accuracy": float(accuracy_score(y_test, preds)),
        "f1": float(f1_score(y_test, preds)),
        "classification_report": classification_report(y_test, preds, digits=4),
    }

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    print(f"Saved model to {out_dir / 'reliability_binary_model.joblib'}")
    print(f"Saved metrics to {out_dir / 'metrics.json'}")
    print(metrics["classification_report"])


if __name__ == "__main__":
    main()
