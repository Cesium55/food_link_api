from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.offers import schemas
from app.offers.service import OffersService
from app.offers.models import Offer
from app.products import schemas as products_schemas
from app.products.service import ProductsService
from app.shop_points.service import ShopPointsService
from app.sellers.models import Seller
from utils.errors_handler import handle_alchemy_error
from utils.pagination import PaginatedResponse
from utils.seller_dependencies import verify_seller_owns_resource


class OffersManager:
    """Manager for offers business logic and validation"""
    
    def calculate_dynamic_price(
        self, offer: Offer, at_time: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """
        Calculate dynamic price for an offer based on pricing strategy.
        
        Args:
            offer: Offer instance with loaded pricing_strategy and steps
            at_time: Time to calculate price at (defaults to current time)
            
        Returns:
            Calculated price (can be Decimal('0.00') for free items) or None if cannot calculate
        """
        if at_time is None:
            at_time = datetime.now(timezone.utc)
        
        # If no strategy ID, use current_cost (can be None)
        if not offer.pricing_strategy_id:
            return offer.current_cost
        
        # Try to access pricing_strategy safely
        try:
            strategy = offer.pricing_strategy
        except AttributeError:
            # Strategy not loaded - fallback to current_cost
            return offer.current_cost
        
        # If strategy is None or not loaded, use current_cost
        if not strategy:
            return offer.current_cost
        
        # If no expires_date, cannot calculate dynamic price - fallback to current_cost
        if not offer.expires_date:
            return offer.current_cost
        
        # If expired, return None
        if offer.expires_date < at_time:
            return None
        
        # Calculate time remaining in seconds
        time_remaining = (offer.expires_date - at_time).total_seconds()
        time_remaining_seconds = int(time_remaining)
        
        # If no original_cost, cannot calculate dynamic price - fallback to current_cost
        if not offer.original_cost:
            return offer.current_cost
        
        # Try to access steps safely
        try:
            steps = strategy.steps
        except AttributeError:
            # Steps not loaded - use original_cost without discount
            return offer.original_cost
        
        # If no steps in strategy, use original_cost without discount
        if not steps:
            return offer.original_cost
        
        # Steps are ordered by time_remaining_seconds (ascending)
        # Find the step with MAXIMUM time_remaining_seconds that does NOT exceed current time remaining
        # This means we need to find the highest threshold we've passed
        discount_percent = Decimal('0.00')
        for step in steps:
            # If we have MORE time remaining than this step requires, we can use this step
            # Keep checking to find the step with the highest threshold we meet
            if time_remaining_seconds >= step.time_remaining_seconds:
                discount_percent = step.discount_percent
                # Don't break - continue to find the step with highest threshold we meet
        
        # Calculate price with discount
        price = offer.original_cost * (Decimal('1') - discount_percent / Decimal('100'))
        return max(Decimal('0.00'), price)
    """Manager for offers business logic and validation"""

    def __init__(self):
        self.service = OffersService()
        self.products_service = ProductsService()
        self.shop_points_service = ShopPointsService()

    @handle_alchemy_error
    async def create_offer(
        self, 
        session: AsyncSession, 
        offer_data: schemas.OfferCreate,
        current_seller: Seller = None
    ) -> schemas.Offer:
        """Create a new offer"""
        # Validate product exists
        product = await self.products_service.get_product_by_id(session, offer_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {offer_data.product_id} not found"
            )

        # Validate shop point exists
        shop_point = await self.shop_points_service.get_shop_point_by_id(session, offer_data.shop_id)
        if not shop_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop point with id {offer_data.shop_id} not found"
            )

        # Check ownership - seller must own both product and shop point
        if current_seller:
            await verify_seller_owns_resource(product.seller_id, current_seller)
            await verify_seller_owns_resource(shop_point.seller_id, current_seller)

        # Create offer
        offer = await self.service.create_offer(session, offer_data)
        await session.commit()
        
        return schemas.Offer.model_validate(offer)

    async def get_offers(
        self, session: AsyncSession
    ) -> List[schemas.Offer]:
        """Get list of offers"""
        offers = await self.service.get_offers(session)
        return [schemas.Offer.model_validate(offer) for offer in offers]

    async def get_offers_paginated(
        self,
        session: AsyncSession,
        page: int,
        page_size: int,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None,
        min_expires_date: Optional[datetime] = None,
        max_expires_date: Optional[datetime] = None,
        min_original_cost: Optional[Decimal] = None,
        max_original_cost: Optional[Decimal] = None,
        min_current_cost: Optional[Decimal] = None,
        max_current_cost: Optional[Decimal] = None,
        min_count: Optional[int] = None,
        min_latitude: Optional[float] = None,
        max_latitude: Optional[float] = None,
        min_longitude: Optional[float] = None,
        max_longitude: Optional[float] = None,
        has_dynamic_pricing: Optional[bool] = None
    ) -> PaginatedResponse[schemas.Offer]:
        """Get paginated list of offers with optional filters"""
        offers, total_count = await self.service.get_offers_paginated(
            session, page, page_size,
            product_id, seller_id, shop_id,
            category_ids,
            min_expires_date, max_expires_date,
            min_original_cost, max_original_cost,
            min_current_cost, max_current_cost,
            min_count,
            min_latitude, max_latitude,
            min_longitude, max_longitude,
            has_dynamic_pricing
        )
        offer_schemas = [
            schemas.Offer.model_validate(offer) for offer in offers
        ]
        return PaginatedResponse.create(
            items=offer_schemas,
            page=page,
            page_size=page_size,
            total_items=total_count
        )

    async def get_offers_with_products(
        self,
        session: AsyncSession,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None,
        min_expires_date: Optional[datetime] = None,
        max_expires_date: Optional[datetime] = None,
        min_original_cost: Optional[Decimal] = None,
        max_original_cost: Optional[Decimal] = None,
        min_current_cost: Optional[Decimal] = None,
        max_current_cost: Optional[Decimal] = None,
        min_count: Optional[int] = None,
        min_latitude: Optional[float] = None,
        max_latitude: Optional[float] = None,
        min_longitude: Optional[float] = None,
        max_longitude: Optional[float] = None,
        has_dynamic_pricing: Optional[bool] = None
    ) -> List[schemas.OfferWithProduct]:
        """Get list of offers with product information and optional filters"""
        offers = await self.service.get_offers_with_products(
            session,
            product_id, seller_id, shop_id,
            category_ids,
            min_expires_date, max_expires_date,
            min_original_cost, max_original_cost,
            min_current_cost, max_current_cost,
            min_count,
            min_latitude, max_latitude,
            min_longitude, max_longitude,
            has_dynamic_pricing
        )
        result = []
        for offer in offers:
            offer_schema = schemas.Offer.model_validate(offer)
            product_schema = products_schemas.Product.model_validate(offer.product)
            # Add category IDs from loaded categories
            product_schema.category_ids = [cat.id for cat in offer.product.categories]
            result.append(schemas.OfferWithProduct(
                **offer_schema.model_dump(),
                product=product_schema
            ))
        return result

    async def get_offer_by_id(
        self, session: AsyncSession, offer_id: int
    ) -> schemas.Offer:
        """Get offer by ID"""
        offer = await self.service.get_offer_by_id(session, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )
        return schemas.Offer.model_validate(offer)

    async def get_offer_with_product(
        self, session: AsyncSession, offer_id: int
    ) -> schemas.OfferWithProduct:
        """Get offer with product information"""
        offer = await self.service.get_offer_with_product(session, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )
        
        offer_schema = schemas.Offer.model_validate(offer)
        product_schema = products_schemas.Product.model_validate(offer.product)
        # Add category IDs from loaded categories
        product_schema.category_ids = [cat.id for cat in offer.product.categories]
        
        return schemas.OfferWithProduct(
            **offer_schema.model_dump(),
            product=product_schema
        )

    @handle_alchemy_error
    async def update_offer(
        self, 
        session: AsyncSession,
        offer_id: int, 
        offer_data: schemas.OfferUpdate,
        current_seller: Seller = None
    ) -> schemas.Offer:
        """Update offer"""
        # Check if offer exists
        existing_offer = await self.service.get_offer_by_id(session, offer_id)
        if not existing_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )

        # Check ownership - verify seller owns the product associated with offer
        if current_seller:
            product = await self.products_service.get_product_by_id(session, existing_offer.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {existing_offer.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)

        # Update offer
        updated_offer = await self.service.update_offer(session, offer_id, offer_data)
        await session.commit()
        
        return schemas.Offer.model_validate(updated_offer)

    @handle_alchemy_error
    async def delete_offer(
        self, session: AsyncSession, offer_id: int, current_seller: Seller = None
    ) -> None:
        """Delete offer"""
        # Check if offer exists
        existing_offer = await self.service.get_offer_by_id(session, offer_id)
        if not existing_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )

        # Check ownership - verify seller owns the product associated with offer
        if current_seller:
            product = await self.products_service.get_product_by_id(session, existing_offer.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {existing_offer.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)

        await self.service.delete_offer(session, offer_id)
        await session.commit()

    async def get_pricing_strategies(
        self, session: AsyncSession
    ) -> List[schemas.PricingStrategy]:
        """Get list of all pricing strategies"""
        strategies = await self.service.get_pricing_strategies(session)
        return [schemas.PricingStrategy.model_validate(strategy) for strategy in strategies]

    async def get_pricing_strategy_by_id(
        self, session: AsyncSession, strategy_id: int
    ) -> schemas.PricingStrategy:
        """Get pricing strategy by ID"""
        strategy = await self.service.get_pricing_strategy_by_id(session, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pricing strategy with id {strategy_id} not found"
            )
        return schemas.PricingStrategy.model_validate(strategy)

