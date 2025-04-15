from app.models import MovementEvent
from app.schemas import KafkaEnvelope
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging


async def handle_event(envelope: KafkaEnvelope, db: AsyncSession, backend=None):
    data = envelope.data

    exists = await db.scalar(
        select(MovementEvent.id).where(MovementEvent.message_id == envelope.id)
    )
    if exists:
        raise ValueError(f"Message {envelope.id} already exists")

    event_exists = await db.scalar(
        select(MovementEvent.id).where(
            MovementEvent.movement_id == data.movement_id,
            MovementEvent.event == data.event
        )
    )
    if event_exists:
        raise ValueError(
            f"Event '{data.event}' with movement_id={data.movement_id} already exists"
        )

    event = MovementEvent(
        message_id=envelope.id,
        movement_id=data.movement_id,
        warehouse_id=data.warehouse_id,
        product_id=data.product_id,
        timestamp=data.timestamp,
        event=data.event,
        quantity=data.quantity,
    )
    db.add(event)
    await db.commit()

    if backend is not None:
        cache_key = f"warehouses:{data.warehouse_id}:products:{data.product_id}"
        try:
            await backend.clear(key=cache_key)
        except Exception as e:
            logging.warning(f"Error while clearing cache: {e}")

