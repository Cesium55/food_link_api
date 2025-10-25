from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Dict, Any
from sqlalchemy import text
from app.debug.init import DebugDataInitializer
from src.config import settings
from src.database import sync_engine
from src.models import Base
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/debug", tags=["debug"])

# Initialize data initializer
initializer = DebugDataInitializer()

templates = Jinja2Templates(directory="src/templates")

@router.post("/init-test-data")
async def initialize_test_data(request: Request) -> Dict[str, Any]:
    """
    Initialize application with test data for all domains except inventory.
    This will create product categories, sellers, shop points, and products.
    Each step is independent and can be run multiple times safely.
    """
    try:
        result = await initializer.initialize_all_data()
        return {
            "success": True,
            "message": "Test data initialization completed successfully",
            "steps_completed": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize test data: {str(e)}"
        )


@router.post("/init-categories")
async def initialize_categories(request: Request) -> Dict[str, Any]:
    """
    Initialize product categories only.
    """
    try:
        result = await initializer.get_or_create_categories()
        return {
            "success": True,
            "message": "Product categories initialized successfully",
            "categories_created": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize categories: {str(e)}"
        )


@router.post("/wipe-db-hard")
async def wipe_database_hard(request: Request) -> Dict[str, Any]:
    """
    Полная очистка БД, независимо от связей.
    Действие опасно: удаляет ВСЕ таблицы и пересоздаёт схему по текущим моделям.
    Доступно только при settings.debug = True.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403, detail="Wipe is allowed only in debug mode"
        )

    try:
        with sync_engine.begin() as conn:
            # Отразим текущую схему, чтобы удалить все таблицы даже без импортов моделей
            Base.metadata.reflect(bind=conn)
            Base.metadata.drop_all(bind=conn)

            # Импортируем модели, чтобы пересоздать таблицы по коду
            from app.sellers.models import Seller, SellerImage  # noqa: F401
            from app.shop_points.models import ShopPoint, ShopPointImage  # noqa: F401
            from app.products.models import (
                Product,
                ProductImage,
                ProductEntry,
            )  # noqa: F401
            from app.product_categories.models import (
                ProductCategory,
                product_category_relations,
            )  # noqa: F401
            from app.auth.models import User, RefreshToken  # noqa: F401

            # Пересоздание пустой схемы
            Base.metadata.create_all(bind=conn)

        return {"success": True, "message": "Database wiped and recreated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to wipe database: {str(e)}"
        )


@router.post("/init-sellers")
async def initialize_sellers(request: Request) -> Dict[str, Any]:
    """
    Initialize sellers only.
    """
    try:
        result = await initializer.get_or_create_sellers()
        return {
            "success": True,
            "message": "Sellers initialized successfully",
            "sellers_created": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize sellers: {str(e)}"
        )


@router.post("/init-shop-points")
async def initialize_shop_points(request: Request) -> Dict[str, Any]:
    """
    Initialize shop points only.
    """
    try:
        # First get sellers
        sellers = await initializer.get_or_create_sellers()
        if not sellers:
            return {
                "success": False,
                "message": "No sellers found. Please initialize sellers first.",
                "shop_points_created": [],
            }

        result = await initializer.get_or_create_shop_points(sellers)
        return {
            "success": True,
            "message": "Shop points initialized successfully",
            "shop_points_created": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize shop points: {str(e)}"
        )


@router.post("/init-products")
async def initialize_products(request: Request) -> Dict[str, Any]:
    """
    Initialize products only.
    """
    try:
        # First get sellers and categories
        sellers = await initializer.get_or_create_sellers()
        categories = await initializer.get_or_create_categories()

        if not sellers:
            return {
                "success": False,
                "message": "No sellers found. Please initialize sellers first.",
                "products_created": [],
            }

        if not categories:
            return {
                "success": False,
                "message": "No categories found. Please initialize categories first.",
                "products_created": [],
            }

        result = await initializer.get_or_create_products(sellers, categories)
        return {
            "success": True,
            "message": "Products initialized successfully",
            "products_created": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize products: {str(e)}"
        )


@router.delete("/clear-database")
async def clear_database(request: Request) -> Dict[str, Any]:
    """
    Clear all data from the database.
    This will delete all products, shop points, sellers, and categories.
    WARNING: This action is irreversible!
    """
    if not settings.debug:
        raise HTTPException(
            status_code=403, detail="Clear is allowed only in debug mode"
        )

    try:
        # Прямая очистка через БД сессию
        session = request.state.session

        # Импортируем модели для прямого удаления
        from app.products.models import Product, ProductImage, ProductEntry
        from app.shop_points.models import ShopPoint, ShopPointImage
        from app.sellers.models import Seller, SellerImage
        from app.product_categories.models import (
            ProductCategory,
            product_category_relations,
        )
        from app.auth.models import User, RefreshToken

        cleared_entities = {
            "products": 0,
            "shop_points": 0,
            "sellers": 0,
            "categories": 0,
            "users": 0,
        }

        # Удаляем в правильном порядке (сначала зависимые таблицы)
        from sqlalchemy import text

        # Продукты и их изображения
        products_result = await session.execute(text("DELETE FROM products"))
        cleared_entities["products"] = products_result.rowcount

        # Точки продаж и их изображения
        shop_points_result = await session.execute(text("DELETE FROM shop_points"))
        cleared_entities["shop_points"] = shop_points_result.rowcount

        # Продавцы и их изображения
        sellers_result = await session.execute(text("DELETE FROM sellers"))
        cleared_entities["sellers"] = sellers_result.rowcount

        # Категории продуктов
        categories_result = await session.execute(
            text("DELETE FROM product_categories")
        )
        cleared_entities["categories"] = categories_result.rowcount

        # Пользователи (осторожно!)
        users_result = await session.execute(text("DELETE FROM users"))
        cleared_entities["users"] = users_result.rowcount

        await session.commit()

        return {
            "success": True,
            "message": "Database cleared successfully",
            "cleared_entities": cleared_entities,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to clear database: {str(e)}"
        )


@router.get("/status")
async def get_initialization_status(request: Request) -> Dict[str, Any]:
    """
    Get current status of initialized data.
    """
    try:
        # Get counts of existing data
        sellers = await initializer.get_or_create_sellers()
        categories = await initializer.get_or_create_categories()

        # For shop points and products, we need to make separate requests
        # since they depend on sellers
        shop_points_count = 0
        products_count = 0

        if sellers:
            shop_points = await initializer.get_or_create_shop_points(sellers)
            shop_points_count = len(shop_points)

            if categories:
                products = await initializer.get_or_create_products(sellers, categories)
                products_count = len(products)

        status = {
            "sellers": len(sellers),
            "categories": len(categories),
            "shop_points": shop_points_count,
            "products": products_count,
        }

        return {"success": True, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")



@router.get("/map", response_class=HTMLResponse)
async def get_yandex_map(
    width: int = Query(800, description="Ширина карты в пикселях"),
    height: int = Query(600, description="Высота карты в пикселях")
):
    html_content = f"""
<!DOCTYPE html>
<html style="margin: 0; padding: 0; height: 100%;">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        #app {{
            width: 100%;
            height: 100%;
        }}
    </style>
    <script src="https://api-maps.yandex.ru/v3/?apikey={settings.yandex_map_api_key}&lang=ru_RU"></script>
</head>
<body>
    <div id="app"></div>
    <script>
        window.addEventListener('load', function() {{
            async function initMap() {{
                try {{
                    await ymaps3.ready;

                    const {{ YMap, YMapDefaultSchemeLayer }} = ymaps3;

                    const map = new YMap(
                        document.getElementById('app'),
                        {{
                            location: {{
                                center: [37.588144, 55.733842],
                                zoom: 10
                            }}
                        }}
                    );

                    map.addChild(new YMapDefaultSchemeLayer());
                }} catch (error) {{
                    console.error('Ошибка инициализации карты:', error);
                }}
            }}

            initMap();
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/template", response_class=HTMLResponse)
async def get_template(request: Request) -> Dict[str, Any]:
    return templates.TemplateResponse("just_map.html", {"request": request, "yandex_map_api_key": settings.yandex_map_api_key})