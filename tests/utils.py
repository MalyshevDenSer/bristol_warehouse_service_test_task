from uuid import uuid4
from datetime import datetime, timezone
from app.schemas import KafkaEnvelope, KafkaEventData


def make_envelope(event: str = "arrival", movement_id=None) -> KafkaEnvelope:
    movement_id = movement_id or uuid4()
    return KafkaEnvelope(
        id=uuid4(),
        source="test",
        specversion="1.0",
        type="ru.retail.warehouses.movement",
        datacontenttype="application/json",
        dataschema="ru.retail.warehouses.movement.v1.0",
        time=int(datetime.now(tz=timezone.utc).timestamp()),
        subject=f"test:{event.upper()}",
        destination="ru.retail.warehouses",
        data=KafkaEventData(
            movement_id=movement_id,
            warehouse_id=uuid4(),
            product_id=uuid4(),
            timestamp=datetime.now(tz=timezone.utc),
            event=event,
            quantity=100,
        )
    )
