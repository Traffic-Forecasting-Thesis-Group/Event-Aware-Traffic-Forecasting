from __future__ import annotations

import asyncio

import pandas as pd

from app.core.config import get_settings
from app.nlp.evaluation import evaluate_predictions
from app.nlp.service import TransformerTieredNLPFilter
from app.schemas.ingestion import CleanedTextItem
from app.schemas.nlp import EvaluationDatasetRequest, EvaluationDatasetResponse, EvaluationRequest, EvaluationSample


async def evaluate_dataset(request: EvaluationDatasetRequest) -> EvaluationDatasetResponse:
    settings = get_settings()
    dataset_path = request.file_path or settings.nlp_evaluation_dataset_path

    frame = pd.read_csv(dataset_path)
    required_columns = {request.text_column, request.label_column}
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    filter_service = TransformerTieredNLPFilter()
    samples: list[EvaluationSample] = []

    for row in frame.itertuples(index=False):
        text = str(getattr(row, request.text_column))
        label = int(getattr(row, request.label_column))

        item = CleanedTextItem(
            source="dataset",
            original_text=text,
            cleaned_text=text,
            location_hint=None,
            language_hint="taglish",
            timestamp=pd.Timestamp.utcnow().to_pydatetime(),
        )
        decision = await filter_service.verify(item)
        score = float(decision.confidence)
        samples.append(EvaluationSample(label=label, score=score))

    metrics = evaluate_predictions(EvaluationRequest(samples=samples))
    return EvaluationDatasetResponse(rows_evaluated=len(samples), metrics=metrics)
