import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.responses import JSONResponse

from warehouse_service.services.movements import get_movement_info


@pytest.mark.asyncio
async def test_happy_path():
    wid_from, wid_to, mid = uuid4(), uuid4(), uuid4()
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(hours=2)

    dep = SimpleNamespace(event="departure", warehouse_id=wid_from,
                          timestamp=t0, quantity=100)
    arr = SimpleNamespace(event="arrival", warehouse_id=wid_to,
                          timestamp=t1, quantity=90)

    db = AsyncMock()
    db.scalars.return_value = [dep, arr]

    resp = await get_movement_info(db, mid)

    assert resp.movement_id == mid
    assert resp.quantity_difference == -10
    assert resp.transit_seconds == int((t1 - t0).total_seconds())


# ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_incomplete_returns_404():
    db = AsyncMock()
    db.scalars.return_value = []            # пустой ответ

    resp = await get_movement_info(db, uuid4())

    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 404
    body = json.loads(resp.body)
    assert body["detail"] == "Movement incomplete or not found"


# ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_missing_arrival_returns_404():
    """Есть departure, но нет arrival → JSONResponse 404."""
    movement_id = uuid4()
    t0 = datetime.now(timezone.utc)

    departure_event = SimpleNamespace(
        event="departure",
        warehouse_id=uuid4(),
        timestamp=t0,
        quantity=5,
    )

    db = AsyncMock()
    db.scalars.side_effect = [
        [departure_event],  # первый вызов get_movement_events
    ]

    resp = await get_movement_info(db, movement_id)

    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 404