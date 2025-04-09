from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db import init_db, get_db
from app.models import MovementEvent
from app.schemas import KafkaEnvelope, MovementResponse, StockResponse
from sqlalchemy import select, func, case
from uuid import UUID

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing database...")
    await init_db()
    logging.info("Database initialized.")
    yield
    logging.info("Shutting down...")


app = FastAPI(title="Warehouse Monitoring Service", lifespan=lifespan)


@app.post("/simulate_kafka")
async def simulate_kafka_event(
    envelope: KafkaEnvelope,
    db: AsyncSession = Depends(get_db)
):
    exists = await db.scalar(
        select(MovementEvent.id).where(MovementEvent.message_id == envelope.id)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Duplicate message_id")

    event = MovementEvent(
        message_id=envelope.id,
        movement_id=envelope.data.movement_id,
        warehouse_id=envelope.data.warehouse_id,
        product_id=envelope.data.product_id,
        timestamp=envelope.data.timestamp,
        event=envelope.data.event,
        quantity=envelope.data.quantity,
    )

    db.add(event)
    await db.commit()
    return {"status": "ok"}


@app.get(
    "/warehouses/{warehouse_id}/products/{product_id}",
    response_model=StockResponse
)
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
            f"Отрицательное значение остатков: склад {warehouse_id}, товар {product_id}, рассчитано {raw_quantity}, возвращаю 0"
        )

    return StockResponse(
        warehouse_id=warehouse_id,
        product_id=product_id,
        quantity=quantity
    )


@app.get("/movements/{movement_id}", response_model=MovementResponse)
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
