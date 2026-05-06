"""
Utility script to generate and cache spatial graphs from OSM data.
Run this locally to prepare the spatial grid for Graph WaveNet input.
"""

import pickle
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

# Add ml module to path
ml_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(ml_path))

from event_aware_traffic.spatial import (
    extract_driving_graph_from_pbf,
    graph_to_adjacency_matrix,
)


def main():
    """Generate spatial graph from OSM Philippines data."""
    
    # Paths
    pbf_path = Path(__file__).parent.parent / "data" / "raw" / "OSM" / "philippines-260503.osm.pbf"
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts" / "spatial_grid"
    
    print("\n" + "="*80)
    print("OSM SPATIAL GRAPH GENERATION UTILITY")
    print("="*80)
    
    # Validate input
    if not pbf_path.exists():
        print(f"\n❌ ERROR: PBF file not found at {pbf_path}")
        print(f"   Please download OSM data from: https://download.geofabrik.de/asia/philippines-latest.osm.pbf")
        print(f"   And place it at: {pbf_path}")
        return False
    
    print(f"\n✓ PBF file found: {pbf_path}")
    print(f"  File size: {pbf_path.stat().st_size / 1e6:.1f} MB")
    
    # Create artifacts directory
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Artifacts directory ready: {artifacts_dir}")
    
    # Default Metro Manila bounding box
    bbox = {
        "north": 15.05,
        "south": 14.35,
        "east": 121.08,
        "west": 120.88,
    }
    
    print(f"\n📍 Extracting road network for Metro Manila")
    print(f"   Bounding box: N={bbox['north']}, S={bbox['south']}, E={bbox['east']}, W={bbox['west']}")
    
    try:
        print("   Parsing PBF and filtering by bbox...")
        G = extract_driving_graph_from_pbf(str(pbf_path), bbox=bbox)
        
        nodes_count = G.number_of_nodes()
        edges_count = G.number_of_edges()
        
        print(f"\n✓ Graph extracted successfully!")
        print(f"   Nodes: {nodes_count:,}")
        print(f"   Edges: {edges_count:,}")
        
        if nodes_count == 0:
            print("\n❌ ERROR: Graph has no nodes. Check PBF content or bounding box.")
            return False
        
        # Generate adjacency matrix
        print(f"\n🔄 Generating sparse adjacency matrix...")
        A, node_list = graph_to_adjacency_matrix(G, sparse=True)
        
        print(f"✓ Adjacency matrix created!")
        print(f"   Shape: {A.shape}")
        print(f"   Sparsity: {1 - A.nnz / (A.shape[0] * A.shape[1]):.2%}")
        print(f"   Non-zero elements: {A.nnz:,}")
        
        # Save graph
        graph_path = artifacts_dir / "road_network_graph.pkl"
        print(f"\n💾 Saving graph to {graph_path}...")
        with open(graph_path, "wb") as f:
            pickle.dump(G, f)
        print(f"✓ Graph saved ({graph_path.stat().st_size / 1e6:.1f} MB)")
        
        # Save adjacency matrix
        adj_matrix_path = artifacts_dir / "adjacency_matrix.npz"
        print(f"\n💾 Saving adjacency matrix to {adj_matrix_path}...")
        sp.save_npz(str(adj_matrix_path), A)
        print(f"✓ Adjacency matrix saved ({adj_matrix_path.stat().st_size / 1e6:.1f} MB)")
        
        # Save node list
        nodes_path = artifacts_dir / "node_list.npy"
        print(f"\n💾 Saving node list to {nodes_path}...")
        np.save(str(nodes_path), node_list)
        print(f"✓ Node list saved ({nodes_path.stat().st_size / 1e6:.1f} MB)")
        
        # Save metadata
        metadata = {
            "nodes_count": nodes_count,
            "edges_count": edges_count,
            "bbox": bbox,
            "source": "OSM Philippines",
            "format": "NetworkX MultiDiGraph",
            "adjacency_matrix_format": "SciPy CSR sparse",
        }
        
        import json
        metadata_path = artifacts_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Metadata saved to {metadata_path}")
        print(f"\n" + "="*80)
        print("SUCCESS! Spatial grid is ready for Graph WaveNet input.")
        print("="*80)
        print(f"\nArtifacts location: {artifacts_dir}")
        print(f"\nUsage in ML pipeline:")
        print(f"  from event_aware_traffic.spatial import load_spatial_grid")
        print(f"  G = pickle.load(open('{graph_path}', 'rb'))")
        print(f"  A = sp.load_npz('{adj_matrix_path}')")
        print(f"  nodes = np.load('{nodes_path}')")
        print()
        
        return True
    
    except Exception as e:
        print(f"\n❌ ERROR during graph generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
