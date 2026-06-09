import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_redis_connection():
    return await redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
