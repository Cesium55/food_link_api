from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Double, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ImageMixin

if TYPE_CHECKING:
    from app.sellers.models import Seller
    from app.product_categories.models import ProductCategory
    from app.shop_points.models import ShopPoint
    from app.offers.models import Offer


class Product(Base):
    """Products model"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(10000))
    article: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_product_name_min_length"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 10000",
            name="ck_product_description_max_length",
        ),
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage", back_populates="product", order_by="ProductImage.order"
    )
    offers: Mapped[List["Offer"]] = relationship(
        "Offer", back_populates="product"
    )
    categories: Mapped[List["ProductCategory"]] = relationship(
        "ProductCategory",
        secondary="product_category_relations",
        back_populates="products",
    )
    attributes: Mapped[List["ProductAttribute"]] = relationship(
        "ProductAttribute", back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(ImageMixin, Base):
    """Product images model"""

    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class ProductAttribute(Base):
    """Product attributes model"""

    __tablename__ = "product_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(1000), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "length(slug) >= 1", name="ck_product_attribute_slug_min_length"
        ),
        CheckConstraint(
            "length(name) >= 1", name="ck_product_attribute_name_min_length"
        ),
        CheckConstraint(
            "length(value) >= 1", name="ck_product_attribute_value_min_length"
        ),
        UniqueConstraint("product_id", "slug", name="uq_product_attribute_product_slug"),
    )

    product: Mapped["Product"] = relationship("Product", back_populates="attributes")
