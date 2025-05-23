from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from warehouse_service.db import get_db
from warehouse_service.models import Movement
from warehouse_service.schemas import MovementResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{movement_id}", response_model=MovementResponse, summary="Получение информации о перемещении", description="Возвращает отправителя, получателя, время и количество")
def get_movement(movement_id: str, db: Session = Depends(get_db)):
    logger.info(f"Получен запрос перемещения: {movement_id}")
    movements = db.query(Movement).filter(Movement.movement_id == movement_id).all()
    if len(movements) != 2:
        raise HTTPException(status_code=404, detail="Перемещение не полное")

    dep = next((m for m in movements if m.event == "departure"), None)
    arr = next((m for m in movements if m.event == "arrival"), None)

    if not dep or not arr:
        raise HTTPException(status_code=404, detail="Не хватает перемещения")

    return MovementResponse(
        movement_id=movement_id,
        from_warehouse=dep.warehouse_id,
        to_warehouse=arr.warehouse_id,
        product_id=dep.product_id,
        quantity_sent=dep.quantity,
        quantity_received=arr.quantity,
        time_diff_seconds=int((arr.timestamp - dep.timestamp).total_seconds())
    )