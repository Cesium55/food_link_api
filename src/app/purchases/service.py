from typing import Optional, List, Dict
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, func
from sqlalchemy.orm.exc import NoResultFound

from app.purchases.models import Purchase, PurchaseOffer, PurchaseOfferResult


class PurchasesService:
    """Service for working with purchases"""

    async def create_purchase(
        self, session: AsyncSession, user_id: int, total_cost: Optional[Decimal] = None
    ) -> Purchase:
        """Create a new purchase"""
        result = await session.execute(
            insert(Purchase)
            .values(
                user_id=user_id,
                status="pending",
                total_cost=total_cost
            )
            .returning(Purchase)
        )
        return result.scalar_one()

    async def create_purchase_offers(
        self, session: AsyncSession, purchase_id: int, offers_data: List[dict]
    ) -> List[PurchaseOffer]:
        """Create purchase offers"""
        if not offers_data:
            return []
        
        # Prepare values for bulk insert
        values = [
            {
                "purchase_id": purchase_id,
                "offer_id": offer_data["offer_id"],
                "quantity": offer_data["quantity"],
                "cost_at_purchase": offer_data.get("cost_at_purchase"),
            }
            for offer_data in offers_data
        ]
        
        result = await session.execute(
            insert(PurchaseOffer).values(values).returning(PurchaseOffer)
        )
        return list(result.scalars().all())

    async def get_purchase_by_id(
        self, session: AsyncSession, purchase_id: int
    ) -> Purchase:
        """Get purchase by ID"""
        result = await session.execute(
            select(Purchase)
            .where(Purchase.id == purchase_id)
        )
        return result.scalar_one()

    async def get_purchase_by_id_for_update(
        self, session: AsyncSession, purchase_id: int
    ) -> Purchase:
        """Get purchase by ID with FOR UPDATE lock"""
        result = await session.execute(
            select(Purchase)
            .where(Purchase.id == purchase_id)
            .with_for_update()
        )
        return result.scalar_one()

    async def get_purchase_offers_by_purchase_id(
        self, session: AsyncSession, purchase_id: int
    ) -> List[PurchaseOffer]:
        """Get purchase offers by purchase ID"""
        result = await session.execute(
            select(PurchaseOffer)
            .where(PurchaseOffer.purchase_id == purchase_id)
        )
        return list(result.scalars().all())

    async def get_purchases_by_user(
        self, session: AsyncSession, user_id: int
    ) -> List[Purchase]:
        """Get purchases by user ID"""
        result = await session.execute(
            select(Purchase)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_purchases_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> tuple[List[Purchase], int]:
        """Get paginated list of purchases with optional filters"""
        # Build base query with filters
        base_query = select(Purchase)
        
        # Apply filters
        conditions = []
        if status is not None:
            conditions.append(Purchase.status == status)
        if user_id is not None:
            conditions.append(Purchase.user_id == user_id)
        if min_created_at is not None:
            conditions.append(Purchase.created_at >= min_created_at)
        if max_created_at is not None:
            conditions.append(Purchase.created_at <= max_created_at)
        if min_updated_at is not None:
            conditions.append(Purchase.updated_at >= min_updated_at)
        if max_updated_at is not None:
            conditions.append(Purchase.updated_at <= max_updated_at)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Get total count with filters
        count_query = select(func.count(Purchase.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results with filters
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query
            .order_by(Purchase.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        purchases = result.scalars().all()
        
        return list(purchases), total_count

    async def get_seller_purchases_paginated(
        self,
        session: AsyncSession,
        seller_offer_ids: List[int],
        page: int,
        page_size: int,
        status: Optional[str] = None,
        fulfillment_status: Optional[str] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> tuple[
        List[Purchase],
        int,
        Dict[int, List[PurchaseOffer]],
        Dict[int, List[PurchaseOfferResult]],
    ]:
        """Get paginated purchases containing provided seller offer IDs only."""
        if not seller_offer_ids:
            return [], 0, {}, {}

        conditions = [PurchaseOffer.offer_id.in_(seller_offer_ids)]

        if status is not None:
            conditions.append(Purchase.status == status)
        if min_created_at is not None:
            conditions.append(Purchase.created_at >= min_created_at)
        if max_created_at is not None:
            conditions.append(Purchase.created_at <= max_created_at)
        if min_updated_at is not None:
            conditions.append(Purchase.updated_at >= min_updated_at)
        if max_updated_at is not None:
            conditions.append(Purchase.updated_at <= max_updated_at)

        if fulfillment_status == "unprocessed":
            conditions.append(PurchaseOffer.fulfillment_status.is_(None))
        elif fulfillment_status is not None:
            conditions.append(PurchaseOffer.fulfillment_status == fulfillment_status)

        count_query = (
            select(func.count(func.distinct(Purchase.id)))
            .select_from(Purchase)
            .join(PurchaseOffer, PurchaseOffer.purchase_id == Purchase.id)
            .where(and_(*conditions))
        )
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        offset = (page - 1) * page_size
        purchase_ids_query = (
            select(Purchase.id, Purchase.created_at)
            .join(PurchaseOffer, PurchaseOffer.purchase_id == Purchase.id)
            .where(and_(*conditions))
            .distinct()
            .order_by(Purchase.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        purchase_ids_result = await session.execute(purchase_ids_query)
        purchase_ids = [row[0] for row in purchase_ids_result.all()]

        if not purchase_ids:
            return [], total_count, {}, {}

        purchases_result = await session.execute(
            select(Purchase).where(Purchase.id.in_(purchase_ids))
        )
        purchases = list(purchases_result.scalars().all())
        purchases_by_id = {purchase.id: purchase for purchase in purchases}
        ordered_purchases = [purchases_by_id[purchase_id] for purchase_id in purchase_ids if purchase_id in purchases_by_id]

        purchase_offers_result = await session.execute(
            select(PurchaseOffer)
            .where(
                and_(
                    PurchaseOffer.purchase_id.in_(purchase_ids),
                    PurchaseOffer.offer_id.in_(seller_offer_ids),
                )
            )
        )
        seller_purchase_offers = list(purchase_offers_result.scalars().all())

        purchase_offers_map: Dict[int, List[PurchaseOffer]] = {}
        for purchase_offer in seller_purchase_offers:
            purchase_offers_map.setdefault(purchase_offer.purchase_id, []).append(purchase_offer)

        seller_offer_ids = list({purchase_offer.offer_id for purchase_offer in seller_purchase_offers})
        offer_results_map: Dict[int, List[PurchaseOfferResult]] = {}
        if seller_offer_ids:
            offer_results_result = await session.execute(
                select(PurchaseOfferResult).where(
                    and_(
                        PurchaseOfferResult.purchase_id.in_(purchase_ids),
                        PurchaseOfferResult.offer_id.in_(seller_offer_ids),
                    )
                )
            )
            seller_offer_results = list(offer_results_result.scalars().all())
            for offer_result in seller_offer_results:
                offer_results_map.setdefault(offer_result.purchase_id, []).append(offer_result)

        return ordered_purchases, total_count, purchase_offers_map, offer_results_map
    
    async def get_purchases(
        self, session: AsyncSession,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> tuple[List[Purchase], int]:
        """Get paginated list of purchases with optional filters"""
        # Build base query with filters
        base_query = select(Purchase)
        
        # Apply filters
        conditions = []
        if status is not None:
            conditions.append(Purchase.status == status)
        if user_id is not None:
            conditions.append(Purchase.user_id == user_id)
        if min_created_at is not None:
            conditions.append(Purchase.created_at >= min_created_at)
        if max_created_at is not None:
            conditions.append(Purchase.created_at <= max_created_at)
        if min_updated_at is not None:
            conditions.append(Purchase.updated_at >= min_updated_at)
        if max_updated_at is not None:
            conditions.append(Purchase.updated_at <= max_updated_at)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        result = await session.execute(
            base_query
            .order_by(Purchase.created_at.desc())
        )
        purchases = result.scalars().all()
        
        return list(purchases)

    async def get_pending_purchase_by_user(
        self, session: AsyncSession, user_id: int, for_update: bool = False
    ) -> Purchase:
        """
        Get pending purchase by user ID.
        
        Args:
            session: Database session
            user_id: User ID
            for_update: If True, locks the row with SELECT FOR UPDATE to prevent race conditions
        """
        query = select(Purchase).where(
            Purchase.user_id == user_id,
            Purchase.status == "pending"
        )
        if for_update:
            query = query.with_for_update()
        
        result = await session.execute(query)
        return result.scalar_one()

    async def has_pending_purchase_by_user(
        self, session: AsyncSession, user_id: int, for_update: bool = False
    ) -> bool:
        """
        Check if user has a pending purchase.
        Uses strict select with optional row lock and handles "not found" explicitly.
        """
        query = select(Purchase.id).where(
            Purchase.user_id == user_id,
            Purchase.status == "pending"
        )
        if for_update:
            query = query.with_for_update()
        query = query.limit(1)

        result = await session.execute(query)
        try:
            result.scalar_one()
            return True
        except NoResultFound:
            return False


    async def update_purchase_status(
        self, session: AsyncSession, purchase_id: int, status: str
    ) -> Purchase:
        """Update purchase status"""
        result = await session.execute(
            update(Purchase)
            .where(Purchase.id == purchase_id)
            .values(status=status)
            .returning(Purchase)
        )
        return result.scalar_one()

    async def delete_purchase(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Delete purchase"""
        await session.execute(
            delete(Purchase).where(Purchase.id == purchase_id)
        )

    async def create_purchase_offer_results(
        self, session: AsyncSession, purchase_id: int, results_data: List[dict]
    ) -> List[PurchaseOfferResult]:
        """Create purchase offer results"""
        if not results_data:
            return []
        
        # Prepare values for bulk insert
        values = [
            {
                "purchase_id": purchase_id,
                "offer_id": result_data["offer_id"],
                "status": result_data["status"],
                "requested_quantity": result_data["requested_quantity"],
                "processed_quantity": result_data.get("processed_quantity"),
                "available_quantity": result_data.get("available_quantity"),
                "message": result_data.get("message"),
            }
            for result_data in results_data
        ]
        
        result = await session.execute(
            insert(PurchaseOfferResult).values(values).returning(PurchaseOfferResult)
        )
        return list(result.scalars().all())

    async def get_purchase_offer_results_by_purchase_id(
        self, session: AsyncSession, purchase_id: int
    ) -> List[PurchaseOfferResult]:
        """Get purchase offer results by purchase ID"""
        result = await session.execute(
            select(PurchaseOfferResult)
            .where(PurchaseOfferResult.purchase_id == purchase_id)
            .order_by(PurchaseOfferResult.id)
        )
        return list(result.scalars().all())

    async def get_purchase_offer_results_by_purchase_and_offer_ids_for_update(
        self,
        session: AsyncSession,
        purchase_id: int,
        offer_ids: List[int],
    ) -> List[PurchaseOfferResult]:
        """Get purchase offer results by purchase and offer IDs with FOR UPDATE lock"""
        if not offer_ids:
            return []

        result = await session.execute(
            select(PurchaseOfferResult)
            .where(
                and_(
                    PurchaseOfferResult.purchase_id == purchase_id,
                    PurchaseOfferResult.offer_id.in_(offer_ids),
                )
            )
            .with_for_update()
        )
        return list(result.scalars().all())

    async def get_purchase_offer_results_by_purchase_ids_and_offer_ids(
        self,
        session: AsyncSession,
        purchase_ids: List[int],
        offer_ids: List[int],
    ) -> List[PurchaseOfferResult]:
        """Get purchase offer results by purchase IDs and offer IDs"""
        if not purchase_ids or not offer_ids:
            return []

        result = await session.execute(
            select(PurchaseOfferResult).where(
                and_(
                    PurchaseOfferResult.purchase_id.in_(purchase_ids),
                    PurchaseOfferResult.offer_id.in_(offer_ids),
                )
            )
        )
        return list(result.scalars().all())

    async def update_purchase_offer_fulfillment(
        self,
        session: AsyncSession,
        purchase_id: int,
        offer_id: int,
        fulfillment_status: str,
        fulfilled_quantity: int,
        fulfilled_by_seller_id: int,
        unfulfilled_reason: Optional[str] = None
    ) -> PurchaseOffer:
        """Update fulfillment fields in PurchaseOffer"""
        fulfilled_at = None
        if fulfillment_status == "fulfilled":
            fulfilled_at = datetime.now(timezone.utc)

        result = await session.execute(
            update(PurchaseOffer)
            .where(
                and_(
                    PurchaseOffer.purchase_id == purchase_id,
                    PurchaseOffer.offer_id == offer_id
                )
            )
            .values(
                fulfillment_status=fulfillment_status,
                fulfilled_quantity=fulfilled_quantity,
                fulfilled_at=fulfilled_at,
                fulfilled_by_seller_id=fulfilled_by_seller_id,
                unfulfilled_reason=unfulfilled_reason
            )
            .returning(PurchaseOffer)
        )
        return result.scalar_one()

    async def get_purchase_offers_by_purchase_with_fulfillment(
        self, session: AsyncSession, purchase_id: int
    ) -> List[PurchaseOffer]:
        """Get purchase offers by purchase ID with fulfillment information"""
        result = await session.execute(
            select(PurchaseOffer)
            .where(PurchaseOffer.purchase_id == purchase_id)
        )
        return list(result.scalars().all())

    async def get_purchase_offers_by_purchase_and_offer_ids(
        self, session: AsyncSession, purchase_id: int, offer_ids: List[int]
    ) -> List[PurchaseOffer]:
        if not offer_ids:
            return []

        result = await session.execute(
            select(PurchaseOffer)
            .where(
                and_(
                    PurchaseOffer.purchase_id == purchase_id,
                    PurchaseOffer.offer_id.in_(offer_ids)
                )
            )
        )
        return list(result.scalars().all())

    async def get_purchase_offer_by_purchase_and_offer(
        self, session: AsyncSession, purchase_id: int, offer_id: int
    ) -> PurchaseOffer:
        """Get purchase offer by composite key"""
        result = await session.execute(
            select(PurchaseOffer).where(
                and_(
                    PurchaseOffer.purchase_id == purchase_id,
                    PurchaseOffer.offer_id == offer_id,
                )
            )
        )
        return result.scalar_one()

    async def check_all_offers_fulfilled(
        self, session: AsyncSession, purchase_id: int
    ) -> bool:
        """
        Check if purchase is fully resolved and can be completed.

        A purchase is considered resolved when every purchase offer:
        1. has been processed by seller (fulfilled/not_fulfilled),
        2. has a corresponding PurchaseOfferResult,
        3. issued quantity + refunded quantity covers requested quantity.
        """
        purchase_offers_result = await session.execute(
            select(PurchaseOffer)
            .where(PurchaseOffer.purchase_id == purchase_id)
        )
        purchase_offers = list(purchase_offers_result.scalars().all())

        if not purchase_offers:
            return False

        offer_results_result = await session.execute(
            select(PurchaseOfferResult).where(
                PurchaseOfferResult.purchase_id == purchase_id
            )
        )
        offer_results = list(offer_results_result.scalars().all())
        offer_results_by_offer_id = {offer_result.offer_id: offer_result for offer_result in offer_results}

        for po in purchase_offers:
            offer_result = offer_results_by_offer_id.get(po.offer_id)
            if offer_result is None:
                return False

            refunded_quantity = offer_result.refunded_quantity or 0

            # Fully refunded lines are considered resolved even without fulfillment processing.
            if refunded_quantity >= po.quantity:
                continue

            if po.fulfillment_status not in {"fulfilled", "not_fulfilled"}:
                return False

            fulfilled_quantity = po.fulfilled_quantity or 0
            if po.fulfillment_status == "not_fulfilled" and fulfilled_quantity != 0:
                return False
            if fulfilled_quantity + refunded_quantity < po.quantity:
                return False

        return True
