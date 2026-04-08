from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.shop_points.models import ShopPoint
from app.sellers.models import Seller
from config import settings
from app.shop_points.service import ShopPointsService

router = APIRouter(prefix="/maps", tags=["maps"])

templates = Jinja2Templates(directory="src/templates")


def _build_seller_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None

    normalized_path = image_path.strip()
    if not normalized_path:
        return None

    if normalized_path.startswith(("http://", "https://")):
        return normalized_path

    if normalized_path.startswith("s3://"):
        parts = normalized_path.replace("s3://", "", 1).split("/", 1)
        if len(parts) == 2:
            normalized_path = parts[1]
        else:
            normalized_path = parts[0]

    return f"{settings.s3_public_prefix.rstrip('/')}/{normalized_path.lstrip('/')}"


@router.get("/shop-points-markers", response_class=HTMLResponse)
async def get_shop_points_map(request: Request) -> HTMLResponse:
    """
    Display all shop points on Yandex Map
    
    Returns:
        HTML page with map showing all shop points
    """
    session: AsyncSession = request.state.session
    shop_points_service = ShopPointsService()
    
    # Get all shop points with coordinates
    shop_points = await shop_points_service.get_shop_points(session)
    
    # Prepare markers data
    markers = []
    for shop_point in shop_points:
        if shop_point.latitude and shop_point.longitude:
            markers.append({
                "coordinates": [shop_point.longitude, shop_point.latitude],
                "label": f"{shop_point.id}",
                "title": shop_point.address_formated or shop_point.address_raw or "Shop Point",
                "id": shop_point.id,
                "seller_id": shop_point.seller_id,
                "address_raw": shop_point.address_raw,
                "address_formated": shop_point.address_formated,
                "region": shop_point.region,
                "city": shop_point.city,
                "street": shop_point.street,
                "house": shop_point.house,
                "geo_id": shop_point.geo_id,
                "latitude": shop_point.latitude,
                "longitude": shop_point.longitude
            })
    
    # If no markers, show default location (Moscow)
    if not markers:
        markers = [{"coordinates": [37.6176, 55.7558], "label": "0", "title": "No shop points"}]
    
    return templates.TemplateResponse(
        "just_map.html",
        {
            "request": request,
            "yandex_map_api_key": settings.yandex_map_api_key,
            "markers": markers
        }
    )


@router.get("/shop-points", response_class=HTMLResponse)
async def get_shop_points_seller_bubbles_map(request: Request) -> HTMLResponse:
    """
    Display all shop points on Yandex Map with seller avatar bubble markers.

    Returns:
        HTML page with map showing all shop points using circular seller-image markers
    """
    session: AsyncSession = request.state.session

    result = await session.execute(
        select(ShopPoint)
        .options(
            selectinload(ShopPoint.seller).selectinload(Seller.images),
            selectinload(ShopPoint.images),
        )
        .order_by(ShopPoint.id)
    )
    shop_points = result.scalars().all()

    markers = []
    for shop_point in shop_points:
        if not shop_point.latitude or not shop_point.longitude:
            continue

        seller = shop_point.seller
        seller_image_path = None
        if seller and seller.images:
            seller_image_path = seller.images[0].path

        markers.append(
            {
                "coordinates": [shop_point.longitude, shop_point.latitude],
                "label": f"{shop_point.id}",
                "title": shop_point.address_formated or shop_point.address_raw or "Shop Point",
                "id": shop_point.id,
                "seller_id": shop_point.seller_id,
                "seller_name": seller.short_name if seller else None,
                "seller_image_url": _build_seller_image_url(seller_image_path),
                "address_raw": shop_point.address_raw,
                "address_formated": shop_point.address_formated,
                "region": shop_point.region,
                "city": shop_point.city,
                "street": shop_point.street,
                "house": shop_point.house,
                "geo_id": shop_point.geo_id,
                "latitude": shop_point.latitude,
                "longitude": shop_point.longitude,
            }
        )

    if not markers:
        markers = [
            {
                "coordinates": [37.6176, 55.7558],
                "label": "0",
                "title": "No shop points",
                "seller_name": "SP",
                "seller_image_url": None,
            }
        ]

    return templates.TemplateResponse(
        "just_map_seller_bubbles.html",
        {
            "request": request,
            "yandex_map_api_key": settings.yandex_map_api_key,
            "markers": markers,
        },
    )
