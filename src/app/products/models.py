from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Double, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ImageMixin

if TYPE_CHECKING:
    from app.sellers.models import Seller
    from app.product_categories.models import ProductCategory
    from app.shop_points.models import ShopPoint


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
    product_entries: Mapped[List["ProductEntry"]] = relationship(
        "ProductEntry", back_populates="product"
    )
    categories: Mapped[List["ProductCategory"]] = relationship(
        "ProductCategory",
        secondary="product_category_relations",
        back_populates="products",
    )


class ProductImage(ImageMixin, Base):
    """Product images model"""

    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class ProductEntry(Base):
    """Product entries model"""

    __tablename__ = "product_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    shop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_points.id"), nullable=False, index=True
    )
    expires_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=False)
    original_cost: Mapped[Optional[float]] = mapped_column(Double, nullable=False)
    current_cost: Mapped[Optional[float]] = mapped_column(Double, nullable=False)
    count: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint(
            "original_cost >= 0", name="ck_product_entry_original_cost_positive"
        ),
        CheckConstraint(
            "current_cost >= 0", name="ck_product_entry_current_cost_positive"
        ),
        CheckConstraint("count >= 0", name="ck_product_entry_count_positive"),
        UniqueConstraint("product_id", "shop_id", name="uq_product_entry_product_shop"),
    )

    product: Mapped["Product"] = relationship(
        "Product", back_populates="product_entries"
    )
    shop_point: Mapped["ShopPoint"] = relationship(
        "ShopPoint", back_populates="product_entries"
    )
