"""Celery application configuration"""
from celery import Celery
from config import settings

# Импортируем все модели для правильной инициализации SQLAlchemy relationships
# Важно: импортируем в правильном порядке, чтобы избежать проблем с relationships
from app.auth.models import User, RefreshToken  # noqa: F401
from app.sellers.models import Seller, SellerImage  # noqa: F401
from app.shop_points.models import ShopPoint, ShopPointImage  # noqa: F401
from app.products.models import Product, ProductImage  # noqa: F401
from app.product_categories.models import ProductCategory, product_category_relations  # noqa: F401
from app.offers.models import Offer  # noqa: F401
from app.purchases.models import Purchase, PurchaseOffer  # noqa: F401

# Создаем Celery приложение
celery_app = Celery(
    "food_link",
    broker=settings.celery_broker_url or "redis://localhost:6379/0",
    backend=settings.celery_result_backend or "redis://localhost:6379/0",
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Импортируем задачи явно после инициализации всех моделей
# Это гарантирует, что все relationships будут правильно настроены
from app.purchases import tasks  # noqa: F401

