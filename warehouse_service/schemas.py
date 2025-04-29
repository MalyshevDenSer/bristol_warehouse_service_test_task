from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Literal


class KafkaEventData(BaseModel):
    movement_id: UUID
    warehouse_id: UUID
    timestamp: datetime
    event: Literal["arrival", "departure"]
    product_id: UUID
    quantity: int


class KafkaEnvelope(BaseModel):
    id: UUID
    source: str
    specversion: str
    type: str
    datacontenttype: str
    dataschema: str
    time: int
    subject: str
    destination: str
    data: KafkaEventData


class StockResponse(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    quantity: int


class MovementResponse(BaseModel):
    movement_id: UUID
    sender_warehouse: UUID
    receiver_warehouse: UUID
    departure_time: datetime
    arrival_time: datetime
    quantity_departed: int
    quantity_arrived: int
    quantity_difference: int
    transit_seconds: int


class ErrorResponse(BaseModel):
    detail: str
