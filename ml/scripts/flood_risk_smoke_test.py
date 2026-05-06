from __future__ import annotations

from pathlib import Path
import sys

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from event_aware_traffic.flood_risk import (  # noqa: E402
    assess_place_risk,
    assess_route_risk,
    build_flood_penalized_graph,
    load_flood_hazard_map,
    reroute_with_flood_avoidance,
)


def build_toy_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=120.98, y=14.60)
    graph.add_node(2, x=120.99, y=14.61)
    graph.add_node(3, x=121.00, y=14.62)
    graph.add_edge(1, 2, length=1200.0)
    graph.add_edge(2, 3, length=900.0)
    graph.add_edge(1, 3, length=2500.0)
    return graph


def main() -> None:
    hazard_root = ROOT / "data" / "raw" / "MetroManila"
    hazard_gdf = load_flood_hazard_map(hazard_root)

    place = assess_place_risk(120.98, 14.60, hazard_gdf, rainfall_mm_per_hour=18)
    print("Place risk:", place.to_dict())

    graph = build_toy_graph()
    penalized = build_flood_penalized_graph(graph, hazard_gdf, rainfall_mm_per_hour=18)
    route = [1, 2, 3]
    route_assessment = assess_route_risk(penalized, route, hazard_gdf, rainfall_mm_per_hour=18)
    print("Route risk:", route_assessment.to_dict())

    reroute = reroute_with_flood_avoidance(graph, 1, 3, hazard_gdf, rainfall_mm_per_hour=18)
    print("Reroute result:", reroute.to_dict())


if __name__ == "__main__":
    main()