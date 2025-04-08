from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import init_db, get_db
from app.models import MovementEvent
from app.schemas import KafkaEnvelope


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
