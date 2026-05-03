from __future__ import annotations
from typing import Sequence, Tuple

import math
import warnings

import numpy as np 

def extract_driving_graph_from_pbf(
    pbf_file_path: str,
    bbox : Sequence[float] = (120.90, 14.33, 121.13, 14.78),
    retain_edge_attributes: Sequence[str] = ("highway", "oneway", "lanes", "maxspeed"),
) -> "networkx.MultiDiGraph":
    try:
        import osmnx as ox
        import pyrosm
        import geopandas as gpd
        import networkx as nx 
    except Exception as exception:
        raise RuntimeError("Install osmnx, pyrosm, geopandas, and networkx to extract driving graph from PBF") from exception
    
    print("Opening PBF file - Reading Metro Manila BBOX")
    osm = pyrosm.OSM(pbf_file_path)
    
    try: 
        result = osm.get_network(network_type="driving", bbox=bbox, extra_attributes=list(retain_edge_attributes or []))
    except TypeError:
        data = osm.get_data_by_bbox( bbox, keep_ways=True)
        result = osm.get_network(network_type="driving", extra_attributes=list(retain_edge_attributes or []))
        
    if isinstance(result, tuple) and len(result) == 2:
        edges_gdf, nodes_gdf = result
    else: 
        edges_gdf = result
        print("Building nodes GeoDataFrame from edges")
        try:
            from shapely.geometry import Point

            endpoints = []
            for geom in edges_gdf.geometry:
                if geom is None:
                    continue
                try:
                    coords = list(geom.coords)
                except Exception:
                    try:
                        coords = list(geom.geoms[0].coords)
                    except Exception:
                        continue
                if coords:
                    endpoints.append(coords[0])
                    endpoints.append(coords[-1])

            unique_coords = { (float(x), float(y)) for (x, y) in endpoints }
            nodes_gdf = gpd.GeoDataFrame(
                {"osmid": list(range(len(unique_coords)))},
                geometry=[Point(x, y) for (x, y) in unique_coords],
                crs="EPSG:4326",
            )
        except Exception:
            raise RuntimeError("Unable to synthesize nodes from edges; upgrade pyrosm or provide nodes.")
        
    edges_gdf = edges_gdf[~edges_gdf.geometry.is_empty].copy()
    edges_gdf.reset_index(drop=True, inplace=True)
    
    if retain_edge_attrs:
        keep = [c for c in retain_edge_attrs if c in edges_gdf.columns]
        keep = ["geometry"] + keep
        edges_gdf = edges_gdf[[c for c in edges_gdf.columns if c in keep]]

    print(f"Extracted edges: {len(edges_gdf)}; nodes: {len(nodes_gdf)} (approx). Converting to NetworkX...")
    try:
        G = ox.graph_from_gdfs(nodes_gdf, edges_gdf, retain_all=False)
    except Exception:
        import networkx as nx

        G = nx.MultiDiGraph()
        for idx, row in edges_gdf.iterrows():
            # attempt to find start/end coords
            geom = row.geometry
            try:
                coords = list(geom.coords)
            except Exception:
                try:
                    coords = list(geom.geoms[0].coords)
                except Exception:
                    continue
            u_coord = (float(coords[0][1]), float(coords[0][0]))
            v_coord = (float(coords[-1][1]), float(coords[-1][0]))
            u = hash(u_coord)
            v = hash(v_coord)
            G.add_node(u, y=u_coord[0], x=u_coord[1])
            G.add_node(v, y=v_coord[0], x=v_coord[1])
            attr = {k: row[k] for k in row.index if k != "geometry"}
            G.add_edge(u, v, **attr)

    node_count = len(G.nodes)
    edge_count = len(G.edges)
    print(f"Done — graph has {node_count} nodes and {edge_count} edges.")
    return G


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