from uuid import UUID

from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from warehouse_service.models import MovementEvent
from warehouse_service.schemas import MovementResponse


async def get_movement_events(db, movement_id):
    stmt = select(MovementEvent).where(MovementEvent.movement_id == movement_id)
    result = await db.scalars(stmt)
    events = list(result)
    departure = next((e for e in events if e.event == "departure"), None)
    arrival = next((e for e in events if e.event == "arrival"), None)

    return departure, arrival


async def get_movement_info(db: AsyncSession, movement_id: UUID) -> MovementResponse | JSONResponse:
    departure, arrival = await get_movement_events(db, movement_id)

    if not departure or not arrival:
        return JSONResponse(
            status_code=404, content={
                'detail': 'Movement incomplete or not found'
            }
        )

    quantity_diff = arrival.quantity - departure.quantity
    transit = int((arrival.timestamp - departure.timestamp).total_seconds())

    return MovementResponse(
        movement_id=movement_id,
        sender_warehouse=departure.warehouse_id,
        receiver_warehouse=arrival.warehouse_id,
        departure_time=departure.timestamp,
        arrival_time=arrival.timestamp,
        quantity_departed=departure.quantity,
        quantity_arrived=arrival.quantity,
        quantity_difference=quantity_diff,
        transit_seconds=transit
    )
