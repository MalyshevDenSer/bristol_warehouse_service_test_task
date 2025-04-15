import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from app.handler import handle_event
from app.schemas import KafkaEnvelope, KafkaEventData
from app.models import MovementEvent
from tests.utils import make_envelope

from unittest.mock import AsyncMock
import logging


@pytest.mark.asyncio
async def test_handle_event_adds_to_db(db):
    movement_id = uuid.uuid4()
    event_id = uuid.uuid4()
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()
    timestamp = datetime.now(tz=timezone.utc)

    envelope = KafkaEnvelope(
        id=event_id,
        source="test",
        specversion="1.0",
        type="warehouse.event",
        datacontenttype="application/json",
        dataschema="warehouse-event-schema",
        time=int(timestamp.timestamp()),
        subject="test-event",
        destination="warehouse-service",
        data=KafkaEventData(
            movement_id=movement_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            timestamp=timestamp,
            event="arrival",
            quantity=10,
        ),
    )

    await handle_event(envelope, db)

    result = await db.execute(
        select(MovementEvent).where(MovementEvent.movement_id == movement_id)
    )
    event = result.scalars().first()

    assert event is not None
    assert event.message_id == event_id
    assert event.movement_id == movement_id
    assert event.warehouse_id == warehouse_id
    assert event.product_id == product_id
    assert event.timestamp == timestamp
    assert event.event == "arrival"
    assert event.quantity == 10


@pytest.mark.asyncio
async def test_handle_event_duplicate_message(db):
    envelope = make_envelope()
    await handle_event(envelope, db)
    with pytest.raises(ValueError) as excinfo:
        await handle_event(envelope, db)

    assert "already exists" in str(excinfo.value)


@pytest.mark.asyncio
async def test_handle_event_duplicate_event_type(db):
    """
    Проверяет, что нельзя дважды записать одно и то же событие (arrival/departure) для одного movement_id.
    Это защита от дублирующей информации от склада.
    """
    movement_id = uuid.uuid4()

    e1 = make_envelope(event="arrival", movement_id=movement_id)
    e2 = make_envelope(event="arrival", movement_id=movement_id)

    e2.data.product_id = e1.data.product_id
    e2.data.warehouse_id = e1.data.warehouse_id

    await handle_event(e1, db)

    with pytest.raises(ValueError) as excinfo:
        await handle_event(e2, db)

    assert "already exists" in str(excinfo.value)


@pytest.mark.asyncio
async def test_handle_event_cache_clear_called(db):
    """
    Проверяет, что после обработки события вызывается очистка кеша по ключу warehouse+product.
    """
    envelope = make_envelope()
    backend = AsyncMock()

    await handle_event(envelope, db, backend=backend)

    key = f"warehouses:{envelope.data.warehouse_id}:products:{envelope.data.product_id}"
    backend.clear.assert_awaited_once_with(key=key)


@pytest.mark.asyncio
async def test_handle_event_cache_clear_logs_on_failure(db, caplog):
    """
    Проверяет, что при ошибке очистки кеша логгируется warning-сообщение.
    Не должен падать, просто логировать.
    """
    envelope = make_envelope()
    backend = AsyncMock()
    backend.clear.side_effect = Exception("redis fail")

    caplog.set_level(logging.WARNING)

    await handle_event(envelope, db, backend=backend)

    assert "Error while clearing cache" in caplog.text
    assert "redis fail" in caplog.text

