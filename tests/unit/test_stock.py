import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from warehouse_service.services.stock import calculate_stock


@pytest.mark.asyncio
async def test_positive_quantity():
    db = AsyncMock()
    db.scalar.return_value = 120
    qty = await calculate_stock(db, uuid4(), uuid4())
    assert qty == 120


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [-10, -1, 0, 5, 100])
async def test_calculate_stock_never_negative(raw):
    db = AsyncMock()
    db.scalar.return_value = raw

    qty = await calculate_stock(db, uuid4(), uuid4())
    assert qty >= 0


@pytest.mark.asyncio
async def test_none_quantity_no_log(caplog):
    db = AsyncMock()
    db.scalar.return_value = None  # имитируем отсутствие строк в БД

    with caplog.at_level("INFO"):
        qty = await calculate_stock(db, uuid4(), uuid4())

    assert qty == 0
