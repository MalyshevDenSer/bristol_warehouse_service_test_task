import uuid
import pytest
import httpx
from tests.utils import make_envelope
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse


@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient() as ac:
        response = await ac.get("http://fastapi:8000/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_stock_empty():
    warehouse_id = uuid.uuid4()
    product_id = uuid.uuid4()

    url = f"http://fastapi:8000/warehouses/{warehouse_id}/products/{product_id}"

    async with httpx.AsyncClient() as ac:
        response = await ac.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["warehouse_id"] == str(warehouse_id)
    assert data["product_id"] == str(product_id)
    assert data["quantity"] == 0


@pytest.mark.asyncio
async def test_get_stock_after_departure_only():
    envelope = make_envelope(event="departure")
    async with httpx.AsyncClient() as ac:
        await ac.post("http://fastapi:8000/simulate_kafka", json=envelope.model_dump(mode="json"))

        url = f"http://fastapi:8000/warehouses/{envelope.data.warehouse_id}/products/{envelope.data.product_id}"
        response = await ac.get(url)

    assert response.status_code == 200
    assert response.json()["quantity"] == 0


@pytest.mark.asyncio
async def test_kafka_event_invalid_format():
    invalid_payload = {
        "id": "not-a-uuid",  # неправильный UUID
        "data": {
            "movement_id": "also-bad",
            "warehouse_id": "not-a-uuid",
            "timestamp": "not-a-date",
            "event": "fly",  # неправильный event
            "product_id": "fake",
            "quantity": "a lot"  # должен быть int
        }
    }

    async with httpx.AsyncClient() as ac:
        response = await ac.post("http://fastapi:8000/simulate_kafka", json=invalid_payload)

    assert response.status_code == 422  # FastAPI валидация


@pytest.mark.asyncio
async def test_simulate_kafka_duplicate_message():
    envelope = make_envelope()
    async with httpx.AsyncClient() as ac:
        response1 = await ac.post("http://fastapi:8000/simulate_kafka", json=envelope.model_dump(mode="json"))
        assert response1.status_code == 200

        response2 = await ac.post("http://fastapi:8000/simulate_kafka", json=envelope.model_dump(mode="json"))
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_event_type_same_movement_id():
    movement_id = uuid.uuid4()
    first_arrival = make_envelope(event="arrival", movement_id=movement_id)
    second_arrival = make_envelope(event="arrival", movement_id=movement_id)

    # Привязка к одному продукту и складу
    second_arrival.data.product_id = first_arrival.data.product_id
    second_arrival.data.warehouse_id = first_arrival.data.warehouse_id

    async with httpx.AsyncClient() as ac:
        res1 = await ac.post("http://fastapi:8000/simulate_kafka", json=first_arrival.model_dump(mode="json"))
        res2 = await ac.post("http://fastapi:8000/simulate_kafka", json=second_arrival.model_dump(mode="json"))

    assert res1.status_code == 200
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]




@pytest.mark.asyncio
async def test_get_movement_incomplete():
    movement_id = uuid.uuid4()
    envelope = make_envelope(event="departure", movement_id=movement_id)

    async with httpx.AsyncClient() as ac:
        await ac.post("http://fastapi:8000/simulate_kafka", json=envelope.model_dump(mode="json"))
        response = await ac.get(f"http://fastapi:8000/movements/{movement_id}")

    assert response.status_code == 404
    assert "incomplete" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_movement_full_cycle():
    movement_id = uuid.uuid4()
    departure = make_envelope(event="departure", movement_id=movement_id)
    arrival = make_envelope(movement_id=movement_id)
    arrival.data.product_id = departure.data.product_id
    arrival.data.warehouse_id = uuid.uuid4()  # получатель может быть другим

    async with httpx.AsyncClient() as ac:
        await ac.post("http://fastapi:8000/simulate_kafka", json=departure.model_dump(mode="json"))
        await ac.post("http://fastapi:8000/simulate_kafka", json=arrival.model_dump(mode="json"))

        url = f"http://fastapi:8000/movements/{movement_id}"
        response = await ac.get(url)

    assert response.status_code == 200
    body = response.json()
    assert body["movement_id"] == str(movement_id)
    assert body["quantity_departed"] == 100
    assert body["quantity_arrived"] == 100
    assert body["quantity_difference"] == 0
    assert body["transit_seconds"] >= 0


@pytest.mark.asyncio
async def test_get_movement_full_data():
    movement_id = uuid.uuid4()

    departure = make_envelope(event="departure", movement_id=movement_id)
    arrival = make_envelope(movement_id=movement_id)

    arrival.data.product_id = departure.data.product_id
    arrival.data.warehouse_id = departure.data.warehouse_id

    departure.data.timestamp = datetime(2025, 2, 18, 12, 0, 0, tzinfo=timezone.utc)
    arrival.data.timestamp = datetime(2025, 2, 18, 14, 30, 0, tzinfo=timezone.utc)

    departure.data.quantity = 100
    arrival.data.quantity = 95

    async with httpx.AsyncClient() as ac:
        await ac.post("http://fastapi:8000/simulate_kafka", json=departure.model_dump(mode="json"))
        await ac.post("http://fastapi:8000/simulate_kafka", json=arrival.model_dump(mode="json"))

        response = await ac.get(f"http://fastapi:8000/movements/{movement_id}")

    assert response.status_code == 200
    body = response.json()

    assert body["movement_id"] == str(movement_id)

    assert isoparse(body["departure_time"]) == departure.data.timestamp
    assert isoparse(body["arrival_time"]) == arrival.data.timestamp

    assert body["transit_seconds"] == 9000  # 2.5 часа
    assert body["quantity_departed"] == 100
    assert body["quantity_arrived"] == 95
    assert body["quantity_difference"] == -5


@pytest.mark.parametrize(
    "departure_qty, arrival_qty, transit_minutes, expected_difference",
    [
        (100, 95, 150, -5),     # arrival < departure
        (100, 100, 150, 0),     # arrival == departure
        (100, 120, 150, 20),    # arrival > departure
        (50, 0, 0, -50),        # только departure, без arrival
    ]
)
@pytest.mark.asyncio
async def test_get_movement_quantities(
    departure_qty, arrival_qty, transit_minutes, expected_difference
):
    movement_id = uuid.uuid4()

    departure = make_envelope(event="departure", movement_id=movement_id)
    arrival = make_envelope(event="arrival", movement_id=movement_id)

    arrival.data.product_id = departure.data.product_id
    arrival.data.warehouse_id = departure.data.warehouse_id

    departure_time = datetime(2025, 2, 18, 12, 0, 0, tzinfo=timezone.utc)
    arrival_time = departure_time + timedelta(minutes=transit_minutes)

    departure.data.timestamp = departure_time
    arrival.data.timestamp = arrival_time

    departure.data.quantity = departure_qty
    arrival.data.quantity = arrival_qty

    async with httpx.AsyncClient() as ac:
        await ac.post("http://fastapi:8000/simulate_kafka", json=departure.model_dump(mode="json"))
        await ac.post("http://fastapi:8000/simulate_kafka", json=arrival.model_dump(mode="json"))

        response = await ac.get(f"http://fastapi:8000/movements/{movement_id}")

    assert response.status_code == 200
    body = response.json()

    assert body["movement_id"] == str(movement_id)
    assert isoparse(body["departure_time"]) == departure_time
    assert isoparse(body["arrival_time"]) == arrival_time
    assert body["transit_seconds"] == transit_minutes * 60
    assert body["quantity_departed"] == departure_qty
    assert body["quantity_arrived"] == arrival_qty
    assert body["quantity_difference"] == expected_difference



