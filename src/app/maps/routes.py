from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from app.shop_points.service import ShopPointsService

router = APIRouter(prefix="/maps", tags=["maps"])

templates = Jinja2Templates(directory="src/templates")


@router.get("/shop-points", response_class=HTMLResponse)
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
