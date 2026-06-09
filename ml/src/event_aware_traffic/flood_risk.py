from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DEFAULT_HAZARD_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
DEFAULT_TARGET_CRS = "EPSG:4326"


@dataclass(slots=True)
class FloodRiskAssessment:
    """Compact summary for a place or route flood risk check.

    The hazard maps are static 5-year flood extents, so the scoring is
    intentionally conservative: overlap with the mapped flood area is the
    primary signal, and rainfall acts as a trigger multiplier.
    """

    risk_score: float
    risk_level: str
    rainfall_multiplier: float
    hazard_overlap_ratio: float
    intersecting_hazard_count: int
    recommendation: str
    flooded_length_m: float = 0.0
    total_length_m: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RerouteResult:
    original_path: list[Any]
    rerouted_path: list[Any]
    original_cost: float
    rerouted_cost: float
    avoided_edges: int
    assessment: FloodRiskAssessment

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["assessment"] = self.assessment.to_dict()
        return payload


def _import_geopandas():
    try:
        import geopandas as gpd
    except Exception as exception:  # pragma: no cover - import guard
        raise RuntimeError("geopandas is required for flood hazard loading") from exception
    return gpd


def _import_networkx():
    try:
        import networkx as nx
    except Exception as exception:  # pragma: no cover - import guard
        raise RuntimeError("networkx is required for flood-aware rerouting") from exception
    return nx


def _import_shapely():
    try:
        from shapely.geometry import LineString, Point
    except Exception as exception:  # pragma: no cover - import guard
        raise RuntimeError("shapely is required for flood geometry scoring") from exception
    return LineString, Point


def discover_hazard_shapefile(source_path: str | Path | None = None) -> Path:
    """Locate the Metro Manila hazard shapefile without scanning unrelated folders."""

    path = Path(source_path) if source_path is not None else DEFAULT_HAZARD_ROOT / "MetroManila"
    if path.is_file() and path.suffix.lower() == ".shp":
        return path

    if not path.exists():
        raise FileNotFoundError(f"Flood hazard path does not exist: {path}")

    preferred = sorted(path.glob("*_Flood_5year.shp"))
    if preferred:
        return preferred[0]

    fallback = sorted(path.glob("*.shp"))
    if fallback:
        return fallback[0]

    raise FileNotFoundError(f"No shapefile found under {path}")


def load_flood_hazard_map(
    source_path: str | Path | None = None,
    target_crs: str = DEFAULT_TARGET_CRS,
) -> "Any":
    """Load the flood hazard polygons for Metro Manila.

    Why geopandas here instead of a raw shapefile reader:
    - It preserves CRS metadata.
    - It gives us spatial indexing and fast geometry operations.
    - It keeps the module compatible with route scoring and rerouting logic.
    """

    gpd = _import_geopandas()

    shapefile = discover_hazard_shapefile(source_path)
    print(f"Loading flood hazard map: {shapefile}")
    hazard_gdf = gpd.read_file(shapefile)

    if hazard_gdf.empty:
        raise ValueError(f"Flood hazard map is empty: {shapefile}")

    if hazard_gdf.crs is None:
        hazard_gdf = hazard_gdf.set_crs(target_crs)
    elif target_crs and str(hazard_gdf.crs).upper() != target_crs.upper():
        hazard_gdf = hazard_gdf.to_crs(target_crs)

    hazard_gdf = hazard_gdf[hazard_gdf.geometry.notna() & ~hazard_gdf.geometry.is_empty].copy()
    hazard_gdf.reset_index(drop=True, inplace=True)
    hazard_gdf["hazard_layer"] = shapefile.stem
    hazard_gdf["hazard_weight"] = 1.0

    print(f"Loaded {len(hazard_gdf)} flood hazard polygons")
    return hazard_gdf


def rainfall_multiplier(rainfall_mm_per_hour: float | int | None) -> float:
    """Boost flood risk when rainfall is present."""

    if rainfall_mm_per_hour is None:
        return 1.0

    rainfall = max(float(rainfall_mm_per_hour), 0.0)
    if rainfall <= 1.0:
        return 1.0
    if rainfall <= 5.0:
        return 1.10
    if rainfall <= 15.0:
        return 1.25
    if rainfall <= 30.0:
        return 1.50
    return 1.80


def risk_level_from_score(score: float) -> str:
    if score >= 0.80:
        return "severe"
    if score >= 0.55:
        return "high"
    if score >= 0.30:
        return "moderate"
    if score > 0.0:
        return "low"
    return "none"


def recommendation_from_score(score: float) -> str:
    if score >= 0.80:
        return "Avoid this area and reroute immediately."
    if score >= 0.55:
        return "High flood exposure. Prefer an alternate route."
    if score >= 0.30:
        return "Monitor conditions and reroute if rainfall increases."
    if score > 0.0:
        return "Minor exposure. Keep as a fallback route only."
    return "No flood overlap detected in the current hazard layer."


