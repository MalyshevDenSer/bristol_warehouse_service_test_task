import logging

import pytest
from uuid import uuid4


@pytest.mark.asyncio(loop_scope="session")
async def test_full_flow(db_session, async_client, kafka_producer):
    payload = {
        "id": str(uuid4()),
        "source": "string",
        "specversion": "string",
        "type": "string",
        "datacontenttype": "string",
        "dataschema": "string",
        "time": 0,
        "subject": "string",
        "destination": "string",
        "data": {
            "movement_id": str(uuid4()),
            "warehouse_id": str(uuid4()),
            "timestamp": "2025-04-23T10:22:45.621Z",
            "event": "arrival",
            "product_id": str(uuid4()),
            "quantity": 0
        }
    }
    r_stock_to = await async_client.post(f"/debug/publish_kafka", json=payload)

