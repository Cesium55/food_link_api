from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.products.schemas import Product
    from app.shop_points.schemas import ShopPoint


class ProductEntryBase(BaseModel):
    """Base schema for product availability record"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[float] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[float] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")


class ProductEntryCreate(ProductEntryBase):
    """Schema for creating product availability record"""
    product_id: int = Field(..., description="Product ID")
    shop_id: int = Field(..., description="Shop point ID")


class ProductEntryUpdate(BaseModel):
    """Schema for updating product availability record"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[float] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[float] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")


class ProductEntry(ProductEntryBase):
    """Schema for displaying product availability record"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    product_id: int = Field(..., description="Product ID")
    shop_id: int = Field(..., description="Shop point ID")


class ProductEntryWithProduct(ProductEntry):
    """Record schema with product information"""
    product: "Product" = Field(..., description="Product information")


class ProductEntryWithShop(ProductEntry):
    """Record schema with shop point information"""
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class ProductEntryWithDetails(ProductEntry):
    """Record schema with full information"""
    product: "Product" = Field(..., description="Product information")
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class InventorySummary(BaseModel):
    """Inventory summary schema"""
    total_entries: int = Field(..., description="Total number of entries")
    total_products: int = Field(..., description="Number of unique products")
    total_shop_points: int = Field(..., description="Number of unique shop points")
    total_value: float = Field(..., description="Total inventory value")


class ExpiringProductsSummary(BaseModel):
    """Expiring products summary schema"""
    expiring_soon: int = Field(..., description="Number of products expiring soon")
    expired: int = Field(..., description="Number of expired products")
    total_entries: int = Field(..., description="Total number of entries with expiration date")


# Update forward references
def _rebuild_models():
    try:
        from app.products.schemas import Product
        from app.shop_points.schemas import ShopPoint
        ProductEntryWithProduct.model_rebuild()
        ProductEntryWithShop.model_rebuild()
        ProductEntryWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()