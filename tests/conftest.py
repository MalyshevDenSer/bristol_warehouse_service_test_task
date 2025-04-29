import logging

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from kafka_utils.producer import KafkaProducerWrapper
from warehouse_service.config import KAFKA_HOST, KAFKA_PORT
from warehouse_service.db import AsyncSessionLocal
from warehouse_service.logger import setup_logger
from warehouse_service.main import app as fastapi_app

logger = setup_logger(name='tests')


@pytest_asyncio.fixture(scope="session")
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
    await session.close()


@pytest_asyncio.fixture(scope="session")
async def async_client():
    logging.debug('LifespanManager is going to start now!')
    async with LifespanManager(fastapi_app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://test",
        ) as client:
            yield client


@pytest_asyncio.fixture(scope="session")
async def kafka_producer():
    wrapper = KafkaProducerWrapper(f"{KAFKA_HOST}:{KAFKA_PORT}")
    await wrapper.connect()
    yield wrapper
    await wrapper.disconnect()
