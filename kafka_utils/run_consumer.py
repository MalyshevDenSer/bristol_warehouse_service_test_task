import asyncio

from kafka_utils.consumer import consume

if __name__ == "__main__":
    asyncio.run(consume())
