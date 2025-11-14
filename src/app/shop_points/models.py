from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, Double, ForeignKey, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ImageMixin

if TYPE_CHECKING:
    from app.sellers.models import Seller
    from app.offers.models import Offer


class ShopPoint(Base):
    """Shop points model"""

    __tablename__ = "shop_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id"), nullable=False, index=True
    )
    
    # Location coordinates
    latitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    
    # Address fields for Yandex Maps integration
    address_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Raw address
    address_formated: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Formatted address
    region: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Region
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # City
    street: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Street
    house: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # House number
    geo_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Yandex Geocoder GEO ID

    seller: Mapped["Seller"] = relationship("Seller", back_populates="shop_points")
    offers: Mapped[List["Offer"]] = relationship(
        "Offer", back_populates="shop_point"
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