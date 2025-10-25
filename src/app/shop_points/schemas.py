from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.sellers.schemas import Seller


class ShopPointImage(BaseModel):
    """Schema for shop point image"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    path: str = Field(..., min_length=1, max_length=2048, description="Path to image")
    order: int = Field(0, ge=0, description="Image display order")


class ShopPointBase(BaseModel):
    """Base schema for shop point"""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class ShopPointCreate(ShopPointBase):
    """Schema for creating shop point"""
    seller_id: int = Field(..., description="Seller ID")


class ShopPointUpdate(BaseModel):
    """Schema for updating shop point"""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class ShopPoint(ShopPointBase):
    """Schema for displaying shop point"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    seller_id: int = Field(..., description="Seller ID")
    images: List[ShopPointImage] = Field(default_factory=list, description="Shop point images")


class ShopPointWithSeller(ShopPoint):
    """Shop point schema with seller information"""
    seller: "Seller" = Field(..., description="Seller information")


class ShopPointSummary(BaseModel):
    """Shop points summary schema"""
    total_shop_points: int = Field(..., description="Total number of shop points")
    total_sellers: int = Field(..., description="Number of unique sellers")
    avg_shop_points_per_seller: float = Field(..., description="Average number of points per seller")


# Update forward references
def _rebuild_models():
    try:
        from app.sellers.schemas import Seller
        ShopPointWithSeller.model_rebuild()
    except ImportError:
        pass

_rebuild_models()