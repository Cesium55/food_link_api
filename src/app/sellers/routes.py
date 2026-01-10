from typing import List, Optional
from fastapi import APIRouter, Request, Depends, UploadFile, File, Query
from app.sellers import schemas
from app.sellers.manager import SellersManager
from utils.auth_dependencies import get_current_user
from utils.seller_dependencies import get_current_seller
from app.auth.models import User
from app.sellers.models import Seller
from utils.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/sellers", tags=["sellers"])

# Initialize manager
sellers_manager = SellersManager()


@router.post("", response_model=schemas.Seller, status_code=201)
async def create_seller(
    request: Request, seller_data: schemas.SellerCreate, current_user: User = Depends(get_current_user)
):
    """
    Create a new seller account for the current user.
    This will create both a user account and a seller account.
    """
    return await sellers_manager.create_seller(request.state.session, seller_data, current_user)


@router.get("/me", response_model=schemas.Seller)
async def get_my_seller(
    request: Request, current_user: User = Depends(get_current_user)
) -> schemas.Seller:
    """
    Get current user's seller account
    """
    return await sellers_manager.get_seller_by_email(request.state.session, current_user.email)


@router.get("", response_model=PaginatedResponse[schemas.PublicSeller])
async def get_sellers(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=20, ge=1, description="Number of items per page"),
    status: Optional[int] = Query(default=None, ge=0, description="Filter by seller status"),
    verification_level: Optional[int] = Query(default=None, ge=0, description="Filter by verification level")
) -> PaginatedResponse[schemas.PublicSeller]:
    """
    Get paginated list of sellers (public data only)
    """
    return await sellers_manager.get_sellers_paginated(
        request.state.session, page, page_size, status, verification_level
    )


@router.get("/{seller_id}", response_model=schemas.PublicSeller)
async def get_seller(request: Request, seller_id: int) -> schemas.PublicSeller:
    """
    Get seller by ID (public data only)
    """
    return await sellers_manager.get_seller_by_id(request.state.session, seller_id)



@router.get("/{seller_id}/with-shops", response_model=schemas.PublicSellerWithShopPoints)
async def get_seller_with_shops(
    request: Request, seller_id: int
) -> schemas.PublicSellerWithShopPoints:
    """
    Get seller with shop points (public data only)
    """
    return await sellers_manager.get_seller_with_shop_points(
        request.state.session, seller_id
    )


@router.get("/{seller_id}/with-details", response_model=schemas.PublicSellerWithDetails)
async def get_seller_with_details(
    request: Request, seller_id: int
) -> schemas.PublicSellerWithDetails:
    """
    Get seller with full details (public data only)
    """
    return await sellers_manager.get_seller_with_details(
        request.state.session, seller_id
    )


@router.put("/{seller_id}", response_model=schemas.Seller)
async def update_seller(
    request: Request,
    seller_id: int,
    seller_data: schemas.SellerUpdate,
    current_seller: Seller = Depends(get_current_seller)
) -> schemas.Seller:
    """
    Update seller (only own seller account)
    """
    return await sellers_manager.update_seller(
        request.state.session, seller_id, seller_data, current_seller
    )


@router.delete("/{seller_id}", status_code=204)
async def delete_seller(
    request: Request,
    seller_id: int,
    current_seller: Seller = Depends(get_current_seller)
) -> None:
    """
    Delete seller (only own seller account)
    """
    await sellers_manager.delete_seller(request.state.session, seller_id, current_seller)


@router.get("/summary/stats", response_model=schemas.SellerSummary)
async def get_sellers_summary(request: Request) -> schemas.SellerSummary:
    """
    Get sellers summary statistics
    """
    return await sellers_manager.get_sellers_summary(request.state.session)


@router.post("/by-ids", response_model=List[schemas.PublicSeller])
async def get_sellers_by_ids(
    request: Request, seller_ids: List[int]
) -> List[schemas.PublicSeller]:
    """
    Get sellers by list of IDs (public data only)
    """
    return await sellers_manager.get_sellers_by_ids(
        request.state.session, seller_ids
    )


@router.post("/{seller_id}/images", response_model=schemas.SellerImage, status_code=201)
async def upload_seller_image(
    request: Request,
    seller_id: int,
    file: UploadFile = File(...),
    order: int = Query(default=0, ge=0),
    current_seller: Seller = Depends(get_current_seller)
) -> schemas.SellerImage:
    """
    Upload an image for a seller (only own seller account)
    """
    return await sellers_manager.upload_seller_image(
        request.state.session, seller_id, file, order, current_seller
    )


@router.post("/{seller_id}/images/batch", response_model=List[schemas.SellerImage], status_code=201)
async def upload_seller_images(
    request: Request,
    seller_id: int,
    files: List[UploadFile] = File(...),
    start_order: int = Query(default=0, ge=0),
    current_seller: Seller = Depends(get_current_seller)
) -> List[schemas.SellerImage]:
    """
    Upload multiple images for a seller (only own seller account)
    """
    return await sellers_manager.upload_seller_images(
        request.state.session, seller_id, files, start_order, current_seller
    )


@router.delete("/images/{image_id}", status_code=204)
async def delete_seller_image(
    request: Request,
    image_id: int,
    current_seller: Seller = Depends(get_current_seller)
) -> None:
    """
    Delete a seller image (only own seller images)
    """
    await sellers_manager.delete_seller_image(request.state.session, image_id, current_seller)