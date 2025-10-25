from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, Table, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from app.products.models import Product


product_category_relations = Table(
    "product_category_relations",
    Base.metadata,
    Column(
        "category_id", Integer, ForeignKey("product_categories.id"), primary_key=True
    ),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    PrimaryKeyConstraint("category_id", "product_id"),
)


class ProductCategory(Base):
    """Product categories model"""

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    parent_category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_categories.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "length(name) >= 1", name="ck_product_category_name_min_length"
        ),
        CheckConstraint(
            "length(slug) >= 1", name="ck_product_category_slug_min_length"
        ),
        CheckConstraint(
            "parent_category_id IS NULL OR parent_category_id != id",
            name="ck_product_category_no_self_parent",
        ),
    )

    parent_category: Mapped[Optional["ProductCategory"]] = relationship(
        "ProductCategory", remote_side=[id], back_populates="subcategories"
    )
    subcategories: Mapped[List["ProductCategory"]] = relationship(
        "ProductCategory", back_populates="parent_category"
    )

    products: Mapped[List["Product"]] = relationship(
        "Product", secondary="product_category_relations", back_populates="categories"
    )