def _geometry_risk_stats(geometry: Any, hazard_gdf: Any) -> tuple[float, int, float, float]:
    if geometry is None or getattr(geometry, "is_empty", True):
        return 0.0, 0, 0.0, 0.0

    try:
        sindex = hazard_gdf.sindex
        candidate_indexes = list(sindex.intersection(geometry.bounds))
        candidate_hazards = hazard_gdf.iloc[candidate_indexes] if candidate_indexes else hazard_gdf.iloc[0:0]
    except Exception:
        candidate_hazards = hazard_gdf

    if candidate_hazards.empty:
        return 0.0, 0, 0.0, 0.0

    try:
        intersecting = candidate_hazards[candidate_hazards.intersects(geometry)]
    except Exception:
        intersecting = candidate_hazards

    if intersecting.empty:
        return 0.0, 0, 0.0, 0.0

    geom_type = getattr(geometry, "geom_type", "")

    if geom_type in {"Point", "MultiPoint"}:
        overlap_ratio = 1.0 if any(not geometry.intersection(hazard_geom).is_empty for hazard_geom in intersecting.geometry) else 0.0
        flooded_measure = overlap_ratio
        total_measure = 1.0
    elif geom_type in {"LineString", "MultiLineString"}:
        total_measure = float(getattr(geometry, "length", 0.0) or 0.0)
        flooded_measure = 0.0
        for hazard_geom in intersecting.geometry:
            piece = geometry.intersection(hazard_geom)
            flooded_measure += float(getattr(piece, "length", 0.0) or 0.0)
        overlap_ratio = flooded_measure / total_measure if total_measure > 0 else 0.0
    else:
        total_measure = float(getattr(geometry, "area", 0.0) or 0.0)
        flooded_measure = 0.0
        for hazard_geom in intersecting.geometry:
            piece = geometry.intersection(hazard_geom)
            flooded_measure += float(getattr(piece, "area", 0.0) or 0.0)
        overlap_ratio = flooded_measure / total_measure if total_measure > 0 else 0.0

    return float(max(0.0, min(1.0, overlap_ratio))), int(len(intersecting)), flooded_measure, total_measure


def assess_place_risk(
    longitude: float,
    latitude: float,
    hazard_gdf: Any,
    rainfall_mm_per_hour: float | int | None = None,
) -> FloodRiskAssessment:
    """Assess a point location against the flood hazard map."""

    _, Point = _import_shapely()

    point = Point(float(longitude), float(latitude))
    overlap_ratio, intersecting_count, flooded_measure, total_measure = _geometry_risk_stats(point, hazard_gdf)
    rain_boost = rainfall_multiplier(rainfall_mm_per_hour)

    base_score = 1.0 if overlap_ratio > 0.0 else 0.0
    risk_score = min(1.0, base_score * rain_boost)

    return FloodRiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level_from_score(risk_score),
        rainfall_multiplier=rain_boost,
        hazard_overlap_ratio=overlap_ratio,
        intersecting_hazard_count=intersecting_count,
        flooded_length_m=flooded_measure,
        total_length_m=total_measure,
        recommendation=recommendation_from_score(risk_score),
    )


def _edge_geometry(graph: Any, u: Any, v: Any, edge_data: dict[str, Any]) -> Any:
    geometry = edge_data.get("geometry")
    if geometry is not None and not getattr(geometry, "is_empty", True):
        return geometry

    LineString, _ = _import_shapely()
    try:
        u_node = graph.nodes[u]
        v_node = graph.nodes[v]
        return LineString([(float(u_node["x"]), float(u_node["y"])), (float(v_node["x"]), float(v_node["y"]))])
    except Exception:
        return None


def _edge_length(edge_data: dict[str, Any], geometry: Any, base_weight: str) -> float:
    value = edge_data.get(base_weight)
    if value is not None:
        try:
            return float(value)
        except Exception:
            pass

    if geometry is not None and getattr(geometry, "length", 0.0) > 0:
        return float(geometry.length)
    return 1.0


