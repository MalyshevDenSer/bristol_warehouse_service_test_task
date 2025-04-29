import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from tests.conftest import logger
from warehouse_service.config import KAFKA_TOPIC


@pytest.mark.asyncio(loop_scope="session")
async def test_full_flow(db_session, async_client, kafka_producer):
    movement_id = uuid4()
    wh_from = uuid4()
    wh_to = uuid4()
    prod = uuid4()
    t_dep = datetime.now(timezone.utc)
    t_arr = t_dep + timedelta(minutes=1)

    envelope_common = {
        "source": "WH-test",
        "specversion": "1.0",
        "type": "ru.retail.warehouses.movement",
        "datacontenttype": "application/json",
        "dataschema": "ru.retail.warehouses.movement.v1.0",
        "time": int(datetime.now(timezone.utc).timestamp() * 1000),
        "subject": "WH-test:EVENT",
        "destination": "ru.retail.warehouses",
    }

    # departure
    msg_dep = {
        **envelope_common,
        "id": str(uuid4()),
        "subject": f"WH-test:DEPARTURE",
        "data": {
            "movement_id": str(movement_id),
            "warehouse_id": str(wh_from),
            "timestamp": t_dep.isoformat(),
            "event": "departure",
            "product_id": str(prod),
            "quantity": 5
        }
    }
    # arrival
    msg_arr = {
        **envelope_common,
        "id": str(uuid4()),
        "subject": f"WH-test:ARRIVAL",
        "data": {
            "movement_id": str(movement_id),
            "warehouse_id": str(wh_to),
            "timestamp": t_arr.isoformat(),
            "event": "arrival",
            "product_id": str(prod),
            "quantity": 5
        }
    }

    await kafka_producer.send(KAFKA_TOPIC, msg_dep)
    await kafka_producer.send(KAFKA_TOPIC, msg_arr)

    # Подождать, чтобы consumer обработал сообщения и записал в БД
    logger.debug('Sleeping for 3 seconds to consume messsages')
    await asyncio.sleep(3)

    r_stock_from = await async_client.get(f"/warehouses/{wh_from}/products/{prod}")
    assert r_stock_from.status_code == 200
    assert r_stock_from.json()["quantity"] == 0

    r_stock_to = await async_client.get(f"/warehouses/{wh_to}/products/{prod}")
    assert r_stock_to.status_code == 200
    assert r_stock_to.json()["quantity"] == 5

    r_mov = await async_client.get(f"/movements/{movement_id}")
    assert r_mov.status_code == 200
    body = r_mov.json()

    assert body["sender_warehouse"] == str(wh_from)
    assert body["receiver_warehouse"] == str(wh_to)

    assert body["departure_time"].startswith(t_dep.isoformat()[:19])
    assert body["arrival_time"].startswith(t_arr.isoformat()[:19])

    assert body["quantity_difference"] == 0
    assert body["transit_seconds"] == int((t_arr - t_dep).total_seconds())
