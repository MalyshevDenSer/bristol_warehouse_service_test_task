from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.db import init_db


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logging.info("Initializing database...")
    await init_db()
    logging.info("Database initialized.")

    yield
    logging.info("Shutting down...")

app = FastAPI(title="Warehouse Monitoring Service", lifespan=lifespan)
