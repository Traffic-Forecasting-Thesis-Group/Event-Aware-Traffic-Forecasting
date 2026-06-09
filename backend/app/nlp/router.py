from fastapi import APIRouter, HTTPException

from app.nlp.evaluation import evaluate_predictions
from app.nlp.service import TransformerTieredNLPFilter
from app.nlp.workflow import evaluate_dataset
from app.schemas.ingestion import CleanedTextItem
from app.schemas.nlp import (
    EvaluationDatasetRequest,
    EvaluationDatasetResponse,
    EvaluationMetrics,
    EvaluationRequest,
    EventSignal,
    VerificationBatchResponse,
)

router = APIRouter(prefix="/nlp", tags=["nlp"])
filter_service = TransformerTieredNLPFilter()


@router.post("/verify", response_model=EventSignal)
async def verify_event(item: CleanedTextItem) -> EventSignal:
    decision = await filter_service.verify(item)
    if not decision.accepted or decision.signal is None:
        raise HTTPException(status_code=422, detail="Event discarded by tiered filter")
    return decision.signal


@router.post("/verify/batch", response_model=VerificationBatchResponse)
async def verify_batch(items: list[CleanedTextItem]) -> VerificationBatchResponse:
    decisions = await filter_service.verify_batch(items)
    accepted = sum(1 for decision in decisions if decision.accepted)
    discarded = len(decisions) - accepted
    return VerificationBatchResponse(accepted=accepted, discarded=discarded, decisions=decisions)


@router.post("/evaluate", response_model=EvaluationMetrics)
async def evaluate(request: EvaluationRequest) -> EvaluationMetrics:
    if not request.samples:
        raise HTTPException(status_code=400, detail="samples must not be empty")
    return evaluate_predictions(request)


@router.post("/evaluate/dataset", response_model=EvaluationDatasetResponse)
async def evaluate_from_dataset(request: EvaluationDatasetRequest) -> EvaluationDatasetResponse:
    try:
        return await evaluate_dataset(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
