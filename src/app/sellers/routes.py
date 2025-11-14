from typing import List
from fastapi import APIRouter, Request, Depends
from app.sellers import schemas
from app.sellers.manager import SellersManager
from utils.auth_dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/sellers", tags=["sellers"])

# Initialize manager
sellers_manager = SellersManager()


@router.post("", response_model=schemas.SellerBase, status_code=201)
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


@router.get("", response_model=List[schemas.PublicSeller])
async def get_sellers(request: Request) -> List[schemas.PublicSeller]:
    """
    Get list of sellers (public data only)
    """
    return await sellers_manager.get_sellers(request.state.session)


@router.get("/{seller_id}", response_model=schemas.PublicSeller)
async def get_seller(request: Request, seller_id: int) -> schemas.PublicSeller:
    """
    Get seller by ID (public data only)
    """
    return await sellers_manager.get_seller_by_id(request.state.session, seller_id)


# NOTE: This endpoint is not exposed for security reasons (exposes sensitive data)
# Use GET /me for authenticated users to get their own seller data
# @router.get("/email/{email}", response_model=schemas.Seller)
# async def get_seller_by_email(request: Request, email: str) -> schemas.Seller:
#     """
#     Get seller by email
#     """
#     return await sellers_manager.get_seller_by_email(request.state.session, email)


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
    request: Request, seller_id: int, seller_data: schemas.SellerUpdate
) -> schemas.Seller:
    """
    Update seller
    """
    return await sellers_manager.update_seller(
        request.state.session, seller_id, seller_data
    )


@router.delete("/{seller_id}", status_code=204)
async def delete_seller(request: Request, seller_id: int) -> None:
    """
    Delete seller
    """
    await sellers_manager.delete_seller(request.state.session, seller_id)


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