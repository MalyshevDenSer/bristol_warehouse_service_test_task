import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from warehouse_service.db import Base, get_db
from main import app

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.dependency_overrides[get_db]  # noqa
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
