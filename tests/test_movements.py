import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def setup_movements(test_db_session):
    from warehouse_service.models import Movement
    from datetime import datetime, timedelta

    dep = Movement(
        movement_id="test-1",
        warehouse_id="WH-1",
        timestamp=datetime.utcnow() - timedelta(minutes=5),
        event="departure",
        product_id="P-1",
        quantity=100
    )
    arr = Movement(
        movement_id="test-1",
        warehouse_id="WH-2",
        timestamp=datetime.utcnow(),
        event="arrival",
        product_id="P-1",
        quantity=100
    )
    test_db_session.add_all([dep, arr])
    test_db_session.commit()
    yield
    test_db_session.query(Movement).delete()
    test_db_session.commit()


def test_get_movement_success(setup_movements):
    response = client.get("/api/movements/test-1")
    assert response.status_code == 200
    data = response.json()
    assert data["from_warehouse"] == "WH-1"
    assert data["to_warehouse"] == "WH-2"
    assert data["quantity_sent"] == 100
    assert data["quantity_received"] == 100


def test_get_movement_not_found():
    response = client.get("/api/movements/nonexistent")
    assert response.status_code == 404
