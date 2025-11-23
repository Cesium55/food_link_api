from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_
from sqlalchemy.orm import selectinload

from app.purchases.models import Purchase, PurchaseOffer, PurchaseOfferResult
from app.offers.models import Offer


class PurchasesService:
    """Service for working with purchases"""

    async def create_purchase(
        self, session: AsyncSession, user_id: int, total_cost: Optional[float] = None
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
    ) -> Optional[Purchase]:
        """Get purchase by ID"""
        result = await session.execute(
            select(Purchase)
            .where(Purchase.id == purchase_id)
        )
        return result.scalar_one_or_none()

    async def get_purchase_by_id_for_update(
        self, session: AsyncSession, purchase_id: int
    ) -> Optional[Purchase]:
        """Get purchase by ID with FOR UPDATE lock"""
        result = await session.execute(
            select(Purchase)
            .where(Purchase.id == purchase_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

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

    async def get_pending_purchase_by_user(
        self, session: AsyncSession, user_id: int, for_update: bool = False
    ) -> Optional[Purchase]:
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
        return result.scalar_one_or_none()


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
            .options(selectinload(PurchaseOffer.offer))
        )
        return list(result.scalars().all())

    async def get_purchase_offers_by_seller_and_purchase(
        self, session: AsyncSession, purchase_id: int, seller_id: int
    ) -> List[PurchaseOffer]:
        """
        Get purchase offers for specific seller and purchase.
        Filters offers by seller's shop points.
        """
        # Get shop point IDs for the seller
        from app.shop_points.models import ShopPoint
        shop_points_result = await session.execute(
            select(ShopPoint.id)
            .where(ShopPoint.seller_id == seller_id)
        )
        shop_point_ids = [row[0] for row in shop_points_result.all()]
        
        if not shop_point_ids:
            return []
        
        # Get offers for these shop points
        offers_result = await session.execute(
            select(Offer.id)
            .where(Offer.shop_id.in_(shop_point_ids))
        )
        offer_ids = [row[0] for row in offers_result.all()]
        
        if not offer_ids:
            return []
        
        # Get purchase offers for these offers
        result = await session.execute(
            select(PurchaseOffer)
            .where(
                and_(
                    PurchaseOffer.purchase_id == purchase_id,
                    PurchaseOffer.offer_id.in_(offer_ids)
                )
            )
            .options(selectinload(PurchaseOffer.offer).selectinload(Offer.product))
        )
        return list(result.scalars().all())

    async def check_all_offers_fulfilled(
        self, session: AsyncSession, purchase_id: int
    ) -> bool:
        """Check if all offers in purchase have been fulfilled (processed)"""
        # Count total offers
        total_result = await session.execute(
            select(PurchaseOffer)
            .where(PurchaseOffer.purchase_id == purchase_id)
        )
        total_offers = len(list(total_result.scalars().all()))
        
        if total_offers == 0:
            return False
        
        # Count fulfilled offers (status is not NULL)
        fulfilled_result = await session.execute(
            select(PurchaseOffer)
            .where(
                and_(
                    PurchaseOffer.purchase_id == purchase_id,
                    PurchaseOffer.fulfillment_status.isnot(None)
                )
            )
        )
        fulfilled_offers = len(list(fulfilled_result.scalars().all()))
        
        return fulfilled_offers == total_offers

