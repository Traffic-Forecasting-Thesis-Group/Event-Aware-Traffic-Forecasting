from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from app.schemas.nlp import EvaluationMetrics, EvaluationRequest


def evaluate_predictions(request: EvaluationRequest) -> EvaluationMetrics:
    labels = [sample.label for sample in request.samples]
    scores = [sample.score for sample in request.samples]
    predictions = [1 if score >= request.threshold else 0 for score in scores]

    precision = float(precision_score(labels, predictions, zero_division=0))
    recall = float(recall_score(labels, predictions, zero_division=0))
    f1 = float(f1_score(labels, predictions, zero_division=0))

    auc_roc: float | None = None
    if len(set(labels)) > 1:
        auc_roc = float(roc_auc_score(labels, scores))

    return EvaluationMetrics(
        threshold=request.threshold,
        precision=precision,
        recall=recall,
        f1_score=f1,
        auc_roc=auc_roc,
    )
