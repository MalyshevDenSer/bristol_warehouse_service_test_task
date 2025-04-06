from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import DB_URL
from app.models import Base

engine = create_async_engine(DB_URL, echo=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with SessionLocal() as session:
        yield session
