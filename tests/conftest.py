import pytest_asyncio
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base
from app.config import DB_URL


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(DB_URL, echo=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()
