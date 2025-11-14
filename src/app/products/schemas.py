from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.sellers.schemas import PublicSeller
    from app.product_categories.schemas import ProductCategory


class ProductImage(BaseModel):
    """Schema for product image"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    path: str = Field(..., min_length=1, max_length=2048, description="Path to image")
    order: int = Field(0, ge=0, description="Image display order")


class ProductAttributeBase(BaseModel):
    """Base schema for product attribute"""
    slug: str = Field(..., min_length=1, max_length=100, description="Attribute identifier (e.g., 'weight', 'manufacturer')")
    name: str = Field(..., min_length=1, max_length=255, description="Attribute name (e.g., 'Вес', 'Производитель')")
    value: str = Field(..., min_length=1, max_length=1000, description="Attribute value")


class ProductAttributeCreate(ProductAttributeBase):
    """Schema for creating product attribute"""
    product_id: int = Field(..., description="Product ID")


class ProductAttributeCreateInline(BaseModel):
    """Schema for creating product attribute inline (without product_id)"""
    slug: str = Field(..., min_length=1, max_length=100, description="Attribute identifier (e.g., 'weight', 'manufacturer')")
    name: str = Field(..., min_length=1, max_length=255, description="Attribute name (e.g., 'Вес', 'Производитель')")
    value: str = Field(..., min_length=1, max_length=1000, description="Attribute value")


class ProductAttributeUpdate(BaseModel):
    """Schema for updating product attribute"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Attribute name")
    value: Optional[str] = Field(None, min_length=1, max_length=1000, description="Attribute value")


class ProductAttribute(ProductAttributeBase):
    """Schema for displaying product attribute"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    product_id: int = Field(..., description="Product ID")


class ProductBase(BaseModel):
    """Base schema for product"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=10000, description="Product description")
    article: Optional[str] = Field(None, max_length=255, description="Product article")
    code: Optional[str] = Field(None, max_length=255, description="Product code")


class ProductCreate(ProductBase):
    """Schema for creating product"""
    category_ids: List[int] = Field(default_factory=list, description="Product category IDs")
    attributes: List[ProductAttributeCreateInline] = Field(default_factory=list, description="Product attributes")


class ProductUpdate(BaseModel):
    """Schema for updating product"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=10000, description="Product description")
    article: Optional[str] = Field(None, max_length=255, description="Product article")
    code: Optional[str] = Field(None, max_length=255, description="Product code")
    category_ids: Optional[List[int]] = Field(None, description="Product category IDs")


class Product(ProductBase):
    """Schema for displaying product"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    seller_id: int = Field(..., description="Seller ID")
    images: List[ProductImage] = Field(default_factory=list, description="Product images")
    attributes: List[ProductAttribute] = Field(default_factory=list, description="Product attributes")
    category_ids: List[int] = Field(default_factory=list, description="Product category IDs")


class ProductWithSeller(Product):
    """Product schema with seller information"""
    seller: "PublicSeller" = Field(..., description="Seller information")


class ProductWithCategories(Product):
    """Product schema with categories"""
    categories: List["ProductCategory"] = Field(default_factory=list, description="Product categories")


class ProductWithDetails(Product):
    """Product schema with full information"""
    seller: "PublicSeller" = Field(..., description="Seller information")
    categories: List["ProductCategory"] = Field(default_factory=list, description="Product categories")


class ProductSummary(BaseModel):
    """Product summary schema"""
    total_products: int = Field(..., description="Total number of products")
    total_sellers: int = Field(..., description="Number of unique sellers")
    avg_products_per_seller: float = Field(..., description="Average number of products per seller")


# Update forward references
def _rebuild_models():
    try:
        from app.sellers.schemas import PublicSeller
        from app.product_categories.schemas import ProductCategory
        ProductWithSeller.model_rebuild()
        ProductWithCategories.model_rebuild()
        ProductWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()