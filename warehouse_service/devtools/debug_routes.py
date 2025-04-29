from fastapi import APIRouter, Depends, HTTPException
from warehouse_service.schemas import KafkaEnvelope
from kafka_utils.producer import KafkaProducerWrapper
from kafka_utils.db import handle_event
from warehouse_service.db import get_db
from warehouse_service.config import KAFKA_TOPIC
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache import FastAPICache
import logging
from fastapi import Request
logger = logging.getLogger("warehouse_service.api.debug")

router = APIRouter(prefix="/debug", tags=["debug"])


def get_kafka_producer_from_state(request: Request) -> KafkaProducerWrapper:
    return request.app.state.kafka_producer


@router.post("/publish_kafka")
async def publish_to_kafka(
    envelope: KafkaEnvelope,
    producer: KafkaProducerWrapper = Depends(get_kafka_producer_from_state)
):
    try:
        await producer.send(KAFKA_TOPIC, envelope.model_dump())
        return {"status": "sent to Kafka"}
    except Exception as e:
        logger.error(f"Failed to send message to Kafka: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kafka send failed")


@router.post("/simulate_kafka")
async def simulate_kafka_event(
    envelope: KafkaEnvelope,
    db: AsyncSession = Depends(get_db)
):
    backend = FastAPICache.get_backend()
    try:
        await handle_event(envelope, db, backend=backend)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ok"}
