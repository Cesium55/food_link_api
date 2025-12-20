from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Query, Depends
from app.offers import schemas
from app.offers.manager import OffersManager
from utils.seller_dependencies import get_current_seller
from app.sellers.models import Seller
from utils.pagination import PaginatedResponse

router = APIRouter(prefix="/offers", tags=["offers"])

# Initialize manager
offers_manager = OffersManager()


@router.post("", response_model=schemas.Offer, status_code=201)
async def create_offer(
    request: Request,
    offer_data: schemas.OfferCreate,
    current_seller: Seller = Depends(get_current_seller)
) -> schemas.Offer:
    """
    Create a new offer (only for own products and shop points)
    """
    return await offers_manager.create_offer(request.state.session, offer_data, current_seller)


@router.get("", response_model=PaginatedResponse[schemas.Offer])
async def get_offers(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=20, ge=1, description="Number of items per page"),
    product_id: Optional[int] = Query(default=None, ge=1, description="Filter by product ID"),
    seller_id: Optional[int] = Query(default=None, ge=1, description="Filter by seller ID"),
    shop_id: Optional[int] = Query(default=None, ge=1, description="Filter by shop point ID"),
    category_ids: Optional[List[int]] = Query(default=None, description="Filter by category IDs (offers with products having at least one of these categories)"),
    min_expires_date: Optional[datetime] = Query(default=None, description="Minimum expiration date"),
    max_expires_date: Optional[datetime] = Query(default=None, description="Maximum expiration date"),
    min_original_cost: Optional[Decimal] = Query(default=None, ge=0, description="Minimum original cost"),
    max_original_cost: Optional[Decimal] = Query(default=None, ge=0, description="Maximum original cost"),
    min_current_cost: Optional[Decimal] = Query(default=None, ge=0, description="Minimum current cost"),
    max_current_cost: Optional[Decimal] = Query(default=None, ge=0, description="Maximum current cost"),
    min_count: Optional[int] = Query(default=None, ge=0, description="Minimum product count"),
    min_latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Minimum latitude for location-based filtering"),
    max_latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Maximum latitude for location-based filtering"),
    min_longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Minimum longitude for location-based filtering"),
    max_longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Maximum longitude for location-based filtering"),
    has_dynamic_pricing: Optional[bool] = Query(default=None, description="Filter by dynamic pricing: true - only with pricing strategy, false - only without, null - all")
) -> PaginatedResponse[schemas.Offer]:
    """
    Get paginated list of offers with optional filters.
    Location filters: min_latitude, max_latitude, min_longitude, max_longitude.
    Filters offers by shop points within the specified latitude and longitude ranges.
    """
    return await offers_manager.get_offers_paginated(
        request.state.session,
        page, page_size,
        product_id, seller_id, shop_id, category_ids,
        min_expires_date, max_expires_date,
        min_original_cost, max_original_cost,
        min_current_cost, max_current_cost,
        min_count,
        min_latitude, max_latitude,
        min_longitude, max_longitude,
        has_dynamic_pricing
    )


@router.get("/with-products", response_model=List[schemas.OfferWithProduct])
async def get_offers_with_products(
    request: Request,
    product_id: Optional[int] = Query(default=None, ge=1, description="Filter by product ID"),
    seller_id: Optional[int] = Query(default=None, ge=1, description="Filter by seller ID"),
    shop_id: Optional[int] = Query(default=None, ge=1, description="Filter by shop point ID"),
    category_ids: Optional[List[int]] = Query(default=None, description="Filter by category IDs (offers with products having at least one of these categories)"),
    min_expires_date: Optional[datetime] = Query(default=None, description="Minimum expiration date"),
    max_expires_date: Optional[datetime] = Query(default=None, description="Maximum expiration date"),
    min_original_cost: Optional[Decimal] = Query(default=None, ge=0, description="Minimum original cost"),
    max_original_cost: Optional[Decimal] = Query(default=None, ge=0, description="Maximum original cost"),
    min_current_cost: Optional[Decimal] = Query(default=None, ge=0, description="Minimum current cost"),
    max_current_cost: Optional[Decimal] = Query(default=None, ge=0, description="Maximum current cost"),
    min_count: Optional[int] = Query(default=None, ge=0, description="Minimum product count"),
    min_latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Minimum latitude for location-based filtering"),
    max_latitude: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Maximum latitude for location-based filtering"),
    min_longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Minimum longitude for location-based filtering"),
    max_longitude: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Maximum longitude for location-based filtering"),
    has_dynamic_pricing: Optional[bool] = Query(default=None, description="Filter by dynamic pricing: true - only with pricing strategy, false - only without, null - all")
) -> List[schemas.OfferWithProduct]:
    """
    Get list of offers with product information and optional filters.
    Location filters: min_latitude, max_latitude, min_longitude, max_longitude.
    Filters offers by shop points within the specified latitude and longitude ranges.
    """
    return await offers_manager.get_offers_with_products(
        request.state.session,
        product_id, seller_id, shop_id, category_ids,
        min_expires_date, max_expires_date,
        min_original_cost, max_original_cost,
        min_current_cost, max_current_cost,
        min_count,
        min_latitude, max_latitude,
        min_longitude, max_longitude,
        has_dynamic_pricing
    )


@router.get("/pricing-strategies", response_model=List[schemas.PricingStrategy])
async def get_pricing_strategies(
    request: Request
) -> List[schemas.PricingStrategy]:
    """
    Get list of all pricing strategies with their steps
    """
    return await offers_manager.get_pricing_strategies(request.state.session)


@router.get("/pricing-strategies/{strategy_id}", response_model=schemas.PricingStrategy)
async def get_pricing_strategy(
    request: Request,
    strategy_id: int
) -> schemas.PricingStrategy:
    """
    Get pricing strategy by ID with steps
    """
    return await offers_manager.get_pricing_strategy_by_id(request.state.session, strategy_id)


@router.get("/{offer_id}", response_model=schemas.Offer)
async def get_offer(
    request: Request,
    offer_id: int
) -> schemas.Offer:
    """
    Get offer by ID
    """
    return await offers_manager.get_offer_by_id(request.state.session, offer_id)


@router.get("/{offer_id}/with-product", response_model=schemas.OfferWithProduct)
async def get_offer_with_product(
    request: Request,
    offer_id: int
) -> schemas.OfferWithProduct:
    """
    Get offer with product information
    """
    return await offers_manager.get_offer_with_product(request.state.session, offer_id)


@router.put("/{offer_id}", response_model=schemas.Offer)
async def update_offer(
    request: Request,
    offer_id: int,
    offer_data: schemas.OfferUpdate,
    current_seller: Seller = Depends(get_current_seller)
) -> schemas.Offer:
    """
    Update offer (only own offers)
    """
    return await offers_manager.update_offer(request.state.session, offer_id, offer_data, current_seller)


@router.delete("/{offer_id}", status_code=204)
async def delete_offer(
    request: Request,
    offer_id: int,
    current_seller: Seller = Depends(get_current_seller)
) -> None:
    """
    Delete offer (only own offers)
    """
    await offers_manager.delete_offer(request.state.session, offer_id, current_seller)
