from fastapi import FastAPI
from services.movements import router as movements_router
from services.stock import router as stock_router
from devtools.debug_routes import router as debug_router

app = FastAPI(title="Warehouse Monitoring Service")

app.include_router(movements_router, prefix="/api/movements", tags=["Movements"])
app.include_router(stock_router, prefix="/api/warehouses", tags=["Stock"])
app.include_router(debug_router, prefix="/dev", tags=["DevTools"])