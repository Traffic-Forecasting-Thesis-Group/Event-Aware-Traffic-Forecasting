from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as redis
import torch
import numpy as np

from .database import get_db_session, get_redis_connection
from .event_pipeline import ingest_unstructured_events
from .structured_model_adapter import prepare_baseline_input
from .d2stgnn_external import D2STGNN
from .fusion import encode_events_to_embeddings, fuse_forecast_with_events

app = FastAPI()

# ---------------------------------------------------------------------------
# Model configuration matching D2STGNN baseleine
# num_feat=4: speed, flow, density, valid_flag
# History tensor has 6 cols: 4 traffic features + time_of_day + day_of_week
# ---------------------------------------------------------------------------
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
    """Instantiate the full D2STGNN model for a given road graph."""
    return D2STGNN(
        num_nodes=num_nodes,
        adjs=adjs,
        **_D2STGNN_DEFAULTS,
    )


@app.post("/api/events/ingest")
async def ingest_events(raw_events: list[dict]):
    """Normalize raw events from GDELT, news, or X (Twitter) sources."""
    return ingest_unstructured_events(raw_events)


@app.post("/api/structured/prepare")
async def prepare_structured(raw_structured_data: dict):
    """Normalize structured data and build the D2STGNN-ready dataset."""
    return prepare_baseline_input(raw_structured_data)


@app.post("/api/structured/d2stgnn")
async def run_d2stgnn(payload: dict):
    """Run the full FUSE-Traffic D2STGNN pipeline with event fusion.

    Expected payload:
    {
        "structured_data": {
            "road_network": [...],   # OSMnx segments
            "traffic": [...],        # TomTom observations
            "weather": [...],        # OpenWeatherMap / WeatherStack
            "flood": [...]           # Project NOAH hazard levels
        },
        "events": {
            "count": N,
            "events": [...]          # From /api/events/ingest
        }
    }
    """
    # --- 1. Build structured dataset ---
    dataset = prepare_baseline_input(payload.get("structured_data", {}))
    history_np = dataset["history_tensor"]    # [T, N, 6]
    adjacency_np = dataset["adjacency_matrix"]  # [N, N]
    num_nodes = adjacency_np.shape[0]
    input_len = dataset["input_len"]
    output_len = dataset["output_len"]
    num_feat = dataset.get("num_feat", 4)

    # --- 2. Build adjacency list for D2STGNN (k_s adjacency matrices) ---
    adj_tensor = torch.tensor(adjacency_np, dtype=torch.float32)
    # D2STGNN expects k_s adjacency matrices; duplicate for bidirectional graph
    k_s = _D2STGNN_DEFAULTS["k_s"]
    adjs = [adj_tensor for _ in range(k_s)]

    # --- 3. Encode unstructured events into [1, E, C] embedding tensor ---
    events_payload = payload.get("events", {"count": 0, "events": []})
    event_list = events_payload.get("events", []) or []
    c_dim = 512  # Must match D2STGNN._c_dim = forecast_dim * 2 = 256 * 2
    event_emb_np = encode_events_to_embeddings(
        event_list, c_dim=c_dim, max_events=384)
    event_emb_tensor = torch.tensor(event_emb_np, dtype=torch.float32)
    # → [1, 384, 512]

    # --- 4. Prepare history tensor for D2STGNN ---
    # D2STGNN expects [B, T, N, num_feat+2]
    # history_np is [T, N, 6] → unsqueeze batch dim → [1, T, N, 6]
    history_tensor = torch.tensor(history_np, dtype=torch.float32).unsqueeze(0)
    # Future tensor: zeros placeholder (inference mode, no teacher forcing)
    future_tensor = torch.zeros(
        1, output_len, num_nodes, num_feat + 2, dtype=torch.float32)

    # --- 5. Instantiate and run D2STGNN ---
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
    # forecast_tensor shape: [1, gap*4, N, 1]
    forecast_np = forecast_tensor.cpu().numpy()

    # --- 6. Post-hoc reliability adjustment from unstructured pipeline ---
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
