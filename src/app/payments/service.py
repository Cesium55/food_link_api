from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_

from app.payments import schemas
from app.payments.models import UserPayment, PaymentStatus, UserRefund
from app.purchases.models import PurchaseOfferResult, PurchaseOffer, MoneyFlowStatus
from app.offers.models import Offer
from app.shop_points.models import ShopPoint


class PaymentsService:
    """Service for working with payments"""


    async def get_batch(self, session: AsyncSession, ids: List[int]):
        result = await session.execute(
            select(UserPayment).where(UserPayment.id.in_(ids))
        )
        return result.scalars().all()

    async def create_payment(
        self,
        session: AsyncSession,
        payment_data: schemas.PaymentCreateInternal,
    ) -> UserPayment:
        """Create a new payment"""
        result = await session.execute(
            insert(UserPayment)
            .values(**payment_data.model_dump())
            .returning(UserPayment)
        )
        return result.scalar_one()

    async def get_payment_by_id(
        self, session: AsyncSession, payment_id: int
    ) -> Optional[UserPayment]:
        """Get payment by ID"""
        result = await session.execute(
            select(UserPayment).where(UserPayment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_id_for_update(
        self, session: AsyncSession, payment_id: int
    ) -> Optional[UserPayment]:
        """Get payment by ID with FOR UPDATE lock"""
        result = await session.execute(
            select(UserPayment)
            .where(UserPayment.id == payment_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_payment_by_yookassa_id(
        self, session: AsyncSession, yookassa_payment_id: str
    ) -> Optional[UserPayment]:
        """Get payment by YooKassa payment ID"""
        result = await session.execute(
            select(UserPayment).where(
                UserPayment.yookassa_payment_id == yookassa_payment_id
            )
        )
        return result.scalar_one_or_none()

    async def get_payment_by_yookassa_id_for_update(
        self, session: AsyncSession, yookassa_payment_id: str
    ) -> Optional[UserPayment]:
        """Get payment by YooKassa payment ID with FOR UPDATE lock"""
        result = await session.execute(
            select(UserPayment)
            .where(UserPayment.yookassa_payment_id == yookassa_payment_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_payment_by_purchase_id(
        self, session: AsyncSession, purchase_id: int
    ) -> Optional[UserPayment]:
        """Get payment by purchase ID (one payment per purchase)"""
        result = await session.execute(
            select(UserPayment)
            .where(UserPayment.purchase_id == purchase_id)
        )
        return result.scalar_one_or_none()

    async def update_payment(
        self,
        session: AsyncSession,
        payment_id: int,
        payment_data: schemas.PaymentUpdate,
    ) -> UserPayment:
        """Update payment"""
        update_data = payment_data.model_dump(exclude_unset=True)

        if update_data:
            result = await session.execute(
                update(UserPayment)
                .where(UserPayment.id == payment_id)
                .values(**update_data)
                .returning(UserPayment)
            )
            return result.scalar_one()

        return await self.get_payment_by_id(session, payment_id)

    async def update_payment_by_yookassa_id(
        self,
        session: AsyncSession,
        yookassa_payment_id: str,
        payment_data: schemas.PaymentUpdate,
    ) -> Optional[UserPayment]:
        """Update payment by YooKassa payment ID"""
        update_data = payment_data.model_dump(exclude_unset=True)

        if update_data:
            result = await session.execute(
                update(UserPayment)
                .where(UserPayment.yookassa_payment_id == yookassa_payment_id)
                .values(**update_data)
                .returning(UserPayment)
            )
            return result.scalar_one_or_none()

        return await self.get_payment_by_yookassa_id(session, yookassa_payment_id)

    async def delete_payment(
        self, session: AsyncSession, payment_id: int
    ) -> None:
        """Delete payment"""
        await session.execute(
            delete(UserPayment).where(UserPayment.id == payment_id)
        )

    async def update_payment_status(
        self, session: AsyncSession, payment_id: int, status: str
    ) -> None:
        """Update payment status"""
        await session.execute(
            update(UserPayment)
            .where(UserPayment.id == payment_id)
            .values(status=status)
        )

    async def get_payment_refunds(self, session: AsyncSession, payment_id: int):
        """Get refunds for a payment"""
        result = await session.execute(
            select(UserRefund).where(UserRefund.payment_id == payment_id)
        )
        return result.scalars().all()
    
    async def create_refund(self, session: AsyncSession, payment_id: int, amount: Decimal, reason: Optional[str] = None) -> UserRefund:
        """Create a refund for a payment"""
        result = await session.execute(
            insert(UserRefund)
            .values(payment_id=payment_id, amount=amount, reason=reason)
            .returning(UserRefund)
        )
        return result.scalar_one()

    async def get_offer_results_with_seller_by_ids_for_update(
        self,
        session: AsyncSession,
        offer_result_ids: List[int],
    ):
        """Get purchase offer results with seller IDs by result IDs with row lock"""
        result = await session.execute(
            select(PurchaseOfferResult, ShopPoint.seller_id)
            .join(Offer, Offer.id == PurchaseOfferResult.offer_id)
            .join(ShopPoint, ShopPoint.id == Offer.shop_id)
            .where(PurchaseOfferResult.id.in_(offer_result_ids))
            .with_for_update()
        )
        return result.all()

    async def get_purchase_offers_by_purchase_and_offer_ids(
        self,
        session: AsyncSession,
        purchase_id: int,
        offer_ids: List[int],
    ) -> List[PurchaseOffer]:
        """Get purchase offers by purchase ID and offer IDs"""
        result = await session.execute(
            select(PurchaseOffer).where(
                PurchaseOffer.purchase_id == purchase_id,
                PurchaseOffer.offer_id.in_(offer_ids),
            )
        )
        return list(result.scalars().all())

    async def update_offer_result_refund_progress(
        self,
        session: AsyncSession,
        offer_result_id: int,
        refund_id: int,
        refunded_quantity: int,
        status: str,
        money_flow_status: str,
        message: str,
    ) -> None:
        """Update purchase offer result refund progress"""
        await session.execute(
            update(PurchaseOfferResult)
            .where(PurchaseOfferResult.id == offer_result_id)
            .values(
                status=status,
                refund_id=refund_id,
                refunded_quantity=refunded_quantity,
                money_flow_status=money_flow_status,
                message=message,
            )
        )

    async def mark_offer_results_in_system_by_purchase(
        self,
        session: AsyncSession,
        purchase_id: int,
    ) -> None:
        """
        Move purchase offer result money flow to in_system after successful payment.

        Include every processed line (processed_quantity > 0), not only full "success".
        """
        await session.execute(
            update(PurchaseOfferResult)
            .where(
                and_(
                    PurchaseOfferResult.purchase_id == purchase_id,
                    PurchaseOfferResult.processed_quantity.is_not(None),
                    PurchaseOfferResult.processed_quantity > 0,
                )
            )
            .values(money_flow_status=MoneyFlowStatus.IN_SYSTEM.value)
        )

    async def get_seller_offer_results_for_system_balance(
        self,
        session: AsyncSession,
        seller_id: int,
    ):
        """Get rows required for calculating seller system balance"""
        result = await session.execute(
            select(
                PurchaseOfferResult,
                PurchaseOffer.cost_at_purchase,
                PurchaseOffer.fulfilled_quantity,
                PurchaseOffer.fulfillment_status,
                PurchaseOffer.fulfilled_at,
                UserPayment.status,
            )
            .join(Offer, Offer.id == PurchaseOfferResult.offer_id)
            .join(ShopPoint, ShopPoint.id == Offer.shop_id)
            .join(
                PurchaseOffer,
                and_(
                    PurchaseOffer.purchase_id == PurchaseOfferResult.purchase_id,
                    PurchaseOffer.offer_id == PurchaseOfferResult.offer_id,
                ),
            )
            .join(UserPayment, UserPayment.purchase_id == PurchaseOfferResult.purchase_id)
            .where(ShopPoint.seller_id == seller_id)
        )
        return result.all()
