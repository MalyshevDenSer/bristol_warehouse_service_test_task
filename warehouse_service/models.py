from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy import UniqueConstraint


class Base(DeclarativeBase):
    pass


class MovementEvent(Base):
    __tablename__ = "movement_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[UUID] = mapped_column(SQLUUID, unique=True)
    movement_id: Mapped[UUID]
    warehouse_id: Mapped[UUID]
    product_id: Mapped[UUID]
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event: Mapped[str]
    quantity: Mapped[int]

    __table_args__ = (
        # «один тип события (`arrival`/`departure`) на одно движение»
        UniqueConstraint("movement_id", "event",
                         name="uix_movement_id_event_type"),
    )
