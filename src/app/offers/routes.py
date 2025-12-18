from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Request, Query, Depends
from app.offers import schemas
from app.offers.manager import OffersManager
from utils.pagination import PaginatedResponse

router = APIRouter(prefix="/offers", tags=["offers"])

# Initialize manager
offers_manager = OffersManager()


@router.post("", response_model=schemas.Offer, status_code=201)
async def create_offer(
    request: Request,
    offer_data: schemas.OfferCreate
) -> schemas.Offer:
    """
    Create a new offer
    """
    return await offers_manager.create_offer(request.state.session, offer_data)


@router.get("", response_model=PaginatedResponse[schemas.Offer])
async def get_offers(
    request: Request,
    filters: schemas.OffersFilterParams = Depends()
) -> PaginatedResponse[schemas.Offer]:
    """
    Get paginated list of offers with optional filters.
    Location filters: min_latitude, max_latitude, min_longitude, max_longitude.
    Filters offers by shop points within the specified latitude and longitude ranges.
    """
    return await offers_manager.get_offers_paginated(
        request.state.session,
        filters
    )


@router.get("/with-products", response_model=List[schemas.OfferWithProduct])
async def get_offers_with_products(
    request: Request,
    filters: schemas.OffersFilterParams = Depends()
) -> List[schemas.OfferWithProduct]:
    """
    Get list of offers with product information and optional filters.
    Location filters: min_latitude, max_latitude, min_longitude, max_longitude.
    Filters offers by shop points within the specified latitude and longitude ranges.
    """
    return await offers_manager.get_offers_with_products(
        request.state.session,
        filters
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
    offer_data: schemas.OfferUpdate
) -> schemas.Offer:
    """
    Update offer
    """
    return await offers_manager.update_offer(request.state.session, offer_id, offer_data)


@router.delete("/{offer_id}", status_code=204)
async def delete_offer(
    request: Request,
    offer_id: int
) -> None:
    """
    Delete offer
    """
    await offers_manager.delete_offer(request.state.session, offer_id)
