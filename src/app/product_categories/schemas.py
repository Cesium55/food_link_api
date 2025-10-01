from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.products.schemas import Product


class ProductCategoryBase(BaseModel):
    """Base schema for product category"""
    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    slug: str = Field(..., min_length=1, max_length=100, description="Unique category identifier")


class ProductCategoryCreate(ProductCategoryBase):
    """Schema for creating product category"""
    parent_category_id: Optional[int] = Field(None, description="Parent category ID")


class ProductCategoryUpdate(BaseModel):
    """Schema for updating product category"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Category name")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="Unique category identifier")
    parent_category_id: Optional[int] = Field(None, description="Parent category ID")


class ProductCategory(ProductCategoryBase):
    """Schema for displaying product category"""
    id: int = Field(..., description="Unique identifier")
    parent_category_id: Optional[int] = Field(None, description="Parent category ID")
    
    class Config:
        from_attributes = True


class ProductCategoryWithParent(ProductCategory):
    """Category schema with parent category"""
    parent_category: Optional["ProductCategory"] = Field(None, description="Parent category")


class ProductCategoryWithSubcategories(ProductCategory):
    """Category schema with subcategories"""
    subcategories: List["ProductCategory"] = Field(default_factory=list, description="Subcategories")


class ProductCategoryWithProducts(ProductCategory):
    """Category schema with products"""
    products: List["Product"] = Field(default_factory=list, description="Products in category")


class ProductCategoryWithDetails(ProductCategory):
    """Category schema with full information"""
    parent_category: Optional["ProductCategory"] = Field(None, description="Parent category")
    subcategories: List["ProductCategory"] = Field(default_factory=list, description="Subcategories")
    products: List["Product"] = Field(default_factory=list, description="Products in category")


class ProductCategorySummary(BaseModel):
    """Product categories summary schema"""
    total_categories: int = Field(..., description="Total number of categories")
    total_root_categories: int = Field(..., description="Number of root categories")
    avg_products_per_category: float = Field(..., description="Average number of products per category")


# Update forward references
def _rebuild_models():
    try:
        from app.products.schemas import Product
        ProductCategoryWithParent.model_rebuild()
        ProductCategoryWithSubcategories.model_rebuild()
        ProductCategoryWithProducts.model_rebuild()
        ProductCategoryWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()