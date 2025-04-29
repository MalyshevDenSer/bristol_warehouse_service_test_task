# app.config.py

import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")
TTL = int(os.getenv('TTL'))

DB_URL = os.getenv('DB_URL')

KAFKA_TOPIC = os.getenv('KAFKA_TOPIC')
KAFKA_HOST = os.getenv('KAFKA_HOST')
KAFKA_PORT = os.getenv('KAFKA_PORT')
KAFKA_URL = f'{KAFKA_HOST}:{KAFKA_PORT}'
