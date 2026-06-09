"""
Integration test for OSM spatial mapping and flood-aware routing.
Demonstrates the complete workflow: OSM graph → adjacency matrix → flood risk assessment.
"""

import pickle
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import scipy.sparse as sp

# Add ml module to path
ml_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(ml_path))

from event_aware_traffic.spatial import (
    extract_driving_graph_from_pbf,
    graph_to_adjacency_matrix,
)
from event_aware_traffic.flood_risk import (
    load_flood_hazard_map,
    assess_place_risk,
    assess_route_risk,
    build_flood_penalized_graph,
    reroute_with_flood_avoidance,
)


def test_osm_graph_generation():
    """Test OSM graph extraction and adjacency matrix generation."""
    print("\n" + "="*80)
    print("TEST 1: OSM GRAPH GENERATION")
    print("="*80)
    
    pbf_path = Path(__file__).parent.parent / "data" / "raw" / "OSM" / "philippines-260503.osm.pbf"
    
    if not pbf_path.exists():
        print(f"❌ SKIP: PBF file not found at {pbf_path}")
        return False
    
    bbox = {
        "north": 15.05,
        "south": 14.35,
        "east": 121.08,
        "west": 120.88,
    }
    
    try:
        print(f"\n1️⃣  Extracting driving graph from OSM PBF...")
        print(f"   Source: {pbf_path.name}")
        print(f"   Region: Metro Manila")
        
        G = extract_driving_graph_from_pbf(str(pbf_path), bbox=bbox)
        
        print(f"\n✓ Graph extracted!")
        print(f"   Nodes: {G.number_of_nodes():,}")
        print(f"   Edges: {G.number_of_edges():,}")
        print(f"   Graph type: {type(G).__name__}")
        
        # Inspect a sample node
        sample_nodes = list(G.nodes(data=True))[:1]
        if sample_nodes:
            node_id, attrs = sample_nodes[0]
            print(f"\n   Sample node {node_id}:")
            for key, val in list(attrs.items())[:3]:
                print(f"     {key}: {val}")
        
        print(f"\n2️⃣  Generating adjacency matrix...")
        A, node_list = graph_to_adjacency_matrix(G, sparse=True)
        
        print(f"\n✓ Adjacency matrix created!")
        print(f"   Shape: {A.shape}")
        print(f"   Type: {type(A).__name__}")
        print(f"   Sparsity: {1 - A.nnz / (A.shape[0] * A.shape[1]):.2%}")
        print(f"   Non-zero: {A.nnz:,}")
        print(f"   Node list length: {len(node_list)}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_flood_risk_integration():
    """Test flood risk assessment on spatial data."""
    print("\n" + "="*80)
    print("TEST 2: FLOOD RISK ASSESSMENT (Integration)")
    print("="*80)
    
    flood_path = Path(__file__).parent.parent / "data" / "raw" / "MetroManila"
    
    if not flood_path.exists():
        print(f"❌ SKIP: Flood hazard maps not found at {flood_path}")
        print(f"   Please download Project NOAH shapefiles to this location.")
        return False
    
    try:
        print(f"\n1️⃣  Loading flood hazard map...")
        hazard_gdf = load_flood_hazard_map(flood_path)
        
        print(f"\n✓ Hazard map loaded!")
        print(f"   Polygons: {len(hazard_gdf)}")
        print(f"   CRS: {hazard_gdf.crs}")
        print(f"   Bounds: {hazard_gdf.total_bounds}")
        
        # Test place risk assessment
        print(f"\n2️⃣  Assessing place risk (Marikina, rainfall=18mm/hr)...")
        test_loc = {"lon": 121.5768, "lat": 14.6474}  # Marikina, flood-prone area
        
        risk = assess_place_risk(
            lon=test_loc["lon"],
            lat=test_loc["lat"],
            hazard_gdf=hazard_gdf,
            rainfall_mm_per_hour=18.0,
        )
        
        print(f"\n✓ Risk assessment complete!")
        print(f"   Risk score: {risk.risk_score:.2f}")
        print(f"   Risk level: {risk.risk_level}")
        print(f"   Recommendation: {risk.recommendation}")
        
        # Test safe location
        print(f"\n3️⃣  Assessing safe location (Makati, rainfall=18mm/hr)...")
        safe_loc = {"lon": 121.5707, "lat": 14.5554}  # Makati, safer area
        
        safe_risk = assess_place_risk(
            lon=safe_loc["lon"],
            lat=safe_loc["lat"],
            hazard_gdf=hazard_gdf,
            rainfall_mm_per_hour=18.0,
        )
        
        print(f"\n✓ Safe location assessment complete!")
        print(f"   Risk score: {safe_risk.risk_score:.2f}")
        print(f"   Risk level: {safe_risk.risk_level}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_flood_aware_routing():
    """Test flood-aware route optimization."""
    print("\n" + "="*80)
    print("TEST 3: FLOOD-AWARE ROUTING")
    print("="*80)
    
    pbf_path = Path(__file__).parent.parent / "data" / "raw" / "OSM" / "philippines-260503.osm.pbf"
    flood_path = Path(__file__).parent.parent / "data" / "raw" / "MetroManila"
    
    if not pbf_path.exists():
        print(f"❌ SKIP: PBF file not found")
        return False
    
    if not flood_path.exists():
        print(f"❌ SKIP: Flood hazard maps not found")
        return False
    
    try:
        print(f"\n1️⃣  Loading spatial data...")
        bbox = {
            "north": 15.05,
            "south": 14.35,
            "east": 121.08,
            "west": 120.88,
        }
        
        G = extract_driving_graph_from_pbf(str(pbf_path), bbox=bbox)
        hazard_gdf = load_flood_hazard_map(flood_path)
        
        print(f"   Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
        print(f"   Hazards: {len(hazard_gdf)} polygons")
        
        print(f"\n2️⃣  Building flood-penalized graph...")
        G_penalized = build_flood_penalized_graph(G, hazard_gdf, rainfall_mm_per_hour=18.0)
        
        print(f"✓ Penalized graph created")
        
        # Get a connected component for testing
        largest_cc = max(nx.weakly_connected_components(G_penalized), key=len)
        origin = list(largest_cc)[0]
        destination = list(largest_cc)[-1]
        
        print(f"\n3️⃣  Finding safe route...")
        print(f"   Origin node: {origin}")
        print(f"   Destination node: {destination}")
        
        reroute_result = reroute_with_flood_avoidance(
            G=G_penalized,
            origin_node=origin,
            destination_node=destination,
            hazard_gdf=hazard_gdf,
            rainfall_mm_per_hour=18.0,
        )
        
        print(f"\n✓ Route optimization complete!")
        print(f"   Original distance: {reroute_result.original_distance_m:,.0f} m")
        print(f"   Safe distance: {reroute_result.safe_distance_m:,.0f} m")
        print(f"   Distance increase: {reroute_result.distance_increase_percent:.1f}%")
        print(f"   Flooded length avoided: {reroute_result.flooded_length_m:,.0f} m")
        print(f"   Recommendation: {reroute_result.recommendation}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("OSM SPATIAL MAPPING & FLOOD-AWARE ROUTING INTEGRATION TESTS")
    print("="*80)
    
    results = {
        "Graph Generation": test_osm_graph_generation(),
        "Flood Risk Assessment": test_flood_risk_integration(),
        "Flood-Aware Routing": test_flood_aware_routing(),
    }
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ SKIP/FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*80)
    
    if all(results.values()):
        print("All tests passed! OSM integration is ready.")
        return True
    else:
        print("Some tests skipped or failed. Check requirements and data files.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
