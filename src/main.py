from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session_generator
from app.sellers.models import Seller
from config import settings

from app.sellers.routes import router as sellers_router
from app.shop_points.routes import router as shop_points_router
from app.products.routes import router as products_router
from app.inventory.routes import router as inventory_router
from app.product_categories.routes import router as product_categories_router
from app.auth.routes import router as auth_router
from app.debug.routes import router as debug_router

from middleware.insert_session_middleware import InsertSessionMiddleware
from middleware.timing_middleware import TimingMiddleware
from middleware.response_wrapper_middleware import ResponseWrapperMiddleware

app = FastAPI(
    title=settings.app_name,
    description=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

app.add_middleware(TimingMiddleware)
app.add_middleware(InsertSessionMiddleware)
app.add_middleware(ResponseWrapperMiddleware)

app.include_router(auth_router)
app.include_router(sellers_router)
app.include_router(shop_points_router)
app.include_router(products_router)
# app.include_router(inventory_router)
app.include_router(product_categories_router)
app.include_router(debug_router)


@app.get("/")
def index():
    return {"message": "Hello, World!"}