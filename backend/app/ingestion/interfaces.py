from abc import ABC, abstractmethod

from app.schemas.ingestion import (
    CSVIngestionResponse,
    CleanedTextItem,
    RawTextItem,
    SpatialGraphBuildRequest,
    SpatialGraphBuildResponse,
    StructuredTrafficRecord,
    UnstructuredCollectionResponse,
)


class DataIngestor(ABC):
    @abstractmethod
    async def collect_unstructured(self, limit_per_source: int | None = None) -> UnstructuredCollectionResponse:
        """Fetch text streams from external event sources."""

    @abstractmethod
    async def preprocess_texts(self, items: list[RawTextItem]) -> list[CleanedTextItem]:
        """Apply textual pre-cleaning and Taglish-aware normalization."""

    @abstractmethod
    async def collect_structured_traffic(self, file_path: str) -> CSVIngestionResponse:
        """Load structured traffic records from CSV or API data sources."""

    @abstractmethod
    async def build_spatial_graph(self, request: SpatialGraphBuildRequest) -> SpatialGraphBuildResponse:
        """Generate and persist a Metro Manila graph artifact metadata payload."""
