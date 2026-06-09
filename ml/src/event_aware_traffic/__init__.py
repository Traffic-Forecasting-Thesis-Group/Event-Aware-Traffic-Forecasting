from .bigquery import build_gdelt_query, query_recent_gdelt_events
from .flood_risk import (
    FloodRiskAssessment,
    RerouteResult,
    assess_place_risk,
    assess_route_risk,
    build_flood_penalized_graph,
    hazard_to_route_summary,
    load_flood_hazard_map,
    reroute_with_flood_avoidance,
)
from .fusion import (
    default_distilbert_severity_score,
    extract_domain_from_url,
    fuse_structured_and_unstructured_events,
    mention_multiplier,
    normalize_domain,
    normalize_url,
    trust_score_for_domain,
)
from .spatial import extract_driving_graph_from_pbf, graph_to_adjacency_matrix
