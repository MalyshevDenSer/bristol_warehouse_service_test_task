# tests/unit/test_event_type.py
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import ValidationError

from warehouse_service.schemas import KafkaEventData


def _make(event: str) -> KafkaEventData:
    """Создаём минимально-валидный объект KafkaEventData."""
    return KafkaEventData(
        movement_id=uuid4(),
        warehouse_id=uuid4(),
        product_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        event=event,
        quantity=1,
    )


def test_event_allows_only_arrival_or_departure():
    # оба допустимых значения проходят без ошибок
    for ev in ("arrival", "departure"):
        _make(ev)

    # любое другое значение должно приводить к ValidationError
    with pytest.raises(ValidationError):
        _make("the_arrival_of_endless_amounts_of_beer")
