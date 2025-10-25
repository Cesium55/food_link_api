from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, Double, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ImageMixin

if TYPE_CHECKING:
    from app.sellers.models import Seller
    from app.products.models import ProductEntry


class ShopPoint(Base):
    """Shop points model"""

    __tablename__ = "shop_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id"), nullable=False, index=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Double)
    longitude: Mapped[Optional[float]] = mapped_column(Double)

    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_shop_point_latitude_range"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_shop_point_longitude_range",
        ),
        Index("ix_shop_points_coordinates", "latitude", "longitude"),
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="shop_points")
    product_entries: Mapped[List["ProductEntry"]] = relationship(
        "ProductEntry", back_populates="shop_point"
    )
    images: Mapped[List["ShopPointImage"]] = relationship(
        "ShopPointImage", back_populates="shop_point", order_by="ShopPointImage.order"
    )


class ShopPointImage(ImageMixin, Base):
    """Shop point images model"""

    __tablename__ = "shop_point_images"

    shop_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_points.id"), nullable=False
    )

    shop_point: Mapped["ShopPoint"] = relationship("ShopPoint", back_populates="images")