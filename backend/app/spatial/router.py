"""
FastAPI router for spatial graph generation and routing operations.
Exposes OSM-based road network generation and flood-aware routing.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add ml module to path for imports
ml_path = Path(__file__).resolve().parents[3] / "ml" / "src"
if str(ml_path) not in sys.path:
    sys.path.insert(0, str(ml_path))

from event_aware_traffic.spatial import (  # pyright: ignore[reportMissingImports]
    extract_driving_graph_from_pbf,
    graph_to_adjacency_matrix,
)
from event_aware_traffic.flood_risk import (  # pyright: ignore[reportMissingImports]
    assess_place_risk,
    assess_route_risk,
    build_flood_penalized_graph,
    reroute_with_flood_avoidance,
)

router = APIRouter(tags=["spatial"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SpatialGraphResponse(BaseModel):
    """Response for spatial graph generation."""
    status: str
    message: str
    nodes_count: int
    edges_count: int
    graph_path: Optional[str] = None
    adjacency_matrix_path: Optional[str] = None
    bbox: dict  # {north, south, east, west}


class SpatialGraphRequest(BaseModel):
    """Request for generating an OSM spatial graph."""
    pbf_path: str = "ml/data/raw/OSM/philippines-260503.osm.pbf"
    bbox: Optional[dict] = None
    sparse: bool = True


class PlaceRiskRequest(BaseModel):
    """Request for place risk assessment."""
    longitude: float
    latitude: float
    rainfall_mm_per_hour: float = 0.0


class PlaceRiskResponse(BaseModel):
    """Response for place risk assessment."""
    risk_score: float
    risk_level: str
    rainfall_multiplier: float
    hazard_overlap_ratio: float
    intersecting_hazard_count: int
    recommendation: str


class RerouteRequest(BaseModel):
    """Request for flood-aware rerouting."""
    origin: tuple[float, float]  # (lon, lat)
    destination: tuple[float, float]  # (lon, lat)
    rainfall_mm_per_hour: float = 0.0


class RerouteResponse(BaseModel):
    """Response for rerouting."""
    status: str
    original_distance_m: float
    safe_distance_m: float
    distance_increase_percent: float
    flooded_length_m: float
    recommendation: str
    route_nodes: Optional[list[int]] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/spatial/generate-graph", response_model=SpatialGraphResponse)
async def generate_osm_graph(request: SpatialGraphRequest) -> SpatialGraphResponse:
    """
    Generate a spatial graph from OSM .pbf file.
    
    Args:
        pbf_path: Path to the .pbf file (defaults to Philippines OSM)
        bbox: Optional bounding box dict with keys {north, south, east, west}
              Default: Metro Manila (14.35°N to 15.05°N, 120.88°E to 121.08°E)
        sparse: If True, use sparse (CSR) matrix; if False, use dense NumPy array
    
    Returns:
        SpatialGraphResponse with graph metadata and save paths
    """
    try:
        pbf_path_obj = Path(request.pbf_path)
        if not pbf_path_obj.exists():
            raise FileNotFoundError(f"PBF file not found: {request.pbf_path}")
        
        # Extract driving graph from PBF
        G = extract_driving_graph_from_pbf(str(pbf_path_obj), bbox=request.bbox)
        nodes_count = G.number_of_nodes()
        edges_count = G.number_of_edges()
        
        if nodes_count == 0:
            raise ValueError(
                f"Graph has no nodes. Check bbox bounds or PBF content. "
                f"Bbox used: {request.bbox or 'default (Metro Manila)'}"
            )
        
        # Generate adjacency matrix
        A, node_list = graph_to_adjacency_matrix(G, sparse=request.sparse)
        
        # Save artifacts
        artifacts_dir = Path("artifacts/spatial_grid")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        graph_save_path = artifacts_dir / "road_network_graph.pkl"
        adj_matrix_path = artifacts_dir / "adjacency_matrix.npz"
        
        import pickle
        import scipy.sparse as sp
        import numpy as np
        
        with open(graph_save_path, "wb") as f:
            pickle.dump(G, f)
        
        if request.sparse and sp.issparse(A):
            sp.save_npz(str(adj_matrix_path), A)
        else:
            np.savez(str(adj_matrix_path), adjacency_matrix=A, nodes=node_list)
        
        return SpatialGraphResponse(
            status="success",
            message=f"Generated spatial graph from {request.pbf_path}",
            nodes_count=nodes_count,
            edges_count=edges_count,
            graph_path=str(graph_save_path),
            adjacency_matrix_path=str(adj_matrix_path),
            bbox=request.bbox or {
                "north": 15.05, "south": 14.35,
                "east": 121.08, "west": 120.88
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Graph generation failed: {str(e)}"
        )


@router.post("/spatial/assess-place-risk", response_model=PlaceRiskResponse)
async def assess_place_risk_endpoint(request: PlaceRiskRequest) -> PlaceRiskResponse:
    """
    Assess flood risk at a specific location.
    
    Args:
        request: PlaceRiskRequest with (longitude, latitude, rainfall)
    
    Returns:
        PlaceRiskResponse with risk metrics
    """
    try:
        from event_aware_traffic.flood_risk import load_flood_hazard_map  # pyright: ignore[reportMissingImports]
        
        hazard_path = Path("ml/data/raw/MetroManila")
        if not hazard_path.exists():
            raise FileNotFoundError(
                f"Flood hazard maps not found at {hazard_path}. "
                "Please download Project NOAH shapefiles to this location."
            )
        
        hazard_gdf = load_flood_hazard_map(hazard_path)
        risk = assess_place_risk(
            lon=request.longitude,
            lat=request.latitude,
            hazard_gdf=hazard_gdf,
            rainfall_mm_per_hour=request.rainfall_mm_per_hour,
        )
        
        return PlaceRiskResponse(
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            rainfall_multiplier=risk.rainfall_multiplier,
            hazard_overlap_ratio=risk.hazard_overlap_ratio,
            intersecting_hazard_count=risk.intersecting_hazard_count,
            recommendation=risk.recommendation,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Place risk assessment failed: {str(e)}"
        )


@router.post("/spatial/reroute-with-hazard-avoidance", response_model=RerouteResponse)
async def reroute_endpoint(request: RerouteRequest) -> RerouteResponse:
    """
    Find a flood-safe alternate route between two points.
    
    Args:
        request: RerouteRequest with origin, destination, rainfall
    
    Returns:
        RerouteResponse with original vs. safe route metrics
    """
    try:
        from event_aware_traffic.flood_risk import load_flood_hazard_map  # pyright: ignore[reportMissingImports]
        import pickle
        
        # Load the road network graph
        graph_path = Path("artifacts/spatial_grid/road_network_graph.pkl")
        if not graph_path.exists():
            raise FileNotFoundError(
                "Road network graph not found. "
                "Run POST /api/spatial/generate-graph first."
            )
        
        with open(graph_path, "rb") as f:
            G = pickle.load(f)
        
        # Load hazard map
        hazard_path = Path("ml/data/raw/MetroManila")
        if not hazard_path.exists():
            raise FileNotFoundError(
                f"Flood hazard maps not found at {hazard_path}. "
                "Please download Project NOAH shapefiles to this location."
            )
        
        hazard_gdf = load_flood_hazard_map(hazard_path)
        
        # Build flood-penalized graph
        G_penalized = build_flood_penalized_graph(
            G, hazard_gdf, rainfall_mm_per_hour=request.rainfall_mm_per_hour
        )
        
        # Find safe route
        reroute_result = reroute_with_flood_avoidance(
            G=G_penalized,
            origin_node=request.origin[0],  # Would need node ID mapping in production
            destination_node=request.destination[1],
            hazard_gdf=hazard_gdf,
            rainfall_mm_per_hour=request.rainfall_mm_per_hour,
        )
        
        return RerouteResponse(
            status="success",
            original_distance_m=reroute_result.original_distance_m,
            safe_distance_m=reroute_result.safe_distance_m,
            distance_increase_percent=reroute_result.distance_increase_percent,
            flooded_length_m=reroute_result.flooded_length_m,
            recommendation=reroute_result.recommendation,
            route_nodes=reroute_result.safe_route_nodes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rerouting failed: {str(e)}"
        )


@router.get("/spatial/status")
async def spatial_status():
    """Check availability of spatial data and modules."""
    checks = {
        "osm_pbf_exists": Path("ml/data/raw/OSM/philippines-260503.osm.pbf").exists(),
        "flood_maps_exist": Path("ml/data/raw/MetroManila").exists(),
        "spatial_grid_exists": Path("artifacts/spatial_grid").exists(),
        "graph_cached": Path("artifacts/spatial_grid/road_network_graph.pkl").exists(),
    }
    
    all_ready = all(checks.values())
    
    return {
        "status": "ready" if all_ready else "partial",
        "checks": checks,
        "message": (
            "All spatial data ready!" if all_ready
            else "Run POST /api/spatial/generate-graph to initialize spatial grid"
        ),
    }
