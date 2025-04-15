from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db import init_db, get_db
from app.models import MovementEvent
from app.schemas import KafkaEnvelope, MovementResponse, StockResponse
from sqlalchemy import select, func, case
from uuid import UUID
from app.handler import handle_event
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from fastapi_cache.decorator import cache
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
import time

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

instrumentator = Instrumentator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing database...")
    await init_db()
    logging.info("Database initialized.")

    logging.info("Initializing Redis cache...")
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    logging.info("Redis cache initialized.")

    yield
    logging.info("Shutting down...")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logging.info(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - {process_time:.2f}ms - "
            f"IP: {request.client.host}"
        )
        return response


app = FastAPI(title="Warehouse Monitoring Service", lifespan=lifespan)
instrumentator.instrument(app).expose(app)
app.add_middleware(LoggingMiddleware)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/simulate_kafka")
async def simulate_kafka_event(
    envelope: KafkaEnvelope,
    db: AsyncSession = Depends(get_db)
):
    backend = FastAPICache.get_backend()
    try:
        await handle_event(envelope, db, backend=backend)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ok"}


@app.get(
    "/warehouses/{warehouse_id}/products/{product_id}",
    response_model=StockResponse
)
@cache(expire=60)
async def get_stock(
    warehouse_id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (MovementEvent.event == "arrival", MovementEvent.quantity),
                    (MovementEvent.event == "departure", -MovementEvent.quantity),
                    else_=0
                )
            ),
            0
        )
    ).where(
        MovementEvent.warehouse_id == warehouse_id,
        MovementEvent.product_id == product_id
    )

    result = await db.scalar(stmt)
    raw_quantity = result or 0
    quantity = max(raw_quantity, 0)

    if raw_quantity < 0:
        logging.warning(
            f"Отрицательное значение остатков: склад {warehouse_id}, товар {product_id}, "
            f"рассчитано {raw_quantity}, возвращаю 0"
        )

    return StockResponse(
        warehouse_id=warehouse_id,
        product_id=product_id,
        quantity=quantity
    )


@app.get("/movements/{movement_id}", response_model=MovementResponse)
@cache(expire=60)
async def get_movement(
    movement_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(MovementEvent).where(MovementEvent.movement_id == movement_id)
    result = await db.scalars(stmt)
    events = list(result)

    departure = next((e for e in events if e.event == "departure"), None)
    arrival = next((e for e in events if e.event == "arrival"), None)

    if not departure or not arrival:
        raise HTTPException(status_code=404, detail="Movement incomplete or not found")

    quantity_diff = arrival.quantity - departure.quantity
    transit = int((arrival.timestamp - departure.timestamp).total_seconds())

    return MovementResponse(
        movement_id=movement_id,
        sender_warehouse=departure.warehouse_id,
        receiver_warehouse=arrival.warehouse_id,
        departure_time=departure.timestamp,
        arrival_time=arrival.timestamp,
        quantity_departed=departure.quantity,
        quantity_arrived=arrival.quantity,
        quantity_difference=quantity_diff,
        transit_seconds=transit
    )
