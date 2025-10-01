from typing import List
from fastapi import APIRouter, Request
from app.shop_points import schemas
from app.shop_points.manager import ShopPointsManager

router = APIRouter(prefix="/shop-points", tags=["shop-points"])

# Initialize manager
shop_points_manager = ShopPointsManager()


@router.post("/", response_model=schemas.ShopPoint, status_code=201)
async def create_shop_point(
    request: Request, shop_point_data: schemas.ShopPointCreate
) -> schemas.ShopPoint:
    """
    Create a new shop point
    """
    return await shop_points_manager.create_shop_point(request.state.session, shop_point_data)


@router.get("/", response_model=List[schemas.ShopPoint])
async def get_shop_points(request: Request) -> List[schemas.ShopPoint]:
    """
    Get list of shop points
    """
    return await shop_points_manager.get_shop_points(request.state.session)


@router.get("/{shop_point_id}", response_model=schemas.ShopPoint)
async def get_shop_point(request: Request, shop_point_id: int) -> schemas.ShopPoint:
    """
    Get shop point by ID
    """
    return await shop_points_manager.get_shop_point_by_id(request.state.session, shop_point_id)


@router.get("/network/{network_id}", response_model=List[schemas.ShopPoint])
async def get_shop_points_by_network(request: Request, network_id: int) -> List[schemas.ShopPoint]:
    """
    Get shop points by network ID
    """
    return await shop_points_manager.get_shop_points_by_network(request.state.session, network_id)


@router.get("/{shop_point_id}/with-network", response_model=schemas.ShopPointWithNetwork)
async def get_shop_point_with_network(request: Request, shop_point_id: int) -> schemas.ShopPointWithNetwork:
    """
    Get shop point with network information
    """
    return await shop_points_manager.get_shop_point_with_network(request.state.session, shop_point_id)


@router.put("/{shop_point_id}", response_model=schemas.ShopPoint)
async def update_shop_point(
    request: Request,
    shop_point_id: int, 
    shop_point_data: schemas.ShopPointUpdate
) -> schemas.ShopPoint:
    """
    Update shop point
    """
    return await shop_points_manager.update_shop_point(request.state.session, shop_point_id, shop_point_data)


@router.delete("/{shop_point_id}", status_code=204)
async def delete_shop_point(request: Request, shop_point_id: int) -> None:
    """
    Delete shop point
    """
    await shop_points_manager.delete_shop_point(request.state.session, shop_point_id)


@router.get("/summary/stats", response_model=schemas.ShopPointSummary)
async def get_shop_points_summary(request: Request) -> schemas.ShopPointSummary:
    """
    Get shop points summary statistics
    """
    return await shop_points_manager.get_shop_points_summary(request.state.session)


@router.post("/by-ids", response_model=List[schemas.ShopPoint])
async def get_shop_points_by_ids(
    request: Request, shop_point_ids: List[int]
) -> List[schemas.ShopPoint]:
    """
    Get shop points by list of IDs
    """
    return await shop_points_manager.get_shop_points_by_ids(request.state.session, shop_point_ids)