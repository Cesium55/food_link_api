from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import Integer, Double, String, ForeignKey, CheckConstraint, UniqueConstraint, Text, Index
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from app.auth.models import User
    from app.offers.models import Offer
    from app.payments.models import UserPayment
    from app.sellers.models import Seller


class PurchaseStatus(PyEnum):
    """Purchase status enumeration"""
    PENDING = "pending"  # Заказ создан, ожидает подтверждения
    CONFIRMED = "confirmed"  # Заказ подтвержден, товары зарезервированы
    CANCELLED = "cancelled"  # Заказ отменен
    COMPLETED = "completed"  # Заказ выполнен


class Purchase(Base):
    """Purchase model - represents a purchase order"""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PurchaseStatus.PENDING.value
    )
    total_cost: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "total_cost IS NULL OR total_cost >= 0", 
            name="ck_purchase_total_cost_positive"
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed')",
            name="ck_purchase_status_valid"
        ),
    )

    user: Mapped["User"] = relationship("User", back_populates="purchases")
    purchase_offers: Mapped[List["PurchaseOffer"]] = relationship(
        "PurchaseOffer", back_populates="purchase", cascade="all, delete-orphan"
    )
    offer_results: Mapped[List["PurchaseOfferResult"]] = relationship(
        "PurchaseOfferResult", back_populates="purchase", cascade="all, delete-orphan"
    )
    payments: Mapped[List["UserPayment"]] = relationship(
        "UserPayment", back_populates="purchase", cascade="all, delete-orphan"
    )


class PurchaseOffer(Base):
    """Purchase-Offer relationship model - represents an offer in a purchase"""

    __tablename__ = "purchase_offers"

    purchase_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchases.id"), primary_key=True, nullable=False
    )
    offer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("offers.id"), primary_key=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_at_purchase: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Fulfillment fields
    fulfillment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fulfilled_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fulfilled_by_seller_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sellers.id"), nullable=True, index=True
    )
    unfulfilled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_offer_quantity_positive"),
        CheckConstraint(
            "cost_at_purchase IS NULL OR cost_at_purchase >= 0",
            name="ck_purchase_offer_cost_positive"
        ),
        CheckConstraint(
            "fulfillment_status IS NULL OR fulfillment_status IN ('fulfilled', 'not_fulfilled')",
            name="ck_purchase_offer_fulfillment_status_valid"
        ),
        CheckConstraint(
            "fulfilled_quantity IS NULL OR fulfilled_quantity >= 0",
            name="ck_purchase_offer_fulfilled_quantity_non_negative"
        ),
    )

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="purchase_offers")
    offer: Mapped["Offer"] = relationship("Offer", back_populates="purchase_offers")
    fulfilled_by_seller: Mapped[Optional["Seller"]] = relationship("Seller")


class PurchaseOfferResult(Base):
    """Model for storing offer processing results during purchase creation"""

    __tablename__ = "purchase_offer_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchases.id"), nullable=False, index=True
    )
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    available_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'not_found', 'insufficient_quantity', 'expired')",
            name="ck_purchase_offer_result_status_valid"
        ),
        CheckConstraint(
            "requested_quantity > 0",
            name="ck_purchase_offer_result_requested_quantity_positive"
        ),
        CheckConstraint(
            "processed_quantity IS NULL OR processed_quantity >= 0",
            name="ck_purchase_offer_result_processed_quantity_non_negative"
        ),
        CheckConstraint(
            "available_quantity IS NULL OR available_quantity >= 0",
            name="ck_purchase_offer_result_available_quantity_non_negative"
        ),
    )

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="offer_results")

