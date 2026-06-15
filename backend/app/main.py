from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as redis
import torch
import numpy as np
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from .database import get_db_session, get_redis_connection, engine
from .event_pipeline import ingest_unstructured_events
from .structured_pipeline import build_baseline_d2stgnn_dataset as prepare_baseline_input
from .d2stgnn_external import D2STGNN
from .fusion import encode_events_to_embeddings, fuse_forecast_with_events
from .tomtom_routing import get_route_with_geometry, classify_congestion, TomTomRoutingError
from .auth_router import router as auth_router
from .auth_deps import get_current_user
from .models import Base, User

app = FastAPI()

app.include_router(auth_router)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class LocationPointSchema(BaseModel):
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None

class UserLocationsPayloadSchema(BaseModel):
    home: Optional[LocationPointSchema] = None
    work: Optional[LocationPointSchema] = None

@app.post("/api/user/locations")
async def save_user_locations(payload: UserLocationsPayloadSchema, current_user: User = Depends(get_current_user)):
    print(f"User {current_user.email} -> Home: {payload.home}, Work: {payload.work}")
    return {
        "status": "success",
        "message": "User home and work location contexts synchronized successfully."
    }

@app.get("/api/user/locations")
async def get_user_locations(current_user: User = Depends(get_current_user)):
    return {"home": None, "work": None}

@app.delete("/api/user/locations")
async def clear_user_locations(current_user: User = Depends(get_current_user)):
    return {"status": "success"}

@app.get("/api/geocode")
async def geocode_address_mock(address: str):
    print(f"Geocoding address string input: {address}")
    return {
        "lat": 14.5995,
        "lng": 120.9842,
        "formattedAddress": address
    }

_D2STGNN_DEFAULTS = dict(
    num_feat=4,
    num_hidden=512,
    node_hidden=64,
    time_emb_dim=64,
    seq_length=12,
    k_s=2,
    k_t=3,
    gap=1,
    day_in_week_size=7,
    time_in_day_size=288,
    dropout=0.1,
)

def _build_d2stgnn(num_nodes: int, adjs: list) -> D2STGNN:
    return D2STGNN(
        num_nodes=num_nodes,
        adjs=adjs,
        **_D2STGNN_DEFAULTS,
    )

@app.post("/api/events/ingest")
async def ingest_events(raw_events: list[dict]):
    return ingest_unstructured_events(raw_events)

@app.post("/api/structured/prepare")
async def prepare_structured(raw_structured_data: dict):
    result = prepare_baseline_input(raw_structured_data)
    return {
        "node_ids": result["node_ids"],
        "input_len": result["input_len"],
        "output_len": result["output_len"],
        "num_feat": result["num_feat"],
        "history_tensor": result["history_tensor"].tolist(),
        "adjacency_matrix": result["adjacency_matrix"].tolist(),
        "node_features": result["node_features"].tolist(),
    }

@app.post("/api/structured/d2stgnn")
async def run_d2stgnn(payload: dict):
    dataset = prepare_baseline_input(payload.get("structured_data", {}))
    history_np = dataset["history_tensor"]
    adjacency_np = dataset["adjacency_matrix"]
    num_nodes = adjacency_np.shape[0]
    input_len = dataset["input_len"]
    output_len = dataset["output_len"]
    num_feat = dataset.get("num_feat", 4)

    adj_tensor = torch.tensor(adjacency_np, dtype=torch.float32)
    k_s = _D2STGNN_DEFAULTS["k_s"]
    adjs = [adj_tensor for _ in range(k_s)]

    events_payload = payload.get("events", {"count": 0, "events": []})
    event_list = events_payload.get("events", []) or []
    c_dim = 256 * _D2STGNN_DEFAULTS["gap"] * _D2STGNN_DEFAULTS["seq_length"]
    event_emb_np = encode_events_to_embeddings(event_list, c_dim=c_dim, max_events=384)
    event_emb_tensor = torch.tensor(event_emb_np, dtype=torch.float32)

    history_tensor = torch.tensor(history_np, dtype=torch.float32).unsqueeze(0)
    future_tensor = torch.zeros(1, output_len, num_nodes, num_feat + 5, dtype=torch.float32)

    model = _build_d2stgnn(num_nodes=num_nodes, adjs=adjs)
    model.eval()
    with torch.no_grad():
        forecast_tensor = model(
            history_data=history_tensor,
            future_data=future_tensor,
            batch_seen=0,
            epoch=0,
            train=False,
            event_embeddings=event_emb_tensor,
        )
    forecast_np = forecast_tensor.cpu().numpy()
    fused_np = fuse_forecast_with_events(forecast_np, events_payload)

    return {
        "dataset": {
            "input_len": input_len,
            "output_len": output_len,
            "node_ids": dataset.get("node_ids"),
            "history_tensor": history_np.tolist(),
            "adjacency_matrix": adjacency_np.tolist(),
        },
        "forecast": fused_np.tolist(),
        "fusion_applied": True,
        "event_count": len(event_list),
        "traffic_events": sum(1 for e in event_list if e.get("traffic_related")),
    }

@app.get("/api/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_conn: redis.Redis = Depends(get_redis_connection),
):
    db_status = "error"
    redis_status = "error"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        print(f"DB connection failed: {e}")

    try:
        await redis_conn.ping()
        redis_status = "ok"
    except Exception as e:
        print(f"Redis connection failed: {e}")

    return {
        "database": db_status,
        "redis": redis_status,
    }

class RouteCalculationPayload(BaseModel):
    origin: str
    destination: str
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

@app.post("/api/route/calculate")
async def calculate_dynamic_route(payload: RouteCalculationPayload):
    if payload.origin_lat is None or payload.origin_lng is None \
            or payload.destination_lat is None or payload.destination_lng is None:
        raise HTTPException(
            status_code=422,
            detail="origin_lat/origin_lng/destination_lat/destination_lng are required."
        )

    try:
        route_info = await get_route_with_geometry(
            origin_lat=payload.origin_lat,
            origin_lng=payload.origin_lng,
            dest_lat=payload.destination_lat,
            dest_lng=payload.destination_lng,
        )
    except TomTomRoutingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    congestion = classify_congestion(
        distance_km=route_info["distance_km"],
        duration_minutes=route_info["duration_minutes"],
        traffic_delay_minutes=route_info["traffic_delay_minutes"],
    )

    if route_info["traffic_delay_minutes"] > 0:
        intelligence_note = (
            f"Live TomTom traffic data: ~{route_info['traffic_delay_minutes']} min "
            f"delay vs. free-flow conditions on this route."
        )
    else:
        intelligence_note = "Live TomTom traffic data: no significant delay detected."

    return {
        "duration_minutes": route_info["duration_minutes"],
        "distance_km": route_info["distance_km"],
        "primary_route": "Fastest route (live traffic)",
        "congestion": congestion,
        "intelligence_note": intelligence_note,
        "formatted_destination": payload.destination if payload.destination else "Selected Target Point",
        "route_geometry": route_info["route_geometry"],
    }
