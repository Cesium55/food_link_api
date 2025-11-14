from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.sellers.schemas import PublicSeller


class ShopPointImage(BaseModel):
    """Schema for shop point image"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    path: str = Field(..., min_length=1, max_length=2048, description="Path to image")
    order: int = Field(0, ge=0, description="Image display order")


class ShopPointBase(BaseModel):
    """Base schema for shop point"""
    # Location coordinates
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    
    # Address fields for Yandex Maps
    address_raw: Optional[str] = Field(None, description="Raw address")
    address_formated: Optional[str] = Field(None, description="Formatted address")
    region: Optional[str] = Field(None, max_length=255, description="Region")
    city: Optional[str] = Field(None, max_length=255, description="City")
    street: Optional[str] = Field(None, max_length=255, description="Street")
    house: Optional[str] = Field(None, max_length=50, description="House number")
    geo_id: Optional[str] = Field(None, max_length=255, description="Yandex Geocoder GEO ID")


class ShopPointCreate(ShopPointBase):
    """Schema for creating shop point"""
    seller_id: int = Field(..., description="Seller ID")


class ShopPointCreateByAddress(BaseModel):
    """Schema for creating shop point by raw address"""
    raw_address: str = Field(..., min_length=1, description="Raw address to geocode")


class ShopPointUpdate(BaseModel):
    """Schema for updating shop point"""
    # Location coordinates
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    
    # Address fields for Yandex Maps
    address_raw: Optional[str] = Field(None, description="Raw address")
    address_formated: Optional[str] = Field(None, description="Formatted address")
    region: Optional[str] = Field(None, max_length=255, description="Region")
    city: Optional[str] = Field(None, max_length=255, description="City")
    street: Optional[str] = Field(None, max_length=255, description="Street")
    house: Optional[str] = Field(None, max_length=50, description="House number")
    geo_id: Optional[str] = Field(None, max_length=255, description="Yandex Geocoder GEO ID")


class ShopPoint(ShopPointBase):
    """Schema for displaying shop point"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    seller_id: int = Field(..., description="Seller ID")
    images: List[ShopPointImage] = Field(default_factory=list, description="Shop point images")


class ShopPointWithSeller(ShopPoint):
    """Shop point schema with seller information"""
    seller: "PublicSeller" = Field(..., description="Seller information")


class ShopPointSummary(BaseModel):
    """Shop points summary schema"""
    total_shop_points: int = Field(..., description="Total number of shop points")
    total_sellers: int = Field(..., description="Number of unique sellers")
    avg_shop_points_per_seller: float = Field(..., description="Average number of points per seller")


# Update forward references
def _rebuild_models():
    try:
        from app.sellers.schemas import PublicSeller
        ShopPointWithSeller.model_rebuild()
    except ImportError:
        pass

_rebuild_models()