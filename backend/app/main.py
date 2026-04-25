from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import redis.asyncio as redis

from .database import get_db_session, get_redis_connection

app = FastAPI()

@app.get("/api/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_conn: redis.Redis = Depends(get_redis_connection)
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
