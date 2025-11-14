from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.products.schemas import Product
    from app.shop_points.schemas import ShopPoint


class OfferBase(BaseModel):
    """Base schema for offer"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[float] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[float] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")


class OfferCreate(OfferBase):
    """Schema for creating offer"""
    product_id: int = Field(..., description="Product ID")
    shop_id: int = Field(..., description="Shop point ID")


class OfferUpdate(BaseModel):
    """Schema for updating offer"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[float] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[float] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")


class Offer(OfferBase):
    """Schema for displaying offer"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    product_id: int = Field(..., description="Product ID")
    shop_id: int = Field(..., description="Shop point ID")
    reserved_count: Optional[int] = Field(None, ge=0, description="Product reserved quantity")


class OfferWithProduct(Offer):
    """Offer schema with product information"""
    product: "Product" = Field(..., description="Product information")


class OfferWithShop(Offer):
    """Offer schema with shop point information"""
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class OfferWithDetails(Offer):
    """Offer schema with full information"""
    product: "Product" = Field(..., description="Product information")
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class OffersSummary(BaseModel):
    """Offers summary schema"""
    total_entries: int = Field(..., description="Total number of offers")
    total_products: int = Field(..., description="Number of unique products")
    total_shop_points: int = Field(..., description="Number of unique shop points")
    total_value: float = Field(..., description="Total offers value")


class ExpiringProductsSummary(BaseModel):
    """Expiring products summary schema"""
    expiring_soon: int = Field(..., description="Number of products expiring soon")
    expired: int = Field(..., description="Number of expired products")
    total_entries: int = Field(..., description="Total number of offers with expiration date")


# Update forward references
def _rebuild_models():
    try:
        from app.products.schemas import Product
        from app.shop_points.schemas import ShopPoint
        OfferWithProduct.model_rebuild()
        OfferWithShop.model_rebuild()
        OfferWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()
