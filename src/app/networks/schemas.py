from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.shop_points.schemas import ShopPoint


class NetworkImage(BaseModel):
    """Schema for network image"""

    id: int = Field(..., description="Unique identifier")
    path: str = Field(
        ..., min_length=1, max_length=2048, description="Path to image"
    )
    order: int = Field(0, ge=0, description="Image display order")

    class Config:
        from_attributes = True


class NetworkBase(BaseModel):
    """Base schema for store network"""

    name: str = Field(..., min_length=1, max_length=255, description="Network name")
    slug: str = Field(
        ..., min_length=1, max_length=100, description="Unique network identifier"
    )


class NetworkCreate(NetworkBase):
    """Schema for creating store network"""

    pass


class NetworkUpdate(BaseModel):
    """Schema for updating store network"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Network name"
    )
    slug: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Unique network identifier"
    )


class Network(NetworkBase):
    """Schema for displaying store network"""

    id: int = Field(..., description="Unique identifier")
    images: List[NetworkImage] = Field(
        default_factory=list, description="Network images"
    )

    class Config:
        from_attributes = True


class NetworkWithShopPoints(Network):
    """Network schema with shop points"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Network shop points"
    )


class NetworkWithDetails(Network):
    """Network schema with full information"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Network shop points"
    )


class NetworkSummary(BaseModel):
    """Networks summary schema"""

    total_networks: int = Field(..., description="Total number of networks")
    total_products: int = Field(..., description="Total number of products in networks")
    avg_products_per_network: float = Field(
        ..., description="Average number of products per network"
    )


# Update forward references
def _rebuild_models():
    try:
        from app.shop_points.schemas import ShopPoint

        NetworkWithShopPoints.model_rebuild()
        NetworkWithDetails.model_rebuild()
    except ImportError:
        pass


_rebuild_models()
