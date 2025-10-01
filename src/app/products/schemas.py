from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.networks.schemas import Network
    from app.product_categories.schemas import ProductCategory


class ProductImage(BaseModel):
    """Schema for product image"""
    id: int = Field(..., description="Unique identifier")
    path: str = Field(..., min_length=1, max_length=2048, description="Path to image")
    order: int = Field(0, ge=0, description="Image display order")
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """Base schema for product"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=10000, description="Product description")
    article: Optional[str] = Field(None, max_length=255, description="Product article")
    code: Optional[str] = Field(None, max_length=255, description="Product code")


class ProductCreate(ProductBase):
    """Schema for creating product"""
    network_id: int = Field(..., description="Store network ID")
    category_ids: List[int] = Field(default_factory=list, description="Product category IDs")


class ProductUpdate(BaseModel):
    """Schema for updating product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=10000, description="Product description")
    article: Optional[str] = Field(None, max_length=255, description="Product article")
    code: Optional[str] = Field(None, max_length=255, description="Product code")
    category_ids: Optional[List[int]] = Field(None, description="Product category IDs")


class Product(ProductBase):
    """Schema for displaying product"""
    id: int = Field(..., description="Unique identifier")
    network_id: int = Field(..., description="Store network ID")
    images: List[ProductImage] = Field(default_factory=list, description="Product images")
    
    class Config:
        from_attributes = True


class ProductWithNetwork(Product):
    """Product schema with network information"""
    network: "Network" = Field(..., description="Network information")


class ProductWithCategories(Product):
    """Product schema with categories"""
    categories: List["ProductCategory"] = Field(default_factory=list, description="Product categories")


class ProductWithDetails(Product):
    """Product schema with full information"""
    network: "Network" = Field(..., description="Network information")
    categories: List["ProductCategory"] = Field(default_factory=list, description="Product categories")


class ProductSummary(BaseModel):
    """Product summary schema"""
    total_products: int = Field(..., description="Total number of products")
    total_networks: int = Field(..., description="Number of unique networks")
    avg_products_per_network: float = Field(..., description="Average number of products per network")


# Update forward references
def _rebuild_models():
    try:
        from app.networks.schemas import Network
        from app.product_categories.schemas import ProductCategory
        ProductWithNetwork.model_rebuild()
        ProductWithCategories.model_rebuild()
        ProductWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()