from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager
import pytest
from warehouse_service.schemas import KafkaEnvelope
from kafka_utils import consumer  # 👈 импортируем модуль целиком


def _raw_msg():
    """Сообщение такого же формата, какой кладёт Producer."""
    body = {
        "movement_id": uuid4(),
        "warehouse_id": uuid4(),
        "product_id": uuid4(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "arrival",
        "quantity": 1,
    }
    envelope = {
        "id": str(uuid4()),
        "source": "WH‑1",
        "specversion": "1.0",
        "type": "ru.retail.w",
        "datacontenttype": "application/json",
        "dataschema": "ru.retail.w.v1",
        "time": 123,
        "subject": "WH‑1:ARRIVAL",
        "destination": "ru.retail.w",
        "data": body,
    }
    return SimpleNamespace(value=envelope)  # value уже dict – именно это ждёт consumer


@pytest.mark.asyncio(loop_scope="session")
async def test_process_message_calls_handle_event(monkeypatch):
    msg = _raw_msg()

    fake_session = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield fake_session

    monkeypatch.setattr(consumer, "SessionLocal", _ctx)

    with patch.object(consumer, "handle_event", new=AsyncMock()) as he:
        await consumer.process_message(msg)
        he.assert_awaited_once()

        env = he.await_args.args[0]
        assert isinstance(env, KafkaEnvelope)
        assert env.data.event == "arrival"
