from warehouse_service.models import MovementEvent
from warehouse_service.schemas import KafkaEnvelope
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from warehouse_service.db import create_engine_and_session
from warehouse_service.config import DB_URL
from warehouse_service.services.movements import get_movement_events
from sqlalchemy.exc import IntegrityError
from sqlalchemy import insert, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

engine, SessionLocal = create_engine_and_session(
    DB_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
)


async def handle_event(envelope: KafkaEnvelope, db: AsyncSession, backend):
    data = envelope.data

    event_row = MovementEvent(
        message_id=envelope.id,
        movement_id=data.movement_id,
        warehouse_id=data.warehouse_id,
        product_id=data.product_id,
        timestamp=data.timestamp,
        event=data.event,
        quantity=data.quantity,
    )
    db.add(event_row)

    try:
        await db.commit()  # ← ОДИН запрос: INSERT
    except IntegrityError as exc:
        await db.rollback()

        # Выясняем, какое именно ограничение сработало
        msg = str(exc.orig)
        if "movement_events_message_id_key" in msg:
            raise ValueError(f"Message {envelope.id} already exists") from exc
        elif "uix_movement_event_event_type" in msg:
            raise ValueError(
                f"Event '{data.event}' for movement_id={data.movement_id} "
                "already exists"
            ) from exc
        else:
            raise
    finally:
        if backend is not None:
            movement_cache_key = f":movements:{data.movement_id}"
            stock_cache_key = f":warehouses:{data.warehouse_id}:products:{data.product_id}"
            try:
                await backend.clear(key=movement_cache_key)
                await backend.clear(key=stock_cache_key)
            except Exception as e:
                logging.warning(f"Error while clearing cache: {e}")
