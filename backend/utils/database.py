from __future__ import annotations
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from models.road_graph import Base as GraphBase
from models.traffic import Base

# Settings
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/spatial_mapping"
)

# Engine
def build_engine(url: str = DATABASE_URL, *, testing: bool = False) -> AsyncEngine:
    kwargs: dict = {
        "echo": os.getenv("DB_ECHO", "false").lower() == "true",
        "pool_pre_ping": True,
    }
    if testing:
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
        kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        kwargs["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    return create_async_engine(url, **kwargs)

engine: AsyncEngine = build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Schema Init
async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS postgis")
        )
        await conn.run_sync(Base.metadata.create_all)

async def drop_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)