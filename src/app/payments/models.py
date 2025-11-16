from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import Integer, Double, String, ForeignKey, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from app.purchases.models import Purchase


class PaymentStatus(PyEnum):
    """Payment status enumeration"""
    PENDING = "pending"  # Payment created, waiting for confirmation
    WAITING_FOR_CAPTURE = "waiting_for_capture"  # Payment waiting for capture
    SUCCEEDED = "succeeded"  # Payment completed successfully
    CANCELED = "canceled"  # Payment canceled


class UserPayment(Base):
    """UserPayment model - represents a payment for a purchase via YooKassa"""

    __tablename__ = "user_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchases.id"), nullable=False, index=True
    )
    yookassa_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PaymentStatus.PENDING.value
    )
    amount: Mapped[float] = mapped_column(Double, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmation_url: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    idempotence_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    captured_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    cancellation_details: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_user_payment_amount_positive"
        ),
        CheckConstraint(
            "status IN ('pending', 'waiting_for_capture', 'succeeded', 'canceled')",
            name="ck_user_payment_status_valid"
        ),
        CheckConstraint(
            "currency IN ('RUB')",
            name="ck_user_payment_currency_valid"
        ),
    )

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="payments")
