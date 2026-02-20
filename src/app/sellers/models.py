from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, CheckConstraint, ForeignKey, Numeric, Boolean, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ImageMixin

if TYPE_CHECKING:
    from app.auth.models import User
    from app.shop_points.models import ShopPoint
    from app.products.models import Product


class Seller(Base):
    """Seller model"""

    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True)

    full_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    short_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    is_IP: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ogrn: Mapped[str] = mapped_column(String(15), nullable=False)
    master_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_level: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_doc_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    firebase_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    shop_points: Mapped[List["ShopPoint"]] = relationship(
        "ShopPoint", back_populates="seller"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="seller"
    )
    images: Mapped[List["SellerImage"]] = relationship(
        "SellerImage", back_populates="seller", order_by="SellerImage.order"
    )


class SellerImage(ImageMixin, Base):
    """Seller images model"""

    __tablename__ = "seller_images"

    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id"), nullable=False
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="images")


class SellerRegistrationRequest(Base):
    """Seller registration request model."""

    __tablename__ = "seller_registration_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    # User-entered fields are nullable to support draft-like edits.
    full_name: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inn: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    is_IP: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ogrn: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    terms_accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'rejected', 'approved')",
            name="ck_seller_registration_request_status_valid",
        ),
    )

    user: Mapped["User"] = relationship("User")
