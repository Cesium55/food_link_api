from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Float, Integer, Double, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, String
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
    pricing_strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pricing_strategies.id"), nullable=True
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
    pricing_strategy: Mapped[Optional["PricingStrategy"]] = relationship(
        "PricingStrategy", back_populates="offers"
    )


class PricingStrategy(Base):
    """Pricing strategy model - represents dynamic pricing strategy with steps"""

    __tablename__ = "pricing_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "length(name) >= 1", name="ck_pricing_strategy_name_min_length"
        ),
    )

    steps: Mapped[List["PricingStrategyStep"]] = relationship(
        "PricingStrategyStep", back_populates="strategy", cascade="all, delete-orphan", order_by="PricingStrategyStep.time_remaining_seconds"
    )
    offers: Mapped[List["Offer"]] = relationship(
        "Offer", back_populates="pricing_strategy"
    )


class PricingStrategyStep(Base):
    """Pricing strategy step model - represents a single step in pricing strategy"""

    __tablename__ = "pricing_strategy_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pricing_strategies.id"), nullable=False, index=True
    )
    time_remaining_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "time_remaining_seconds >= 0", name="ck_pricing_strategy_step_time_remaining_positive"
        ),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100", 
            name="ck_pricing_strategy_step_discount_range"
        ),
    )

    strategy: Mapped["PricingStrategy"] = relationship(
        "PricingStrategy", back_populates="steps"
    )
