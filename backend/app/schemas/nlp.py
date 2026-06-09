from datetime import datetime

from pydantic import BaseModel, Field


class EventSignal(BaseModel):
    event: str = Field(..., examples=["Accident"])
    trust_score: float = Field(..., ge=0.0, le=1.0)
    location: str = Field(..., examples=["EDSA-Ayala"])
    timestamp: datetime


class VerificationDecision(BaseModel):
    accepted: bool
    stage: str
    confidence: float
    signal: EventSignal | None = None


class VerificationBatchResponse(BaseModel):
    accepted: int
    discarded: int
    decisions: list[VerificationDecision]


class EvaluationSample(BaseModel):
    label: int = Field(..., ge=0, le=1)
    score: float = Field(..., ge=0.0, le=1.0)


class EvaluationRequest(BaseModel):
    samples: list[EvaluationSample]
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class EvaluationMetrics(BaseModel):
    threshold: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float | None


class EvaluationDatasetRequest(BaseModel):
    file_path: str | None = None
    text_column: str = "text"
    label_column: str = "label"


class EvaluationDatasetResponse(BaseModel):
    rows_evaluated: int
    metrics: EvaluationMetrics
