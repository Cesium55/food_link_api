from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator

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


class OffersFilterParams(BaseModel):
    """Schema for offers filter query parameters with validation"""
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, description="Number of items per page")
    product_id: Optional[int] = Field(default=None, ge=1, description="Filter by product ID")
    seller_id: Optional[int] = Field(default=None, ge=1, description="Filter by seller ID")
    shop_id: Optional[int] = Field(default=None, ge=1, description="Filter by shop point ID")
    min_expires_date: Optional[datetime] = Field(default=None, description="Minimum expiration date")
    max_expires_date: Optional[datetime] = Field(default=None, description="Maximum expiration date")
    min_original_cost: Optional[float] = Field(default=None, ge=0, description="Minimum original cost")
    max_original_cost: Optional[float] = Field(default=None, ge=0, description="Maximum original cost")
    min_current_cost: Optional[float] = Field(default=None, ge=0, description="Minimum current cost")
    max_current_cost: Optional[float] = Field(default=None, ge=0, description="Maximum current cost")
    min_count: Optional[int] = Field(default=None, ge=0, description="Minimum product count")
    min_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Minimum latitude for location-based filtering")
    max_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Maximum latitude for location-based filtering")
    min_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Minimum longitude for location-based filtering")
    max_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Maximum longitude for location-based filtering")

    @model_validator(mode='after')
    def validate_location_filters(self):
        """Validate that location filters are used correctly"""
        if self.min_latitude is not None and self.max_latitude is not None and self.min_latitude > self.max_latitude:
            raise ValueError("min_latitude must be less than or equal to max_latitude")
        
        if self.min_longitude is not None and self.max_longitude is not None and self.min_longitude > self.max_longitude:
            raise ValueError("min_longitude must be less than or equal to max_longitude")
        
        return self


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
