from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_session_generator
from app.sellers.models import Seller
from config import settings
from app.auth.jwt_utils import JWTUtils

from app.sellers.routes import router as sellers_router
from app.shop_points.routes import router as shop_points_router
from app.products.routes import router as products_router
from app.offers.routes import router as offers_router
from app.product_categories.routes import router as product_categories_router
from app.auth.routes import router as auth_router
from app.debug.routes import router as debug_router
from app.maps.routes import router as maps_router
from app.purchases.routes import router as purchases_router
from app.payments.routes import router as payments_router

from middleware.insert_session_middleware import InsertSessionMiddleware
from middleware.timing_middleware import TimingMiddleware
from middleware.response_wrapper_middleware import ResponseWrapperMiddleware
from utils.image_manager import ImageManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    # Initialize MinIO bucket and set public policy
    try:
        image_manager = ImageManager()
        await image_manager.initialize_bucket()
    except Exception as e:
        # Log error but don't fail startup
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize MinIO bucket: {str(e)}")
    
    yield
    
    # Shutdown

app = FastAPI(
    title=settings.app_name,
    description=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

app.add_middleware(TimingMiddleware)
app.add_middleware(InsertSessionMiddleware)
app.add_middleware(ResponseWrapperMiddleware)

app.include_router(auth_router)
app.include_router(sellers_router)
app.include_router(shop_points_router)
app.include_router(products_router)
app.include_router(offers_router)
app.include_router(product_categories_router)
app.include_router(purchases_router)
app.include_router(payments_router)
app.include_router(debug_router)
app.include_router(maps_router)


@app.get("/")
def index():
    return {"message": "Hello, World!"}


@app.get("/public-key")
def get_public_key():
    """
    Get public key for JWT verification in PEM format.
    Returns the raw public key that can be used to verify JWT tokens.
    """
    try:
        jwt_utils = JWTUtils()
        public_key = jwt_utils.get_public_key()
        return {"public_key": public_key}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JWT algorithm does not support public key export: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading public key: {str(e)}"
        )