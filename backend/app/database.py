import os
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5433/traffic_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_redis_connection():
    return await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
