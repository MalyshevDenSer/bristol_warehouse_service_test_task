import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def setup_stock(test_db_session):
    from warehouse_service.models import Movement
    from datetime import datetime

    m1 = Movement(
        movement_id="stock-1",
        warehouse_id="WH-STOCK",
        timestamp=datetime.utcnow(),
        event="arrival",
        product_id="P-STOCK",
        quantity=150
    )
    m2 = Movement(
        movement_id="stock-2",
        warehouse_id="WH-STOCK",
        timestamp=datetime.utcnow(),
        event="departure",
        product_id="P-STOCK",
        quantity=50
    )
    test_db_session.add_all([m1, m2])
    test_db_session.commit()
    yield
    test_db_session.query(Movement).delete()
    test_db_session.commit()


def test_get_stock_success(setup_stock):
    response = client.get("/api/warehouses/WH-STOCK/products/P-STOCK")
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 100


def test_get_stock_negative():
    response = client.get("/api/warehouses/WH-NOPE/products/P-NEG")
    assert response.status_code == 200
    assert response.json()["quantity"] == 0