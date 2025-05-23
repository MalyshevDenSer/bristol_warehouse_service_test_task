from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from warehouse_service.db import get_db
from warehouse_service.models import Movement
from warehouse_service.schemas import StockResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{warehouse_id}/products/{product_id}", response_model=StockResponse, summary="Текущий запас товара на складе")
def get_stock(warehouse_id: str, product_id: str, db: Session = Depends(get_db)):
    arrivals = db.query(func.sum(Movement.quantity)).filter(
        Movement.warehouse_id == warehouse_id,
        Movement.product_id == product_id,
        Movement.event == "arrival"
    ).scalar() or 0

    departures = db.query(func.sum(Movement.quantity)).filter(
        Movement.warehouse_id == warehouse_id,
        Movement.product_id == product_id,
        Movement.event == "departure"
    ).scalar() or 0

    quantity = arrivals - departures
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Остаток ниже нуля, так нельзя")

    return StockResponse(
        warehouse_id=warehouse_id,
        product_id=product_id,
        quantity=quantity
    )