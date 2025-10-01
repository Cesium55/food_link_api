from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.networks.schemas import Network


class ShopPointImage(BaseModel):
    """Schema for shop point image"""
    id: int = Field(..., description="Unique identifier")
    path: str = Field(..., min_length=1, max_length=2048, description="Path to image")
    order: int = Field(0, ge=0, description="Image display order")
    
    class Config:
        from_attributes = True


class ShopPointBase(BaseModel):
    """Base schema for shop point"""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class ShopPointCreate(ShopPointBase):
    """Schema for creating shop point"""
    network_id: int = Field(..., description="Store network ID")


class ShopPointUpdate(BaseModel):
    """Schema for updating shop point"""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class ShopPoint(ShopPointBase):
    """Schema for displaying shop point"""
    id: int = Field(..., description="Unique identifier")
    network_id: int = Field(..., description="Store network ID")
    images: List[ShopPointImage] = Field(default_factory=list, description="Shop point images")
    
    class Config:
        from_attributes = True


class ShopPointWithNetwork(ShopPoint):
    """Shop point schema with network information"""
    network: "Network" = Field(..., description="Network information")


class ShopPointSummary(BaseModel):
    """Shop points summary schema"""
    total_shop_points: int = Field(..., description="Total number of shop points")
    total_networks: int = Field(..., description="Number of unique networks")
    avg_shop_points_per_network: float = Field(..., description="Average number of points per network")


# Update forward references
def _rebuild_models():
    try:
        from app.networks.schemas import Network
        ShopPointWithNetwork.model_rebuild()
    except ImportError:
        pass

_rebuild_models()