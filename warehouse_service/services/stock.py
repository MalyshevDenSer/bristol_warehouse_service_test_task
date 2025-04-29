from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from warehouse_service.models import MovementEvent
from uuid import UUID
from warehouse_service.logger import setup_logger

logger = setup_logger("warehouse_service.services.stock")


async def calculate_stock(db: AsyncSession, warehouse_id: UUID, product_id: UUID) -> int:
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (MovementEvent.event == "arrival", MovementEvent.quantity),
                    (MovementEvent.event == "departure", -MovementEvent.quantity),
                    else_=0
                )
            ),
            0
        )
    ).where(
        MovementEvent.warehouse_id == warehouse_id,
        MovementEvent.product_id == product_id
    )

    result = await db.scalar(stmt)
    raw_quantity = result or 0
    quantity = max(raw_quantity, 0)

    if raw_quantity < 0:
        logger.info(
            f"Отрицательное значение остатков: склад {warehouse_id}, товар {product_id}, "
            f"рассчитано {raw_quantity}, возвращаю 0"
        )

    return quantity
