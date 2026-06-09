import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.nlp.interfaces import TieredNLPFilter
from app.schemas.ingestion import CleanedTextItem
from app.schemas.nlp import EventSignal, VerificationDecision


class TransformerTieredNLPFilter(TieredNLPFilter):
    """Tiered DistilBERT and RoBERTa filter with lazy model loading."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._distilbert_classifier: Callable[[str], list[dict[str, Any]]] | None = None
        self._roberta_classifier: Callable[[str], list[dict[str, Any]]] | None = None

    async def verify(self, item: CleanedTextItem) -> VerificationDecision:
        distilbert_confidence = await self._score_with_model(
            item.cleaned_text,
            model_name=self.settings.distilbert_model_name,
            loader_name="distilbert",
        )
        if distilbert_confidence >= self.settings.distilbert_threshold:
            return self._accept(item, stage="distilbert", confidence=distilbert_confidence)

        roberta_confidence = await self._score_with_model(
            item.cleaned_text,
            model_name=self.settings.roberta_model_name,
            loader_name="roberta",
        )
        if roberta_confidence >= self.settings.roberta_threshold:
            return self._accept(item, stage="roberta", confidence=roberta_confidence)

        return VerificationDecision(
            accepted=False,
            stage="discarded",
            confidence=max(distilbert_confidence, roberta_confidence),
            signal=None,
        )

    async def verify_batch(self, items: list[CleanedTextItem]) -> list[VerificationDecision]:
        return await asyncio.gather(*(self.verify(item) for item in items))

    def _accept(self, item: CleanedTextItem, stage: str, confidence: float) -> VerificationDecision:
        signal = EventSignal(
            event=self._infer_event_type(item.cleaned_text),
            trust_score=round(confidence, 2),
            location=item.location_hint or self._infer_location(item.cleaned_text),
            timestamp=item.timestamp,
        )
        return VerificationDecision(accepted=True, stage=stage, confidence=confidence, signal=signal)

    async def _score_with_model(self, text: str, model_name: str, loader_name: str) -> float:
        keyword_prior = self._heuristic_score(text)
        classifier = await self._get_classifier(model_name, loader_name)
        if classifier is None:
            return 0.0 if self.settings.strict_nlp_mode else keyword_prior

        try:
            inference = await asyncio.to_thread(classifier, text)
            top = inference[0]
            label = str(top.get("label", "")).lower()
            score = float(top.get("score", 0.0))
            if any(token in label for token in ["negative", "label_0"]):
                calibrated = round(max(1.0 - score, keyword_prior), 4)
                return calibrated
            calibrated = round(max(score, keyword_prior), 4)
            return calibrated
        except Exception:
            return 0.0 if self.settings.strict_nlp_mode else keyword_prior

    async def _get_classifier(
        self,
        model_name: str,
        loader_name: str,
    ) -> Callable[[str], list[dict[str, Any]]] | None:
        cached = self._distilbert_classifier if loader_name == "distilbert" else self._roberta_classifier
        if cached is not None:
            return cached

        try:
            from transformers import pipeline

            model_ref = self._resolve_model_reference(loader_name, model_name)
            loaded = pipeline("text-classification", model=model_ref)
            self._persist_model_metadata(loader_name=loader_name, model_ref=model_ref)
            if loader_name == "distilbert":
                self._distilbert_classifier = loaded
            else:
                self._roberta_classifier = loaded
            return loaded
        except Exception:
            return None

    def _resolve_model_reference(self, loader_name: str, fallback_name: str) -> str:
        if loader_name == "distilbert" and self.settings.distilbert_model_path:
            return self.settings.distilbert_model_path
        if loader_name == "roberta" and self.settings.roberta_model_path:
            return self.settings.roberta_model_path
        return fallback_name

    def _persist_model_metadata(self, loader_name: str, model_ref: str) -> None:
        artifact_dir = Path(self.settings.model_artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "module": loader_name,
            "model_ref": model_ref,
            "registry_version": self.settings.model_registry_version,
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "strict_nlp_mode": self.settings.strict_nlp_mode,
            "distilbert_threshold": self.settings.distilbert_threshold,
            "roberta_threshold": self.settings.roberta_threshold,
        }
        output_file = artifact_dir / f"{loader_name}_{self.settings.model_registry_version}.json"
        output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _heuristic_score(self, text: str) -> float:
        strong = ["accident", "bangga", "collision", "crash", "pileup"]
        medium = ["traffic", "roadblock", "flood", "stalled", "gridlock"]
        lowered = text.lower()
        if any(token in lowered for token in strong):
            return 0.9
        if any(token in lowered for token in medium):
            return 0.75
        return 0.2

    def _infer_event_type(self, text: str) -> str:
        lowered = text.lower()
        mapping = {
            "Accident": ["accident", "bangga", "collision", "crash"],
            "Flood": ["flood", "baha", "rainfall"],
            "Roadblock": ["roadblock", "closed", "reroute", "stalled"],
            "Congestion": ["traffic", "gridlock", "heavy traffic"],
        }
        for event_name, terms in mapping.items():
            if any(term in lowered for term in terms):
                return event_name
        return "Traffic Incident"

    def _infer_location(self, text: str) -> str:
        corridors = [
            "edsa-ayala",
            "edsa",
            "c5",
            "ortigas",
            "quezon avenue",
            "commonwealth",
            "roxas boulevard",
            "katipunan",
        ]
        lowered = text.lower()
        for corridor in corridors:
            if corridor in lowered:
                return corridor.title()
        return "Metro Manila"
