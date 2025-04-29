import pytest
from unittest.mock import AsyncMock, MagicMock
from kafka_utils.db import handle_event

from datetime import datetime, timezone
from warehouse_service.schemas import KafkaEnvelope, KafkaEventData
from uuid import uuid4
from sqlalchemy.exc import IntegrityError


def _fake_envelope(event: str = "arrival", duplicate=False):
    data = KafkaEventData(
        movement_id=uuid4(),
        warehouse_id=uuid4(),
        product_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        event=event,
        quantity=1
    )

    return KafkaEnvelope(
        id=uuid4() if not duplicate else "dup",
        source="test-source",
        specversion="1.0",
        type="test.event",
        datacontenttype="application/json",
        dataschema="test-schema",
        time=int(datetime.now(timezone.utc).timestamp() * 1000),
        subject="test-subject",
        destination="test-destination",
        data=data
    )


def _integrity_error(pg_msg: str) -> IntegrityError:
    """Генерируем IntegrityError с нужным текстом postgres-ошибки."""
    class _OrigExc(Exception):
        def __str__(self):
            return pg_msg
    return IntegrityError("stmt", "params", _OrigExc())  # type: ignore


@pytest.mark.asyncio
async def test_duplicate_message_id():
    """Дубликат message_id → ValueError."""
    db = AsyncMock()
    db.add = MagicMock()
    # commit бросает PG-ошибку по уникальному индексу message_id
    db.commit.side_effect = _integrity_error("movement_events_message_id_key")

    with pytest.raises(ValueError, match="already exists"):
        await handle_event(_fake_envelope(), db, backend=None)

    db.add.assert_called_once()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_event():
    """Повторное arrival/departure для того же movement_id."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = _integrity_error("uix_movement_event_event_type")

    with pytest.raises(ValueError, match="already exists"):
        await handle_event(_fake_envelope(), db, backend=None)

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_success_adds_and_commits():
    """Нормальный happy-path: insert + 2 cache clear."""
    db = AsyncMock()
    db.add = MagicMock()           # add — синхронный
    backend = AsyncMock()

    await handle_event(_fake_envelope(), db, backend=backend)

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    # два ключа: :movements:* и :warehouses:*:products:*
    assert backend.clear.await_count == 2


@pytest.mark.asyncio
async def test_handle_event_no_backend():
    """backend=None не должен ломать вызов."""
    db = AsyncMock()
    db.add = MagicMock()

    await handle_event(_fake_envelope(), db, backend=None)

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_event_raises_text():
    """Проверяем текст исключения для дубликата event."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = _integrity_error("uix_movement_event_event_type")

    env = _fake_envelope()

    with pytest.raises(ValueError) as exc:
        await handle_event(env, db, backend=None)

    expected = (
        f"Event '{env.data.event}' "
        f"for movement_id={env.data.movement_id} already exists"
    )
    assert str(exc.value) == expected