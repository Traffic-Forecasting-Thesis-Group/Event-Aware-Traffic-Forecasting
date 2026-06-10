from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Index, Text, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from geoalchemy2 import Geometry

Base = declarative_base()
 
class RoadNode(Base):
    __tablename__ = "road_nodes"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String(64), unique=True, nullable=True, index=True)   
    name = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)                              
    district = Column(String(100), nullable=True)

    # PostGIS Point geometry
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Node classification
    node_type = Column(String(50), default="intersection")  
    is_signal = Column(Boolean, default=False)              
    road_class = Column(String(50), nullable=True)          

    # Graph WaveNet node index
    graph_index = Column(Integer, nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra = Column(JSON, nullable=True)

    # Relationships
    outgoing_edges = relationship("RoadEdge", foreign_keys="RoadEdge.source_node_id", back_populates="source_node")
    incoming_edges = relationship("RoadEdge", foreign_keys="RoadEdge.target_node_id", back_populates="target_node")
    traffic_observations = relationship("TrafficObservation", back_populates="node")
    predictions = relationship("SpatialPrediction", back_populates="node")

    __table_args__ = (
        Index("idx_road_nodes_geom", "geom", postgresql_using="gist"),
        Index("idx_road_nodes_city", "city"),
        Index("idx_road_nodes_graph_index", "graph_index"),
    )

    def __repr__(self):
        return f"<RoadNode id={self.id} osm={self.osm_id} city={self.city}>"

class RoadEdge(Base):
    __tablename__ = "road_edges"

    id = Column(Integer, primary_key=True, index=True)
    osm_way_id = Column(String(64), nullable=True, index=True)

    source_node_id = Column(Integer, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False)

    # PostGIS LineString geometry
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=True)

    # Physical attributes
    length_m = Column(Float, nullable=False)                
    speed_limit_kph = Column(Float, nullable=True)
    lanes = Column(Integer, default=1)
    road_class = Column(String(50), nullable=True)
    is_oneway = Column(Boolean, default=False)
    is_bridge = Column(Boolean, default=False)
    is_tunnel = Column(Boolean, default=False)

    # Spatial weight for adjacency matrix
    spatial_weight = Column(Float, default=1.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra = Column(JSON, nullable=True)

    # Relationships
    source_node = relationship("RoadNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("RoadNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

    __table_args__ = (
        Index("idx_road_edges_geom", "geom", postgresql_using="gist"),
        Index("idx_road_edges_source", "source_node_id"),
        Index("idx_road_edges_target", "target_node_id"),
        Index("idx_road_edges_pair", "source_node_id", "target_node_id", unique=True),
    )

    def __repr__(self):
        return f"<RoadEdge {self.source_node_id} → {self.target_node_id} ({self.length_m:.0f}m)>"