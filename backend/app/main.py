import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import numpy as np
import redis.asyncio as redis
import torch
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import get_db_session, get_redis_connection
from app.ingestion.router import router as ingestion_router
from app.nlp.router import router as nlp_router
from app.spatial.router import router as spatial_router
from app.d2stgnn_external import D2STGNN
from app.fusion import encode_events_to_embeddings, fuse_forecast_with_events
from app.structured_model_adapter import prepare_baseline_input

from ml.graph_wavenet import build_gwn_model
from ml.temporal_models import LSTMTrafficPredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# D2STGNN configuration matching paper defaults
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
    return D2STGNN(num_nodes=num_nodes, adjs=adjs, **_D2STGNN_DEFAULTS)


# Application State
class AppState:
    gwn_model = None
    lstm_model = None
    xgb_models = {}
    num_nodes: int = 0
    device: str = "cpu"

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("▶ Event-Aware Traffic Forecasting API starting up...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    app_state.device = device
    logger.info(f"✓ Torch device: {device}")

    num_nodes = int(os.getenv("GWN_NUM_NODES", "5000"))
    app_state.num_nodes = num_nodes

    gwn_ckpt = os.getenv("GWN_CHECKPOINT_PATH", "")
    if gwn_ckpt and os.path.exists(gwn_ckpt):
        try:
            app_state.gwn_model = build_gwn_model(
                num_nodes=num_nodes, device=device, checkpoint_path=gwn_ckpt)
            logger.info(f"✓ Graph WaveNet loaded from {gwn_ckpt}")
        except Exception as e:
            logger.warning(f"⚠ Failed to load GWN model: {e}")
    else:
        logger.warning("⚠ GWN checkpoint not found — running without spatial model.")

    lstm_ckpt = os.getenv("LSTM_CHECKPOINT_PATH", "")
    if lstm_ckpt and os.path.exists(lstm_ckpt):
        try:
            lstm = LSTMTrafficPredictor()
            state = torch.load(lstm_ckpt, map_location=device)
            lstm.load_state_dict(state["model_state_dict"])
            lstm.eval()
            app_state.lstm_model = lstm
            logger.info(f"✓ LSTM model loaded from {lstm_ckpt}")
        except Exception as e:
            logger.warning(f"⚠ Failed to load LSTM model: {e}")
    else:
        logger.warning("⚠ LSTM checkpoint not found — running without temporal model.")

    try:
        from ml.temporal_models import XGBTrafficPredictor
        xgb_models = {}
        for horizon in [15, 30, 60]:
            path = os.getenv(f"XGB_CHECKPOINT_{horizon}", f"checkpoints/xgb_{horizon}.json")
            if os.path.exists(path):
                xgb_models[horizon] = XGBTrafficPredictor(horizon).load(path)
                logger.info(f"✓ XGBoost {horizon}min model loaded.")
        app_state.xgb_models = xgb_models
    except Exception as exc:
        logger.warning(f"⚠ XGBoost models not loaded: {exc}")

    logger.info("✅ API ready.")
    yield
    logger.info("■ API shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Metro Manila Road Graph API with Event-Aware Traffic Forecasting",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(ingestion_router, prefix=settings.api_prefix)
    app.include_router(nlp_router, prefix=settings.api_prefix)
    app.include_router(spatial_router, prefix=settings.api_prefix)

    @app.post("/api/events/ingest")
    async def ingest_events(raw_events: list[dict]):
        """Normalize raw events from GDELT, news, or X (Twitter) sources."""
        from app.event_pipeline import ingest_unstructured_events
        return ingest_unstructured_events(raw_events)

    @app.post("/api/structured/prepare")
    async def prepare_structured(raw_structured_data: dict):
        """Normalize structured data and build the D2STGNN-ready dataset."""
        return prepare_baseline_input(raw_structured_data)

    @app.post("/api/structured/d2stgnn")
    async def run_d2stgnn(payload: dict):
        """Run the full FUSE-Traffic D2STGNN pipeline with event fusion."""
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
        c_dim = 512
        event_emb_np = encode_events_to_embeddings(event_list, c_dim=c_dim, max_events=384)
        event_emb_tensor = torch.tensor(event_emb_np, dtype=torch.float32)

        history_tensor = torch.tensor(history_np, dtype=torch.float32).unsqueeze(0)
        future_tensor = torch.zeros(1, output_len, num_nodes, num_feat + 2, dtype=torch.float32)

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
    ) -> dict:
        db_status = "error"
        redis_status = "error"

        try:
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_status = "ok"
        except Exception as e:
            logger.error(f"DB connection failed: {e}")

        try:
            await redis_conn.ping()
            redis_status = "ok"
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

        return {
            "status": "ok",
            "module": "api_gateway",
            "db_status": db_status,
            "redis_status": redis_status,
            "gwn_loaded": app_state.gwn_model is not None,
            "lstm_loaded": app_state.lstm_model is not None,
            "xgb_horizons": list(app_state.xgb_models.keys()),
            "num_nodes": app_state.num_nodes,
            "device": app_state.device,
        }

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8003")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        workers=int(os.getenv("WORKERS", "1")),
    )
