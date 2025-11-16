from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app.purchases.models import Purchase, PurchaseOffer, PurchaseOfferResult


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

