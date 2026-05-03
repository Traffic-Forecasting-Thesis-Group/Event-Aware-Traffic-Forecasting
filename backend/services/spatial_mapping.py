from __future__ import annotations
import asyncio
import logging
import time
from typing import List, Optional, Tuple

import numpy as np
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from geoalchemy2.shape import to_shape

from models.road_graph import RoadNode, RoadEdge
from schemas import (
    RoadNodeCreate, RoadNodeUpdate, RoadEdgeCreate,
    GraphBuildRequest, AdjacencyMatrixResponse, GraphStats,
    BulkImportResult,
)
from utils.cache import (
    cache_get, cache_set, cache_delete_pattern,
    key_adjacency_matrix, key_graph_stats,
    TTL_ADJACENCY_MATRIX, TTL_GRAPH_STATS,
)

logger = logging.getLogger(__name__)

class SpatialMappingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Node CRUD
    async def create_node(self, data: RoadNodeCreate) -> RoadNode:
        geom_wkt = f"SRID=4326;POINT({data.longitude} {data.latitude})"
        node = RoadNode(
            **data.model_dump(exclude_none=True),
            geom=geom_wkt,
        )
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        await cache_delete_pattern("module3:adjacency:*")
        return node

    async def get_node(self, node_id: int) -> Optional[RoadNode]:
        result = await self.db.execute(select(RoadNode).where(RoadNode.id == node_id))
        return result.scalar_one_or_none()

    async def update_node(self, node_id: int, data: RoadNodeUpdate) -> Optional[RoadNode]:
        node = await self.get_node(node_id)
        if node is None:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(node, field, value)
        await self.db.flush()
        return node

    async def list_nodes(
        self,
        city: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RoadNode]:
        q = select(RoadNode)
        if city:
            q = q.where(RoadNode.city == city)
        q = q.limit(limit).offset(offset).order_by(RoadNode.id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def nodes_within_radius(
        self,
        lat: float,
        lon: float,
        radius_m: float,
    ) -> List[RoadNode]:
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        q = select(RoadNode).where(
            ST_DWithin(
                func.Geography(RoadNode.geom),
                func.Geography(point),
                radius_m,
            )
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # Edge CRUD
    async def create_edge(self, data: RoadEdgeCreate) -> RoadEdge:
        edge = RoadEdge(**data.model_dump(exclude_none=True))
        self.db.add(edge)
        await self.db.flush()
        await cache_delete_pattern("module3:adjacency:*")
        return edge

    async def bulk_create_edges(self, edges: List[RoadEdgeCreate]) -> int:
        db_edges = [RoadEdge(**e.model_dump(exclude_none=True)) for e in edges]
        self.db.add_all(db_edges)
        await self.db.flush()
        await cache_delete_pattern("module3:adjacency:*")
        return len(db_edges)

    # Graph Construction & Adjacency Matrix
    async def build_adjacency_matrix(
        self,
        request: GraphBuildRequest,
    ) -> AdjacencyMatrixResponse:
        cache_key = key_adjacency_matrix(request.city_filter)
        cached = await cache_get(cache_key)
        if cached:
            logger.info("Adjacency matrix served from cache.")
            return AdjacencyMatrixResponse(**cached)

        # Fetch nodes
        q = select(RoadNode).where(RoadNode.graph_index.isnot(None))
        if request.city_filter:
            q = q.where(RoadNode.city.in_(request.city_filter))
        if request.bbox:
            min_lon, min_lat, max_lon, max_lat = request.bbox
            q = q.where(
                func.ST_Within(
                    RoadNode.geom,
                    func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326),
                )
            )
        if request.max_nodes:
            q = q.limit(request.max_nodes)
 
        node_result = await self.db.execute(q)
        nodes: List[RoadNode] = list(node_result.scalars().all())

        graph_index_to_node_id = {n.graph_index: n.id for n in nodes}
        node_id_to_graph_index = {n.id: n.graph_index for n in nodes}
        node_ids = [n.id for n in nodes]

        if not node_ids:
            return AdjacencyMatrixResponse(
                node_count=0,
                graph_index_to_node_id={},
                edges=[],
                stats=GraphStats(
                    node_count=0, edge_count=0, avg_degree=0.0,
                    density=0.0, cities_covered=[], bbox=[],
                ),
            )

        # Fetch edges between these nodes
        edge_q = select(RoadEdge).where(
            RoadEdge.source_node_id.in_(node_ids),
            RoadEdge.target_node_id.in_(node_ids),
        )
        edge_result = await self.db.execute(edge_q)
        edges: List[RoadEdge] = list(edge_result.scalars().all())

        # Build sparse edge list
        sparse_edges = []
        for e in edges:
            src_idx = node_id_to_graph_index.get(e.source_node_id)
            tgt_idx = node_id_to_graph_index.get(e.target_node_id)
            if src_idx is not None and tgt_idx is not None:
                w = e.spatial_weight if request.include_weights else 1.0
                sparse_edges.append([float(src_idx), float(tgt_idx), float(w)])

        # Stats
        cities = list({n.city for n in nodes if n.city})
        lats = [n.latitude for n in nodes]
        lons = [n.longitude for n in nodes]
        bbox = [min(lons), min(lats), max(lons), max(lats)] if lons else []
        n = len(nodes)
        avg_degree = (len(sparse_edges) * 2) / n if n > 0 else 0.0
        density = len(sparse_edges) / (n * (n - 1)) if n > 1 else 0.0

        stats = GraphStats(
            node_count=n,
            edge_count=len(sparse_edges),
            avg_degree=round(avg_degree, 2),
            density=round(density, 6),
            cities_covered=sorted(cities),
            bbox=bbox,
        )

        response = AdjacencyMatrixResponse(
            node_count=n,
            graph_index_to_node_id={str(k): v for k, v in graph_index_to_node_id.items()},
            edges=sparse_edges,
            stats=stats,
        )

        await cache_set(cache_key, response.model_dump(), TTL_ADJACENCY_MATRIX)
        logger.info(f"Built adjacency matrix: {n} nodes, {len(sparse_edges)} edges.")
        return response

    async def assign_graph_indices(self, city_filter: Optional[List[str]] = None) -> int:
        q = select(RoadNode)
        if city_filter:
            q = q.where(RoadNode.city.in_(city_filter))
        q = q.order_by(RoadNode.id)
        result = await self.db.execute(q)
        nodes = list(result.scalars().all())

        for idx, node in enumerate(nodes):
            node.graph_index = idx
        await self.db.flush()
        await cache_delete_pattern("module3:adjacency:*")
        logger.info(f"Assigned graph indices to {len(nodes)} nodes.")
        return len(nodes)

    # OSM Data Import
    async def import_from_overpass(
        self,
        city: str,
        dry_run: bool = False,
    ) -> BulkImportResult:
        import httpx
        from shapely.geometry import Point

        # Build Overpass QL for Metro Manila road network
        query = f"""
        [out:json][timeout:60];
        area["name"="{city}"]["admin_level"~"6|7|8"]->.search_area;
        (
          way["highway"~"motorway|trunk|primary|secondary|tertiary|residential"]
             (area.search_area);
        );
        out body;
        >;
        out skel qt;
        """

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            resp.raise_for_status()
            osm_data = resp.json()

        nodes_raw = {e["id"]: e for e in osm_data["elements"] if e["type"] == "node"}
        ways = [e for e in osm_data["elements"] if e["type"] == "way"]

        nodes_inserted = nodes_skipped = edges_inserted = edges_skipped = 0
        errors = []

        if dry_run:
            return BulkImportResult(
                nodes_inserted=len(nodes_raw),
                nodes_skipped=0,
                edges_inserted=sum(max(len(w["nodes"]) - 1, 0) for w in ways),
                edges_skipped=0,
                errors=[],
                duration_seconds=round(time.monotonic() - t0, 2),
            )

        # Insert nodes
        osm_id_to_db_id: dict[str, int] = {}
        for osm_node in nodes_raw.values():
            osm_id = str(osm_node["id"])
            lat, lon = osm_node["lat"], osm_node["lon"]
            existing = await self.db.execute(
                select(RoadNode).where(RoadNode.osm_id == osm_id)
            )
            if existing.scalar_one_or_none():
                nodes_skipped += 1
                continue
            try:
                node_data = RoadNodeCreate(
                    osm_id=osm_id,
                    city=city,
                    latitude=lat,
                    longitude=lon,
                    node_type="waypoint",
                )
                db_node = await self.create_node(node_data)
                osm_id_to_db_id[osm_id] = db_node.id
                nodes_inserted += 1
            except Exception as exc:
                errors.append(f"Node {osm_id}: {exc}")

        # Insert edges 
        from geopy.distance import geodesic

        for way in ways:
            way_node_ids = [str(nid) for nid in way.get("nodes", [])]
            tags = way.get("tags", {})
            road_class = tags.get("highway", "unclassified")
            speed_limit = self._parse_maxspeed(tags.get("maxspeed"))
            lanes = int(tags.get("lanes", 1))
            is_oneway = tags.get("oneway", "no") == "yes"

            for i in range(len(way_node_ids) - 1):
                src_osm = way_node_ids[i]
                tgt_osm = way_node_ids[i + 1]
                src_id = osm_id_to_db_id.get(src_osm)
                tgt_id = osm_id_to_db_id.get(tgt_osm)
                if not src_id or not tgt_id:
                    edges_skipped += 1
                    continue

                src_node = nodes_raw.get(int(src_osm))
                tgt_node = nodes_raw.get(int(tgt_osm))
                if not src_node or not tgt_node:
                    edges_skipped += 1
                    continue

                dist = geodesic(
                    (src_node["lat"], src_node["lon"]),
                    (tgt_node["lat"], tgt_node["lon"]),
                ).meters

                try:
                    edge_data = RoadEdgeCreate(
                        osm_way_id=str(way["id"]),
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        length_m=dist,
                        speed_limit_kph=speed_limit,
                        lanes=lanes,
                        road_class=road_class,
                        is_oneway=is_oneway,
                        spatial_weight=self._compute_spatial_weight(dist, road_class),
                    )
                    await self.create_edge(edge_data)
                    edges_inserted += 1
                except Exception as exc:
                    errors.append(f"Edge {src_osm}→{tgt_osm}: {exc}")

        duration = round(time.monotonic() - t0, 2)
        return BulkImportResult(
            nodes_inserted=nodes_inserted,
            nodes_skipped=nodes_skipped,
            edges_inserted=edges_inserted,
            edges_skipped=edges_skipped,
            errors=errors[:50],
            duration_seconds=duration,
        )

    @staticmethod
    def _parse_maxspeed(raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        try:
            return float(raw.replace("kph", "").replace("km/h", "").strip())
        except ValueError:
            return None

    @staticmethod
    def _compute_spatial_weight(length_m: float, road_class: str) -> float:
        hierarchy = {
            "motorway": 1.5, "trunk": 1.3, "primary": 1.2,
            "secondary": 1.0, "tertiary": 0.8,
        }
        h = hierarchy.get(road_class, 0.6)
        return round(h / (1 + length_m / 1000), 4)