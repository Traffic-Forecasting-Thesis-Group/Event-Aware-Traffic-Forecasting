from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import numpy as np

if TYPE_CHECKING:
    import networkx as nx


def _normalize_bbox(bbox: Sequence[float] | dict | None) -> tuple[float, float, float, float]:
    if bbox is None:
        return (120.88, 14.35, 121.08, 15.05)

    if isinstance(bbox, dict):
        return (
            float(bbox["west"]),
            float(bbox["south"]),
            float(bbox["east"]),
            float(bbox["north"]),
        )

    if len(bbox) != 4:
        raise ValueError("bbox must contain four values: (west, south, east, north)")

    return tuple(float(value) for value in bbox)  # type: ignore[return-value]


def extract_driving_graph_from_pbf(
    pbf_file_path: str,
    bbox: Sequence[float] | dict | None = (120.90, 14.33, 121.13, 14.78),
    retain_edge_attributes: Sequence[str] = ("highway", "oneway", "lanes", "maxspeed"),
) -> "nx.MultiDiGraph":
    try:
        import networkx as nx
        import osmnx as ox
    except Exception as exception:
        raise RuntimeError("Install osmnx and networkx to extract a driving graph from OSM data") from exception

    pbf_path = Path(pbf_file_path)
    if not pbf_path.exists():
        raise FileNotFoundError(f"OSM PBF file not found: {pbf_file_path}")

    west, south, east, north = _normalize_bbox(bbox)
    print("Loading OSM road network for Metro Manila")
    print(f"Bounding box: west={west}, south={south}, east={east}, north={north}")

    try:
        import pyrosm  # type: ignore

        osm = pyrosm.OSM(str(pbf_path))
        result = osm.get_network(
            network_type="driving",
            bbox=(west, south, east, north),
            extra_attributes=list(retain_edge_attributes or []),
        )

        if isinstance(result, tuple) and len(result) == 2:
            edges_gdf, nodes_gdf = result
            if retain_edge_attributes:
                keep = [column for column in retain_edge_attributes if column in edges_gdf.columns]
                edges_gdf = edges_gdf[["geometry", *keep]]
            graph = ox.graph_from_gdfs(nodes_gdf, edges_gdf, retain_all=False)
            print(f"Done - graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
            return graph
    except Exception:
        pass

    graph = ox.graph_from_bbox(
        bbox=(north, south, east, west),
        network_type="drive",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
    )

    print(f"Done - graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    return graph


def graph_to_adjacency_matrix(G, weight: str | None = None, sparse: bool = True):
    
    try:         
        import networkx as nx
    except Exception: 
        raise RuntimeError("Install networkx to convert graph to adjacency matrix") 
    node_list = list(G.nodes)
    if sparse:
        try:
            from networkx import to_scipy_sparse_array as nx_sparse_array
            A = nx_sparse_array(G, nodelist=node_list, weight=weight, format="csr")
        except Exception:
            try: 
                from networkx import to_scipy_sparse_matrix as nx_sparse_matrix
                A = nx_sparse_matrix(G, nodelist=node_list, weight=weight, format="csr")
            except Exception:
                import scipy.sparse as sp
                
                row = []
                col = []
                data = []
                for i, u in enumerate(node_list):
                    for v, attrs in G[u].items():
                        j = node_list.index(v)
                        # In MultiDiGraph, attrs is dict-of-dict; handle both
                        if isinstance(attrs, dict) and any(isinstance(val, dict) for val in attrs.values()):
                            # Multi edges
                            for key, ed in attrs.items():
                                w = ed.get(weight, 1.0) if weight else 1.0
                                row.append(i)
                                col.append(j)
                                data.append(w)
                        else:
                            w = attrs.get(weight, 1.0) if weight else 1.0
                            row.append(i)
                            col.append(j)
                            data.append(w)
                A = sp.csr_matrix((data, (row, col)), shape=(len(node_list), len(node_list)))
        return A, node_list
    else:
        try:
            from networkx import to_numpy_array
            A = to_numpy_array(G, nodelist=node_list, weight=weight)
            return np.asarray(A), node_list
        except Exception:
            # fallback manual dense
            n = len(node_list)
            A = np.zeros((n, n), dtype=float)
            idx = {node: i for i, node in enumerate(node_list)}
            for u, v, data in G.edges(data=True):
                i = idx[u]
                j = idx[v]
                w = float(data.get(weight, 1.0)) if weight else 1.0
                A[i, j] += w
            return A, node_list


def load_spatial_grid(
    graph_path: str,
    adjacency_matrix_path: str | None = None,
    node_list_path: str | None = None,
):
    import pickle
    import scipy.sparse as sp

    with open(graph_path, "rb") as graph_file:
        graph = pickle.load(graph_file)

    adjacency_matrix = None
    if adjacency_matrix_path:
        adjacency_matrix = sp.load_npz(adjacency_matrix_path)

    node_list = None
    if node_list_path:
        node_list = np.load(node_list_path, allow_pickle=True)

    return graph, adjacency_matrix, node_list