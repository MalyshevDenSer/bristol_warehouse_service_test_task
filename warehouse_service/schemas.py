from pydantic import BaseModel
from datetime import datetime

class KafkaMovementEvent(BaseModel):
    movement_id: str
    warehouse_id: str
    timestamp: datetime
    event: str  # "arrival" or "departure"
    product_id: str
    quantity: int

class MovementResponse(BaseModel):
    movement_id: str
    from_warehouse: str
    to_warehouse: str
    product_id: str
    quantity_sent: int
    quantity_received: int
    time_diff_seconds: int

class StockResponse(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: int