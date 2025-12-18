from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, insert, func, and_
from sqlalchemy.orm import selectinload

from app.offers import schemas
from app.offers.models import Offer, PricingStrategy, PricingStrategyStep
from app.products.models import Product
from app.shop_points.models import ShopPoint


class OffersService:
    """Service for working with offers"""

    async def create_offer(
        self, session: AsyncSession, schema: schemas.OfferCreate
    ) -> Offer:
        """Create a new offer"""
        result = await session.execute(
            insert(Offer)
            .values(
                product_id=schema.product_id,
                shop_id=schema.shop_id,
                pricing_strategy_id=schema.pricing_strategy_id,
                expires_date=schema.expires_date,
                original_cost=schema.original_cost,
                current_cost=schema.current_cost,
                count=schema.count
            )
            .returning(Offer)
        )
        return result.scalar_one()

    async def get_offer_by_id(
        self, session: AsyncSession, offer_id: int
    ) -> Optional[Offer]:
        """Get offer by ID"""
        result = await session.execute(
            select(Offer)
            .where(Offer.id == offer_id)
        )
        return result.scalar_one_or_none()
    
    async def get_offer_by_product_and_shop(
        self, session: AsyncSession, product_id: int, shop_id: int
    ) -> Optional[Offer]:
        """Get offer by product_id and shop_id"""
        result = await session.execute(
            select(Offer).where(
                and_(Offer.product_id == product_id, Offer.shop_id == shop_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_offer_with_product(
        self, session: AsyncSession, offer_id: int
    ) -> Optional[Offer]:
        """Get offer with product information"""
        result = await session.execute(
            select(Offer)
            .where(Offer.id == offer_id)
            .options(
                selectinload(Offer.product).selectinload(Product.images),
                selectinload(Offer.product).selectinload(Product.attributes)
            )
        )
        return result.scalar_one_or_none()

    async def get_offers(
        self, session: AsyncSession
    ) -> List[Offer]:
        """Get list of all offers"""
        result = await session.execute(
            select(Offer)
            .order_by(Offer.id)
        )
        return result.scalars().all()

    def _build_offers_query_with_filters(
        self,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        min_expires_date: Optional[datetime] = None,
        max_expires_date: Optional[datetime] = None,
        min_original_cost: Optional[float] = None,
        max_original_cost: Optional[float] = None,
        min_current_cost: Optional[float] = None,
        max_current_cost: Optional[float] = None,
        min_count: Optional[int] = None,
        min_latitude: Optional[float] = None,
        max_latitude: Optional[float] = None,
        min_longitude: Optional[float] = None,
        max_longitude: Optional[float] = None,
        has_dynamic_pricing: Optional[bool] = None
    ) -> Tuple[select, List, bool, bool]:
        """
        Build offers query with filters.
        Returns: (base_query, conditions, needs_product_join, needs_shop_join)
        """
        base_query = select(Offer)
        
        needs_product_join = seller_id is not None
        needs_shop_join = (
            min_latitude is not None or max_latitude is not None or
            min_longitude is not None or max_longitude is not None
        )
        
        if needs_product_join:
            base_query = base_query.join(Product, Offer.product_id == Product.id)
        
        if needs_shop_join:
            base_query = base_query.join(ShopPoint, Offer.shop_id == ShopPoint.id)
        
        conditions = []
        if product_id is not None:
            conditions.append(Offer.product_id == product_id)
        if seller_id is not None:
            conditions.append(Product.seller_id == seller_id)
        if shop_id is not None:
            conditions.append(Offer.shop_id == shop_id)
        if min_expires_date is not None:
            conditions.append(Offer.expires_date >= min_expires_date)
        if max_expires_date is not None:
            conditions.append(Offer.expires_date <= max_expires_date)
        if min_original_cost is not None:
            conditions.append(Offer.original_cost >= min_original_cost)
        if max_original_cost is not None:
            conditions.append(Offer.original_cost <= max_original_cost)
        if min_current_cost is not None:
            conditions.append(Offer.current_cost >= min_current_cost)
        if max_current_cost is not None:
            conditions.append(Offer.current_cost <= max_current_cost)
        if min_count is not None:
            conditions.append(Offer.count >= min_count)
        
        if has_dynamic_pricing is not None:
            if has_dynamic_pricing:
                conditions.append(Offer.pricing_strategy_id.isnot(None))
            else:
                conditions.append(Offer.pricing_strategy_id.is_(None))
        
        if needs_shop_join:
            conditions.append(ShopPoint.latitude.isnot(None))
            conditions.append(ShopPoint.longitude.isnot(None))
            
            if min_latitude is not None:
                conditions.append(ShopPoint.latitude >= min_latitude)
            if max_latitude is not None:
                conditions.append(ShopPoint.latitude <= max_latitude)
            if min_longitude is not None:
                conditions.append(ShopPoint.longitude >= min_longitude)
            if max_longitude is not None:
                conditions.append(ShopPoint.longitude <= max_longitude)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        return base_query, conditions, needs_product_join, needs_shop_join

    async def get_offers_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
        shop_id: Optional[int] = None,
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
        max_longitude: Optional[float] = None
    ) -> tuple[List[Offer], int]:
        """Get paginated list of offers with optional filters including location-based filtering"""
        base_query, conditions, needs_product_join, needs_shop_join = self._build_offers_query_with_filters(
            product_id, seller_id, shop_id,
            min_expires_date, max_expires_date,
            min_original_cost, max_original_cost,
            min_current_cost, max_current_cost,
            min_count,
            min_latitude, max_latitude, min_longitude, max_longitude
        )
        
        # Get total count with filters
        count_query = select(func.count(Offer.id))
        if needs_product_join:
            count_query = count_query.join(Product, Offer.product_id == Product.id)
        if needs_shop_join:
            count_query = count_query.join(ShopPoint, Offer.shop_id == ShopPoint.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results with filters
        offset = (page - 1) * page_size
        paginated_query = base_query.order_by(Offer.id).limit(page_size).offset(offset)
        
        result = await session.execute(paginated_query)
        offers = result.scalars().all()
        
        return offers, total_count

    async def get_offers_with_products(
        self,
        session: AsyncSession,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
        shop_id: Optional[int] = None,
        min_expires_date: Optional[datetime] = None,
        max_expires_date: Optional[datetime] = None,
        min_original_cost: Optional[float] = None,
        max_original_cost: Optional[float] = None,
        min_current_cost: Optional[float] = None,
        max_current_cost: Optional[float] = None,
        min_count: Optional[int] = None,
        min_latitude: Optional[float] = None,
        max_latitude: Optional[float] = None,
        min_longitude: Optional[float] = None,
        max_longitude: Optional[float] = None,
        has_dynamic_pricing: Optional[bool] = None
    ) -> List[Offer]:
        """Get list of offers with product information and optional filters"""
        base_query, _, _, _ = self._build_offers_query_with_filters(
            product_id, seller_id, shop_id,
            min_expires_date, max_expires_date,
            min_original_cost, max_original_cost,
            min_current_cost, max_current_cost,
            min_count,
            min_latitude, max_latitude, min_longitude, max_longitude
        )
        
        result = await session.execute(
            base_query
            .options(
                selectinload(Offer.product).selectinload(Product.images),
                selectinload(Offer.product).selectinload(Product.attributes)
            )
            .order_by(Offer.id)
        )
        return result.scalars().all()

    async def update_offer(
        self, session: AsyncSession, offer_id: int, schema: schemas.OfferUpdate
    ) -> Offer:
        """Update offer"""
        # Get only fields that were explicitly set
        update_data = schema.model_dump(exclude_unset=True)
        
        # Remove None values for non-nullable fields, but keep None for nullable fields if explicitly set
        # For pricing_strategy_id, we want to allow None to disable the strategy
        filtered_data = {}
        for key, value in update_data.items():
            if key == 'pricing_strategy_id':
                # Allow None to be set explicitly to disable strategy
                filtered_data[key] = value
            elif value is not None:
                # For other fields, only include non-None values
                filtered_data[key] = value

        result = await session.execute(
            update(Offer)
            .where(Offer.id == offer_id)
            .values(**filtered_data)
            .returning(Offer)
        )
        return result.scalar_one()

    async def delete_offer(
        self, session: AsyncSession, offer_id: int
    ) -> None:
        """Delete offer"""
        await session.execute(
            delete(Offer).where(Offer.id == offer_id)
        )

    async def get_offers_by_ids(
        self, session: AsyncSession, offer_ids: List[int]
    ) -> List[Offer]:
        """Get offers by IDs"""
        if not offer_ids:
            return []
        
        result = await session.execute(
            select(Offer)
            .where(Offer.id.in_(offer_ids))
        )
        return list(result.scalars().all())

    async def get_offers_by_ids_for_update(
        self, session: AsyncSession, offer_ids: List[int]
    ) -> List[Offer]:
        """
        Get offers by IDs with SELECT FOR UPDATE lock.
        This prevents concurrent modifications during reservation.
        Offers are ordered by ID to prevent deadlocks.
        Loads pricing strategy with steps for dynamic pricing calculation.
        """
        if not offer_ids:
            return []
        
        # First, lock the offers
        result = await session.execute(
            select(Offer)
            .where(Offer.id.in_(offer_ids))
            .order_by(Offer.id)
            .with_for_update()
        )
        offers = list(result.scalars().all())
        
        # Then load pricing strategies with steps for offers that have them
        offers_with_strategy = [o for o in offers if o.pricing_strategy_id]
        if offers_with_strategy:
            strategy_ids = {o.pricing_strategy_id for o in offers_with_strategy}
            strategies_result = await session.execute(
                select(PricingStrategy)
                .where(PricingStrategy.id.in_(strategy_ids))
                .options(selectinload(PricingStrategy.steps))
            )
            strategies_dict = {s.id: s for s in strategies_result.scalars().all()}
            
            # Assign loaded strategies to offers
            for offer in offers_with_strategy:
                if offer.pricing_strategy_id in strategies_dict:
                    offer.pricing_strategy = strategies_dict[offer.pricing_strategy_id]
        
        return offers

    async def update_offer_reserved_count(
        self, session: AsyncSession, offer_id: int, reserved_count_delta: int
    ) -> Offer:
        """
        Update offer reserved_count by delta.
        
        Important: This method should be called only after the offer has been locked
        with SELECT FOR UPDATE to prevent race conditions.
        
        The database constraint will prevent reserved_count from exceeding count
        or going below 0. If constraint is violated, an IntegrityError will be raised.
        """
        # Handle NULL values by using COALESCE
        result = await session.execute(
            update(Offer)
            .where(Offer.id == offer_id)
            .values(
                reserved_count=func.coalesce(Offer.reserved_count, 0) + reserved_count_delta
            )
            .returning(Offer)
        )
        return result.scalar_one()

    async def update_offer_count(
        self, session: AsyncSession, offer_id: int, count_delta: int
    ) -> Offer:
        """
        Update offer count by delta.
        
        Important: This method should be called only after the offer has been locked
        with SELECT FOR UPDATE to prevent race conditions.
        
        Args:
            session: Database session
            offer_id: Offer ID
            count_delta: Delta to add to count (can be negative to decrease)
        
        Returns:
            Updated offer
        """
        # Handle NULL values by using COALESCE
        result = await session.execute(
            update(Offer)
            .where(Offer.id == offer_id)
            .values(
                count=func.coalesce(Offer.count, 0) + count_delta
            )
            .returning(Offer)
        )
        return result.scalar_one()

    async def get_pricing_strategies(
        self, session: AsyncSession
    ) -> List[PricingStrategy]:
        """Get list of all pricing strategies with steps"""
        result = await session.execute(
            select(PricingStrategy)
            .options(selectinload(PricingStrategy.steps))
            .order_by(PricingStrategy.id)
        )
        return result.scalars().all()

    async def get_pricing_strategy_by_id(
        self, session: AsyncSession, strategy_id: int
    ) -> Optional[PricingStrategy]:
        """Get pricing strategy by ID with steps"""
        result = await session.execute(
            select(PricingStrategy)
            .where(PricingStrategy.id == strategy_id)
            .options(selectinload(PricingStrategy.steps))
        )
        return result.scalar_one_or_none()
