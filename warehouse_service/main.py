from contextlib import asynccontextmanager
from typing import Union
from uuid import UUID

import redis.asyncio as redis
from fastapi import FastAPI, Depends, Request
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession

from kafka_utils.producer import KafkaProducerWrapper
from warehouse_service.config import KAFKA_URL
from warehouse_service.config import REDIS_HOST, REDIS_PORT, REDIS_DB, TTL
from warehouse_service.db import prepare_database, get_db
from warehouse_service.devtools.debug_routes import router as debug_router
from warehouse_service.logger import setup_logger
from warehouse_service.schemas import MovementResponse, StockResponse, ErrorResponse
from warehouse_service.services.movements import get_movement_info
from warehouse_service.services.stock import calculate_stock

logger = setup_logger("warehouse_service.api")
instrumentator = Instrumentator()


def request_key_builder(
    *_, request: Request = None, **__
) -> str:
    # например :warehouses:3fa85f64-5717-4562-b3fc-2c963f66afa1:products:3fa85f64-5717-4562-b3fc-2c963f66afa2
    cache_key = request.url.path.replace('/', ':')
    return cache_key


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info('Starting db...')
    await prepare_database()
    logger.info('DB was started!')
    redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
        decode_responses=False
    )
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix="fastapi-cache",
        key_builder=request_key_builder
        )
    producer = KafkaProducerWrapper(KAFKA_URL)
    await producer.connect()
    app_instance.state.kafka_producer = producer

    yield
    await FastAPICache.clear()
    await redis_client.connection_pool.disconnect()
    await producer.disconnect()


app = FastAPI(title="Warehouse Monitoring Service", lifespan=lifespan)
instrumentator.instrument(app).expose(app)

app.include_router(debug_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/warehouses/{warehouse_id}/products/{product_id}", response_model=StockResponse)
@cache(expire=TTL)
async def get_stock(warehouse_id: UUID, product_id: UUID, db: AsyncSession = Depends(get_db)):
    quantity = await calculate_stock(db, warehouse_id, product_id)

    return StockResponse(
        warehouse_id=warehouse_id,
        product_id=product_id,
        quantity=quantity
    )


@app.get(
    "/movements/{movement_id}",
    response_model=Union[MovementResponse, ErrorResponse],
)
@cache(expire=TTL)
async def get_movement(movement_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_movement_info(db, movement_id)
