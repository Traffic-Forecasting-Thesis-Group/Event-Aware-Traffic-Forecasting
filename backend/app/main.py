import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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

from ml.graph_wavenet import build_gwn_model
from ml.temporal_models import LSTMTrafficPredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

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

    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    app_state.device = device
    logger.info(f"✓ Torch device: {device}")

    # Load models
    num_nodes = int(os.getenv("GWN_NUM_NODES", "5000"))
    app_state.num_nodes = num_nodes

    gwn_ckpt = os.getenv("GWN_CHECKPOINT_PATH", "")
    if gwn_ckpt and os.path.exists(gwn_ckpt):
        try:
            app_state.gwn_model = build_gwn_model(
                num_nodes=num_nodes,
                device=device,
                checkpoint_path=gwn_ckpt,
            )
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

    @app.get("/api/health")
    async def health_check(
        db: AsyncSession = Depends(get_db_session),
        redis_conn: redis.Redis = Depends(get_redis_connection)
    ) -> dict:
        db_status = "error"
        redis_status = "error"

        try:
            await redis_conn.ping()
            redis_status = "ok"
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

        # Basic DB check could go here, but omitted for brevity if missing in original
        
        return {
            "status": "ok",
            "module": "api_gateway",
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
