import redis.asyncio as redis
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.core.config import get_settings
from app.database import get_db_session, get_redis_connection
from app.ingestion.router import router as ingestion_router
from app.nlp.router import router as nlp_router

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(ingestion_router, prefix=settings.api_prefix)
app.include_router(nlp_router, prefix=settings.api_prefix)

@app.get("/api/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> dict[str, str]:
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
