from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app.payments import schemas
from app.payments.models import UserPayment, PaymentStatus


class PaymentsService:
    """Service for working with payments"""

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
