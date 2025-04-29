# tests/integration/test_cache_stock.py
import logging

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from warehouse_service.models import MovementEvent
from warehouse_service.config import KAFKA_TOPIC
import asyncio


@pytest.mark.asyncio(loop_scope="session")
async def test_cache_key_hit(async_client, db_session):
    warehouse_id = uuid4()
    product_id = uuid4()
    now = datetime.now(timezone.utc)

    db_session.add(
        MovementEvent(
            message_id=uuid4(),
            movement_id=uuid4(),
            warehouse_id=warehouse_id,
            product_id=product_id,
            timestamp=now,
            event="arrival",
            quantity=100,
        )
    )
    await db_session.commit()

    # мокаем функцию, чтобы считать, сколько раз она вызвалась
    with patch("warehouse_service.main.calculate_stock", new_callable=AsyncMock) as mocked_calc:
        mocked_calc.return_value = 100

        # обращаемся первый раз, ожидаем, что сделается кэш по этому запросу
        r1 = await async_client.get(f"/warehouses/{warehouse_id}/products/{product_id}")
        assert r1.status_code == 200
        assert r1.json()["quantity"] == 100
        assert mocked_calc.await_count == 1
        # обращаемся второй раз, ожидаем, что используется созданный кэщ
        r2 = await async_client.get(f"/warehouses/{warehouse_id}/products/{product_id}")
        assert r2.status_code == 200
        assert r2.json()["quantity"] == 100
        assert mocked_calc.await_count == 1  # если до сих пор 1 раз использовалась, значит кэш работает


@pytest.mark.asyncio(loop_scope="session")
async def test_cache_warehouses_products_stock_updated(async_client, db_session, kafka_producer):
    warehouse_id = uuid4()
    product_id = uuid4()

    first_arrival = {
        "id": uuid4(),
        "source": "string",
        "specversion": "string",
        "type": "string",
        "datacontenttype": "string",
        "dataschema": "string",
        "time": 0,
        "subject": "string",
        "destination": "string",
        "data": {
            "movement_id": uuid4(),
            "warehouse_id": warehouse_id,
            "timestamp": "2025-04-24T11:59:22.104Z",
            "event": "arrival",
            "product_id": product_id,
            "quantity": 50
        }
    }

    second_arrival = {
        "id": uuid4(),
        "source": "string",
        "specversion": "string",
        "type": "string",
        "datacontenttype": "string",
        "dataschema": "string",
        "time": 0,
        "subject": "string",
        "destination": "string",
        "data": {
            "movement_id": uuid4(),
            "warehouse_id": warehouse_id,
            "timestamp": "2025-04-24T11:59:22.104Z",
            "event": "arrival",
            "product_id": product_id,
            "quantity": 50
        }
    }

    r0 = await async_client.get(f"/warehouses/{warehouse_id}/products/{product_id}")
    assert r0.status_code == 200
    assert r0.json()["quantity"] == 0

    await kafka_producer.send(KAFKA_TOPIC, first_arrival)
    # Подождать, чтобы consumer обработал сообщения и записал в БД
    await asyncio.sleep(5)

    r1 = await async_client.get(f"/warehouses/{warehouse_id}/products/{product_id}")
    assert r1.status_code == 200
    assert r1.json()["quantity"] == 50

    await kafka_producer.send(KAFKA_TOPIC, second_arrival)
    # Подождать, чтобы consumer обработал сообщения и записал в БД
    await asyncio.sleep(5)

    r2 = await async_client.get(f"/warehouses/{warehouse_id}/products/{product_id}")
    assert r2.status_code == 200
    assert r2.json()["quantity"] == 100


@pytest.mark.asyncio(loop_scope="session")
async def test_cache_movement_updated(async_client, db_session, kafka_producer):
    product_id = uuid4()
    movement_id = uuid4()
    sender_warehouse = uuid4()
    reciever_warehouse = uuid4()

    departure = {
        "id": uuid4(),
        "source": "string",
        "specversion": "string",
        "type": "string",
        "datacontenttype": "string",
        "dataschema": "string",
        "time": 0,
        "subject": "string",
        "destination": "string",
        "data": {
            "movement_id": movement_id,
            "warehouse_id": sender_warehouse,
            "timestamp": "2025-04-24T11:59:22.104Z",
            "event": "departure",
            "product_id": product_id,
            "quantity": 50
        }
    }

    arrival = {
        "id": uuid4(),
        "source": "string",
        "specversion": "string",
        "type": "string",
        "datacontenttype": "string",
        "dataschema": "string",
        "time": 0,
        "subject": "string",
        "destination": "string",
        "data": {
            "movement_id": movement_id,
            "warehouse_id": reciever_warehouse,
            "timestamp": "2025-04-24T11:59:22.104Z",
            "event": "arrival",
            "product_id": product_id,
            "quantity": 50
        }
    }

    r0 = await async_client.get(f"/movements/{movement_id}")
    assert r0.status_code == 404

    await kafka_producer.send(KAFKA_TOPIC, arrival)
    await kafka_producer.send(KAFKA_TOPIC, departure)
    # Подождать, чтобы consumer обработал сообщения и записал в БД
    await asyncio.sleep(5)

    r1 = await async_client.get(f"/movements/{movement_id}")
    assert r1.status_code == 200
    assert r1.json()['movement_id'] == str(movement_id)
    assert r1.json()['quantity_departed'] == 50
    assert r1.json()['quantity_arrived'] == 50
    assert r1.json()['quantity_difference'] == 0
    assert r1.headers['x-fastapi-cache'] == 'MISS'

    r2 = await async_client.get(f"/movements/{movement_id}")
    assert r2.status_code == 200
    assert r2.json()['movement_id'] == str(movement_id)
    assert r2.json()['quantity_departed'] == 50
    assert r2.json()['quantity_arrived'] == 50
    assert r2.json()['quantity_difference'] == 0
    assert r2.headers['x-fastapi-cache'] == 'HIT'


