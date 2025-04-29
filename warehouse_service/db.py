from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from warehouse_service import models
from warehouse_service.config import DB_URL
from warehouse_service.logger import setup_logger

logger = setup_logger(__name__)


def create_engine_and_session(
    db_url,
    **engine_kwargs,
):
    engine = create_async_engine(db_url, future=True, **engine_kwargs)
    session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_local


_engine, AsyncSessionLocal = create_engine_and_session(DB_URL)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# ---------- Утилиты (нужны только в dev / тестах) ----------


async def init_models(engine=_engine, *, drop: bool = False) -> None:

    from sqlalchemy.ext.asyncio import AsyncEngine

    if not isinstance(engine, AsyncEngine):
        raise TypeError("init_models() ожидает AsyncEngine")

    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)
        logger.warning("Schema synced via create_all(); Alembic is bypassed")

metadata = models.Base.metadata


async def _sync_schema_if_needed(engine: AsyncEngine) -> None:
    if os.getenv("CREATE_SCHEMA_FROM_MODELS") == "1":
        await init_models(engine)
    else:
        logger.info("CREATE_SCHEMA_FROM_MODELS != 1 → пропускаем create_all()")


async def prepare_database() -> None:
    await _sync_schema_if_needed(_engine)
