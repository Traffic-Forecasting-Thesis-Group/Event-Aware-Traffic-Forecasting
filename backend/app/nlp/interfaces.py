from abc import ABC, abstractmethod

from app.schemas.ingestion import CleanedTextItem
from app.schemas.nlp import VerificationDecision


class TieredNLPFilter(ABC):
    @abstractmethod
    async def verify(self, item: CleanedTextItem) -> VerificationDecision:
        """Run tiered verification: DistilBERT first, RoBERTa fallback."""

    @abstractmethod
    async def verify_batch(self, items: list[CleanedTextItem]) -> list[VerificationDecision]:
        """Run verification for a batch of cleaned text items."""
