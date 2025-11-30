from typing import List
from fastapi import APIRouter, Request, Depends, UploadFile, File, Query
from app.shop_points import schemas
from app.shop_points.manager import ShopPointsManager
from utils.auth_dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/shop-points", tags=["shop-points"])

# Initialize manager
shop_points_manager = ShopPointsManager()


@router.post("", response_model=schemas.ShopPoint, status_code=201)
async def create_shop_point(
    request: Request, shop_point_data: schemas.ShopPointCreate
) -> schemas.ShopPoint:
    """
    Create a new shop point
    """
    return await shop_points_manager.create_shop_point(request.state.session, shop_point_data)


@router.get("", response_model=List[schemas.ShopPoint])
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


@router.get("/seller/{seller_id}", response_model=List[schemas.ShopPoint])
async def get_shop_points_by_seller(request: Request, seller_id: int) -> List[schemas.ShopPoint]:
    """
    Get shop points by seller ID
    """
    return await shop_points_manager.get_shop_points_by_seller(request.state.session, seller_id)


@router.get("/{shop_point_id}/with-seller", response_model=schemas.ShopPointWithSeller)
async def get_shop_point_with_seller(request: Request, shop_point_id: int) -> schemas.ShopPointWithSeller:
    """
    Get shop point with seller information
    """
    return await shop_points_manager.get_shop_point_with_seller(request.state.session, shop_point_id)


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


@router.post("/by-address", response_model=schemas.ShopPoint, status_code=201)
async def create_shop_point_by_address(
    request: Request,
    shop_point_data: schemas.ShopPointCreateByAddress,
    current_user: User = Depends(get_current_user)
) -> schemas.ShopPoint:
    """
    Create a new shop point by raw address (will be geocoded automatically)
    Address must be in Russia
    Requires authentication and user must be a seller
    """
    return await shop_points_manager.create_shop_point_by_address(
        request.state.session, current_user.id, shop_point_data
    )


@router.post("/{shop_point_id}/images", response_model=schemas.ShopPointImage, status_code=201)
async def upload_shop_point_image(
    request: Request,
    shop_point_id: int,
    file: UploadFile = File(...),
    order: int = Query(default=0, ge=0)
) -> schemas.ShopPointImage:
    """
    Upload an image for a shop point
    """
    return await shop_points_manager.upload_shop_point_image(
        request.state.session, shop_point_id, file, order
    )


@router.post("/{shop_point_id}/images/batch", response_model=List[schemas.ShopPointImage], status_code=201)
async def upload_shop_point_images(
    request: Request,
    shop_point_id: int,
    files: List[UploadFile] = File(...),
    start_order: int = Query(default=0, ge=0)
) -> List[schemas.ShopPointImage]:
    """
    Upload multiple images for a shop point
    """
    return await shop_points_manager.upload_shop_point_images(
        request.state.session, shop_point_id, files, start_order
    )


@router.delete("/images/{image_id}", status_code=204)
async def delete_shop_point_image(request: Request, image_id: int) -> None:
    """
    Delete a shop point image
    """
    await shop_points_manager.delete_shop_point_image(request.state.session, image_id)