import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from app.schemas import KafkaEnvelope
from app.handler import handle_event
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_TOPIC = "warehouse-events"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9093"


async def consume():
    await asyncio.sleep(10)
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="warehouse-service",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest"
    )

    await consumer.start()
    logger.info("Kafka consumer started and listening...")
    try:
        async for msg in consumer:
            logger.info(f"Got message from Kafka: {msg.value}")
            try:
                envelope = KafkaEnvelope(**msg.value)
                async with SessionLocal() as session:
                    await handle_event(envelope, session)
            except Exception as e:
                logger.error(f"Error during proccessing event: {e}", exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")
