from datetime import datetime

from pydantic import BaseModel, Field


class RawTextItem(BaseModel):
    source: str = Field(..., examples=["mmda_twitter"])
    text: str
    location_hint: str | None = None
    timestamp: datetime


class CleanedTextItem(BaseModel):
    source: str
    original_text: str
    cleaned_text: str
    location_hint: str | None = None
    language_hint: str = "taglish"
    timestamp: datetime


class StructuredTrafficRecord(BaseModel):
    timestamp: datetime
    node: str
    speed: float
    flow: float


class UnstructuredCollectionResponse(BaseModel):
    total_items: int
    by_source: dict[str, int]
    items: list[RawTextItem]


class CSVIngestionRequest(BaseModel):
    file_path: str


class CSVIngestionResponse(BaseModel):
    loaded: int
    deduplicated: int
    invalid_rows: int
    preview: list[StructuredTrafficRecord]


class SpatialGraphBuildRequest(BaseModel):
    place_name: str = Field(default="Metro Manila, Philippines")
    output_path: str = Field(default="artifacts/metro_manila_graph.graphml")


class SpatialGraphBuildResponse(BaseModel):
    status: str
    artifact: str
    nodes: int
    edges: int
    updated_at: datetime


class IngestionPipelineRequest(BaseModel):
    limit_per_source: int | None = Field(default=None, ge=1, le=100)
    traffic_csv_path: str | None = None
    place_name: str | None = None
    output_path: str | None = None


class IngestionTaskResponse(BaseModel):
    task_id: str
    task_name: str
    status: str


class IngestionTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, object] | None = None
    error: str | None = None