def assess_route_risk(
    graph: Any,
    route_nodes: Iterable[Any],
    hazard_gdf: Any,
    rainfall_mm_per_hour: float | int | None = None,
    base_weight: str = "length",
) -> FloodRiskAssessment:
    """Assess a route by scoring the edges used in the node path."""

    route_nodes = list(route_nodes)
    if len(route_nodes) < 2:
        return FloodRiskAssessment(
            risk_score=0.0,
            risk_level="none",
            rainfall_multiplier=rainfall_multiplier(rainfall_mm_per_hour),
            hazard_overlap_ratio=0.0,
            intersecting_hazard_count=0,
            flooded_length_m=0.0,
            total_length_m=0.0,
            recommendation="Route is too short to assess.",
        )

    total_length = 0.0
    flooded_length = 0.0
    intersecting_edge_count = 0

    for u, v in pairwise(route_nodes):
        edge_bundle = graph.get_edge_data(u, v)
        if not edge_bundle:
            continue

        chosen_edge = min(
            edge_bundle.values(),
            key=lambda data: _edge_length(data, _edge_geometry(graph, u, v, data), base_weight),
        )
        geometry = _edge_geometry(graph, u, v, chosen_edge)
        edge_length = _edge_length(chosen_edge, geometry, base_weight)
        overlap_ratio, hazard_count, _, _ = _geometry_risk_stats(geometry, hazard_gdf)

        total_length += edge_length
        flooded_length += edge_length * overlap_ratio
        if hazard_count > 0:
            intersecting_edge_count += 1

    overlap_ratio = flooded_length / total_length if total_length > 0 else 0.0
    rain_boost = rainfall_multiplier(rainfall_mm_per_hour)
    risk_score = min(1.0, overlap_ratio * rain_boost)

    return FloodRiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level_from_score(risk_score),
        rainfall_multiplier=rain_boost,
        hazard_overlap_ratio=overlap_ratio,
        intersecting_hazard_count=intersecting_edge_count,
        flooded_length_m=flooded_length,
        total_length_m=total_length,
        recommendation=recommendation_from_score(risk_score),
    )


def build_flood_penalized_graph(
    graph: Any,
    hazard_gdf: Any,
    rainfall_mm_per_hour: float | int | None = None,
    base_weight: str = "length",
    penalty_multiplier: float = 20.0,
    hard_block_threshold: float = 0.80,
    blocked_weight: float = 1e9,
) -> Any:
    """Create a rerouting graph where flooded edges become expensive."""

    penalized = graph.copy()
    rain_boost = rainfall_multiplier(rainfall_mm_per_hour)

    for u, v, key, data in penalized.edges(keys=True, data=True):
        geometry = _edge_geometry(penalized, u, v, data)
        overlap_ratio, hazard_count, _, _ = _geometry_risk_stats(geometry, hazard_gdf)
        flood_score = min(1.0, overlap_ratio * rain_boost)
        data["flood_risk_score"] = flood_score
        data["flood_hazard_count"] = hazard_count

        base_cost = _edge_length(data, geometry, base_weight)
        if flood_score >= hard_block_threshold:
            data["flood_blocked"] = True
            data["_flood_route_weight"] = base_cost * blocked_weight
        else:
            data["flood_blocked"] = False
            data["_flood_route_weight"] = base_cost * (1.0 + penalty_multiplier * flood_score)

    return penalized


def reroute_with_flood_avoidance(
    graph: Any,
    source: Any,
    target: Any,
    hazard_gdf: Any,
    rainfall_mm_per_hour: float | int | None = None,
    base_weight: str = "length",
    route_weight: str = "_flood_route_weight",
    penalty_multiplier: float = 20.0,
    hard_block_threshold: float = 0.80,
) -> RerouteResult:
    """Return a flood-aware shortest path and the risk summary for that path."""

    nx = _import_networkx()

    penalized_graph = build_flood_penalized_graph(
        graph,
        hazard_gdf,
        rainfall_mm_per_hour=rainfall_mm_per_hour,
        base_weight=base_weight,
        penalty_multiplier=penalty_multiplier,
        hard_block_threshold=hard_block_threshold,
    )

    original_path = nx.shortest_path(graph, source=source, target=target, weight=base_weight)
    original_cost = float(nx.shortest_path_length(graph, source=source, target=target, weight=base_weight))

    try:
        rerouted_path = nx.shortest_path(penalized_graph, source=source, target=target, weight=route_weight)
        rerouted_cost = float(nx.shortest_path_length(penalized_graph, source=source, target=target, weight=route_weight))
    except nx.NetworkXNoPath:
        rerouted_path = original_path
        rerouted_cost = original_cost

    assessment = assess_route_risk(
        graph,
        rerouted_path,
        hazard_gdf,
        rainfall_mm_per_hour=rainfall_mm_per_hour,
        base_weight=base_weight,
    )

    avoided_edges = sum(
        1
        for _, _, _, data in penalized_graph.edges(keys=True, data=True)
        if data.get("flood_blocked")
    )

    return RerouteResult(
        original_path=list(original_path),
        rerouted_path=list(rerouted_path),
        original_cost=original_cost,
        rerouted_cost=rerouted_cost,
        avoided_edges=avoided_edges,
        assessment=assessment,
    )


def hazard_to_route_summary(
    graph: Any,
    route_nodes: Iterable[Any],
    hazard_source: str | Path | None = None,
    rainfall_mm_per_hour: float | int | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for notebooks and API endpoints."""

    hazard_gdf = load_flood_hazard_map(hazard_source)
    assessment = assess_route_risk(graph, route_nodes, hazard_gdf, rainfall_mm_per_hour=rainfall_mm_per_hour)
    return assessment.to_dict()
