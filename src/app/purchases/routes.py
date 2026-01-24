from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from app.purchases import schemas
from app.purchases.manager import PurchasesManager
from utils.auth_dependencies import get_current_user
from app.auth.models import User
from utils.response_logger import log_response
from utils.pagination import PaginatedResponse
from utils.debug_logger import hard_log

router = APIRouter(prefix="/purchases", tags=["purchases"])

# Initialize manager
purchases_manager = PurchasesManager()


@router.post("", response_model=schemas.PurchaseWithOffers, status_code=201)
@log_response()
async def create_purchase(
    request: Request,
    purchase_data: schemas.PurchaseCreate,
    current_user: User = Depends(get_current_user)
) -> schemas.PurchaseWithOffers:
    """
    Create a new purchase order with partial success support.
    Processes each offer individually and returns detailed results.
    Validates availability, checks expiration dates, reserves items, and calculates total cost.
    If an offer has insufficient quantity, it will be added with available quantity.
    """
    hard_log(f"POST /purchases START - user_id={current_user.id}, offers={len(purchase_data.offers)}", "ROUTES")
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    result = await purchases_manager.create_purchase_with_partial_success(
        request.state.session, current_user.id, purchase_data, base_url
    )
    hard_log(f"POST /purchases COMPLETE - purchase_id={result.purchase.id}", "ROUTES")
    return result.purchase


@router.post("/with-partial-success", response_model=schemas.PurchaseWithOffers, status_code=201)
@log_response()
async def create_purchase_with_partial_success(
    request: Request,
    purchase_data: schemas.PurchaseCreate,
    current_user: User = Depends(get_current_user)
) -> schemas.PurchaseWithOffers:
    """
    Create a new purchase order with partial success support.
    Processes each offer individually and returns detailed results.
    Validates availability, checks expiration dates, reserves items, and calculates total cost.
    If an offer has insufficient quantity, it will be added with available quantity.
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    result = await purchases_manager.create_purchase_with_partial_success(
        request.state.session, current_user.id, purchase_data, base_url
    )
    return result.purchase


@router.get("", response_model=PaginatedResponse[schemas.Purchase])
async def get_my_purchases(
    request: Request,
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=20, ge=1, description="Number of items per page"),
    status: Optional[str] = Query(default=None, description="Filter by purchase status"),
    user_id: Optional[int] = Query(default=None, ge=1, description="Filter by user ID (defaults to current user)"),
    min_created_at: Optional[datetime] = Query(default=None, description="Minimum creation date"),
    max_created_at: Optional[datetime] = Query(default=None, description="Maximum creation date"),
    min_updated_at: Optional[datetime] = Query(default=None, description="Minimum update date"),
    max_updated_at: Optional[datetime] = Query(default=None, description="Maximum update date")
) -> PaginatedResponse[schemas.Purchase]:
    """
    Get paginated list of purchases with optional filters.
    If user_id is not specified, filters by current user's purchases.
    """
    # If user_id is not specified, use current user's ID
    filter_user_id = user_id if user_id is not None else current_user.id
    
    return await purchases_manager.get_purchases_paginated(
        request.state.session, page, page_size, status, filter_user_id,
        min_created_at, max_created_at, min_updated_at, max_updated_at
    )


@router.get("/current-pending", response_model=schemas.PurchaseWithOffers)
async def get_pending_purchase(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> schemas.PurchaseWithOffers:
    """
    Get current user's pending purchase.
    Returns 404 if no pending purchase exists.
    """
    return await purchases_manager.get_pending_purchase_by_user(
        request.state.session, current_user.id
    )


@router.get("/{purchase_id}", response_model=schemas.PurchaseWithOffers)
async def get_purchase(
    request: Request,
    purchase_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.PurchaseWithOffers:
    """
    Get purchase by ID
    """
    
    purchase = await purchases_manager.get_purchase_by_id(
        request.state.session, purchase_id
    )
    
    # Check if purchase belongs to current user
    if purchase.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this purchase"
        )
    
    return purchase


@router.patch("/{purchase_id}", response_model=schemas.Purchase)
async def update_purchase_status(
    request: Request,
    purchase_id: int,
    status_data: schemas.PurchaseUpdate,
    current_user: User = Depends(get_current_user)
) -> schemas.Purchase:
    """
    Update purchase status
    """
    
    # Check if purchase belongs to current user
    purchase = await purchases_manager.get_purchase_by_id(
        request.state.session, purchase_id
    )
    
    if purchase.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this purchase"
        )
    
    return await purchases_manager.update_purchase_status(
        request.state.session, purchase_id, status_data
    )


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    request: Request,
    purchase_id: int,
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete purchase and release reservations
    """
    
    
    # Check if purchase belongs to current user
    purchase = await purchases_manager.get_purchase_by_id(
        request.state.session, purchase_id
    )
    
    if purchase.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this purchase"
        )
    
    await purchases_manager.delete_purchase(request.state.session, purchase_id)


@router.post("/{purchase_id}/token", response_model=schemas.OrderTokenResponse)
async def generate_order_token(
    request: Request,
    purchase_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.OrderTokenResponse:
    """
    Generate JWT token for order information.
    Token can only be generated if the order is paid.
    """
    return await purchases_manager.generate_order_token(
        request.state.session, purchase_id, current_user.id
    )


@router.post("/verify-token", response_model=schemas.PurchaseInfoByTokenResponse)
async def verify_purchase_token(
    request: Request,
    token_data: schemas.OrderTokenRequest,
    current_user: User = Depends(get_current_user)
) -> schemas.PurchaseInfoByTokenResponse:
    """
    Verify purchase token and get purchase information (only seller's items).
    Requires seller authentication.
    """
    from app.sellers.service import SellersService
    sellers_service = SellersService()
    
    # Get seller by user
    seller = await sellers_service.get_seller_by_master_id(
        request.state.session, current_user.id
    )
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a seller"
        )
    
    return await purchases_manager.verify_purchase_token(
        request.state.session, token_data.token, seller.id
    )


@router.post("/{purchase_id}/fulfill", response_model=schemas.OrderFulfillmentResponse)
async def fulfill_order_items(
    request: Request,
    purchase_id: int,
    fulfillment_data: schemas.OrderFulfillmentRequest,
    current_user: User = Depends(get_current_user)
) -> schemas.OrderFulfillmentResponse:
    """
    Fulfill order items for a seller.
    Seller can only fulfill items from their own shop points.
    """
    from app.sellers.service import SellersService
    sellers_service = SellersService()
    
    # Get seller by user
    seller = await sellers_service.get_seller_by_master_id(
        request.state.session, current_user.id
    )
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a seller"
        )
    
    return await purchases_manager.fulfill_order_items(
        request.state.session, purchase_id, fulfillment_data, seller.id
    )

