from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, Double, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from app.products.models import Product
    from app.shop_points.models import ShopPoint
    from app.purchases.models import PurchaseOffer


class Offer(Base):
    """Offer model - represents product availability in shop points"""

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    shop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_points.id"), nullable=False, index=True
    )
    expires_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    original_cost: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    current_cost: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    reserved_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "original_cost IS NULL OR original_cost >= 0", name="ck_offer_original_cost_positive"
        ),
        CheckConstraint(
            "current_cost IS NULL OR current_cost >= 0", name="ck_offer_current_cost_positive"
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="ck_offer_count_positive"),
        CheckConstraint(
            "reserved_count IS NULL OR reserved_count >= 0", 
            name="ck_offer_reserved_count_positive"
        ),
        CheckConstraint(
            "reserved_count IS NULL OR count IS NULL OR reserved_count <= count",
            name="ck_offer_reserved_count_not_exceed_count"
        ),
    )

    product: Mapped["Product"] = relationship(
        "Product", back_populates="offers"
    )
    shop_point: Mapped["ShopPoint"] = relationship(
        "ShopPoint", back_populates="offers"
    )
    purchase_offers: Mapped[List["PurchaseOffer"]] = relationship(
        "PurchaseOffer", back_populates="offer"
    )

