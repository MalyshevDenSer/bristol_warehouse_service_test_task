from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost/warehouse"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

settings = Settings()


