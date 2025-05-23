import json
from aiokafka import AIOKafkaConsumer
from warehouse_service.models import Movement
from warehouse_service.db import SessionLocal
from warehouse_service.schemas import KafkaMovementEvent
from warehouse_service.config import settings

async def consume():
    consumer = AIOKafkaConsumer(
        "warehouse_movements",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="warehouse-group",
        enable_auto_commit=True
    )
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value)
            event = KafkaMovementEvent(**data["data"])
            db = SessionLocal()
            try:
                movement = Movement(**event.dict())
                db.add(movement)
                db.commit()
            finally:
                db.close()
    finally:
        await consumer.stop()
