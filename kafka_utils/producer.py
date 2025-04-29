import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError


class KafkaProducerWrapper:
    def __init__(
        self,
        bootstrap_servers: str,
        max_retries: int = 10,
        delay: float = 3.0,
        send_timeout: float = 10.0,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.max_retries       = max_retries
        self.retry_delay       = delay
        self.send_timeout      = send_timeout
        self.producer: AIOKafkaProducer | None = None

    async def connect(self):
        attempt = 1
        while attempt <= self.max_retries:
            try:
                logging.debug(f"Attempting to connect to Kafka ({self.bootstrap_servers}), try {attempt}")
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
                )
                await self.producer.start()
                logging.info("Kafka producer connected successfully.")
                return
            except KafkaConnectionError as e:
                logging.warning(f"Kafka not ready (attempt {attempt}/{self.max_retries}): {e}")
                attempt += 1
                await self.producer.stop()
                await asyncio.sleep(self.retry_delay)
        self.producer = None
        raise RuntimeError("Failed to connect to Kafka after multiple attempts.")

    async def disconnect(self):
        if self.producer:
            try:
                await self.producer.stop()
                logging.info("Kafka producer stopped.")
            except KafkaError as stop_err:
                logging.warning(f"Error while stopping Kafka producer: {stop_err}")
            finally:
                # переводим обёртку в состояние 'не подключен'
                self.producer = None

    async def send(self, topic: str, message: dict):
        if not self.producer:
            raise RuntimeError("Kafka producer is not started")

        logging.debug(f"Sending message to {topic}, waiting up to {self.send_timeout}s for an ack…")
        try:
            await self.producer.send(topic, message)
            logging.debug("Message acknowledged by broker.")
        except asyncio.TimeoutError:
            logging.error(f"Timeout after {self.send_timeout}s sending to {topic}")
            raise RuntimeError(f"Kafka send timed out after {self.send_timeout}s")
