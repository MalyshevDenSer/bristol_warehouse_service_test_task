import asyncio
import json

import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from fastapi_cache.backends.redis import RedisBackend

from kafka_utils.db import handle_event, engine, SessionLocal
from warehouse_service.config import KAFKA_URL, KAFKA_TOPIC
from warehouse_service.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from warehouse_service.logger import setup_logger
from warehouse_service.schemas import KafkaEnvelope

logger = setup_logger(__name__)
logger.debug("Kafka consumer initialized")

_redis_client = redis.Redis(
    host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB),
    decode_responses=False,
)
backend = RedisBackend(_redis_client)


async def process_message(msg):
    """Обработка одного Kafka-сообщения."""
    logger.debug("Kafka message: %s", msg.value)
    # start_time = time.perf_counter()

    try:
        envelope = KafkaEnvelope(**msg.value)
    except Exception as e:
        logger.error("Invalid envelope: %s", e, exc_info=True)
        return

    async with SessionLocal() as session:
        try:
            await handle_event(envelope, session, backend)
            await session.commit()
            # elapsed = time.perf_counter() - start_time
            # logger.info("Processed Kafka event in %.3f seconds", elapsed)
        except Exception as e:
            await session.rollback()
            logger.error("handle_event failed: %s", e, exc_info=True)


async def consume(max_retries: int = 10, retry_delay: float = 3.0) -> None:
    consumer = None
    attempt = 1

    while attempt <= max_retries:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_URL,
                group_id=KAFKA_TOPIC,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await consumer.start()
            logger.info("Kafka consumer started (topic=%s)", KAFKA_TOPIC)
            break
        except KafkaConnectionError as e:
            logger.warning("Kafka not ready (attempt %s/%s): %s", attempt, max_retries, e)
            attempt += 1
            await asyncio.sleep(retry_delay)

    if consumer is None:
        raise RuntimeError("Could not connect to Kafka")

    tasks = set()

    try:
        async for msg in consumer:
            task = asyncio.create_task(process_message(msg))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
    except Exception as e:
        logger.error("Consumer error: %s", e, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()
