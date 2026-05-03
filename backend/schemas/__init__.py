from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

# Road Node Schemas
class RoadNodeBase(BaseModel):
    osm_id: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    node_type: str = "intersection"
    is_signal: bool = False
    road_class: Optional[str] = None
    extra: Optional[dict] = None

class RoadNodeCreate(RoadNodeBase):
    pass
 
class RoadNodeUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    node_type: Optional[str] = None
    is_signal: Optional[bool] = None
    road_class: Optional[str] = None
    graph_index: Optional[int] = None
    extra: Optional[dict] = None
 
class RoadNodeResponse(RoadNodeBase):
    id: int
    graph_index: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
 
    model_config = {"from_attributes": True}

# Road Edge Schemas
class RoadEdgeBase(BaseModel):
    osm_way_id: Optional[str] = None
    source_node_id: int
    target_node_id: int
    length_m: float = Field(..., gt=0)
    speed_limit_kph: Optional[float] = None
    lanes: int = 1
    road_class: Optional[str] = None
    is_oneway: bool = False
    is_bridge: bool = False
    is_tunnel: bool = False
    spatial_weight: float = 1.0
 
class RoadEdgeCreate(RoadEdgeBase):
    pass
 
class RoadEdgeResponse(RoadEdgeBase):
    id: int
    created_at: datetime
 
    model_config = {"from_attributes": True}

# Traffic Observation Schemas
class TrafficObservationCreate(BaseModel):
    node_id: int
    observed_at: datetime
    speed_kph: Optional[float] = Field(None, ge=0, le=300)
    volume: Optional[float] = Field(None, ge=0)
    density: Optional[float] = Field(None, ge=0)
    occupancy: Optional[float] = Field(None, ge=0.0, le=1.0)
    level_of_service: Optional[str] = None
    has_incident: bool = False
    incident_type: Optional[str] = None
    source: Optional[str] = None
    extra: Optional[dict] = None
 
    @field_validator("level_of_service")
    @classmethod
    def validate_los(cls, v):
        if v is not None and v not in {"A", "B", "C", "D", "E", "F"}:
            raise ValueError("LOS must be one of A–F")
        return v
 
class TrafficObservationResponse(TrafficObservationCreate):
    id: int
    trend_component: Optional[float] = None
    seasonal_component: Optional[float] = None
    residual_component: Optional[float] = None
 
    model_config = {"from_attributes": True}

# Spatial Prediction Schemas
class PredictionRequest(BaseModel):
    node_ids: List[int] = Field(..., min_length=1, max_length=500)
    horizon_minutes: int = Field(30, ge=5, le=120)
    include_confidence: bool = True
 
class NodePrediction(BaseModel):
    node_id: int
    horizon_minutes: int
    gwn_speed_kph: Optional[float] = None
    lstm_speed_kph: Optional[float] = None
    xgb_speed_kph: Optional[float] = None
    ensemble_speed_kph: Optional[float] = None
    confidence: Optional[float] = None
    prediction_interval_low: Optional[float] = None
    prediction_interval_high: Optional[float] = None
    predicted_los: Optional[str] = None
    model_version: Optional[str] = None
 
    model_config = {"from_attributes": True}
 
class PredictionResponse(BaseModel):
    requested_at: datetime
    horizon_minutes: int
    predictions: List[NodePrediction]
    node_count: int

# Graph Construction Schemas
class GraphBuildRequest(BaseModel):
    city_filter: Optional[List[str]] = None      
    bbox: Optional[List[float]] = None           
    max_nodes: Optional[int] = Field(None, le=50_000)
    include_weights: bool = True
 
class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    avg_degree: float
    density: float
    cities_covered: List[str]
    bbox: List[float]
 
class AdjacencyMatrixResponse(BaseModel):
    node_count: int
    graph_index_to_node_id: dict[int, int]
    # Sparse representation: list of [row, col, weight]
    edges: List[List[float]]
    stats: GraphStats

# Bulk Import Schemas
class OSMImportRequest(BaseModel):
    city: str
    overpass_query: Optional[str] = None    
    dry_run: bool = False
 
class BulkImportResult(BaseModel):
    nodes_inserted: int
    nodes_skipped: int
    edges_inserted: int
    edges_skipped: int
    errors: List[str] = []
    duration_seconds: float