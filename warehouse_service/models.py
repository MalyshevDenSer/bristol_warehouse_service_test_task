from sqlalchemy import Column, String, DateTime, Integer
from warehouse_service.db import Base

class Movement(Base):
    __tablename__ = "movements"

    movement_id = Column(String, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    timestamp = Column(DateTime)
    event = Column(String)  # "arrival" or "departure"
    product_id = Column(String)
    quantity = Column(Integer)