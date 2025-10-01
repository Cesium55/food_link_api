from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Double,
    DateTime,
    ForeignKey,
    Table,
    PrimaryKeyConstraint,
    CheckConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


product_category_relations = Table(
    "product_category_relations",
    Base.metadata,
    Column(
        "category_id", Integer, ForeignKey("product_categories.id"), primary_key=True
    ),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    PrimaryKeyConstraint("category_id", "product_id"),
)


class Network(Base):
    """Модель сетей магазинов"""

    __tablename__ = "networks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_network_name_min_length"),
        CheckConstraint("length(slug) >= 1", name="ck_network_slug_min_length"),
    )

    shop_points: Mapped[List["ShopPoint"]] = relationship(
        "ShopPoint", back_populates="network"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="network"
    )
    images: Mapped[List["NetworkImage"]] = relationship(
        "NetworkImage", back_populates="network", order_by="NetworkImage.order"
    )


class ShopPoint(Base):
    """Модель точек продаж (Магазинов)"""

    __tablename__ = "shop_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    network_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("networks.id"), nullable=False, index=True
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

    network: Mapped["Network"] = relationship("Network", back_populates="shop_points")
    product_entries: Mapped[List["ProductEntry"]] = relationship(
        "ProductEntry", back_populates="shop_point"
    )
    images: Mapped[List["ShopPointImage"]] = relationship(
        "ShopPointImage", back_populates="shop_point", order_by="ShopPointImage.order"
    )


class Product(Base):
    """Модель продуктов"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(10000))
    article: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    network_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("networks.id"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_product_name_min_length"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 10000",
            name="ck_product_description_max_length",
        ),
    )

    network: Mapped["Network"] = relationship("Network", back_populates="products")
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


class ImageMixin:
    """Базовый миксин для изображений"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProductImage(ImageMixin, Base):
    """Модель изображений продуктов"""

    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class NetworkImage(ImageMixin, Base):
    """Модель изображений сетей магазинов"""

    __tablename__ = "network_images"

    network_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("networks.id"), nullable=False
    )

    network: Mapped["Network"] = relationship("Network", back_populates="images")


class ShopPointImage(ImageMixin, Base):
    """Модель изображений точек продаж"""

    __tablename__ = "shop_point_images"

    shop_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_points.id"), nullable=False
    )

    shop_point: Mapped["ShopPoint"] = relationship("ShopPoint", back_populates="images")


class ProductCategory(Base):
    """Модель категорий продуктов"""

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


class ProductEntry(Base):
    """Модель записей о наличии продуктов в магазинах"""

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
