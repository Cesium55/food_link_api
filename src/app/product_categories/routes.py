from typing import List
from fastapi import APIRouter, Request
from app.product_categories import schemas
from app.product_categories.manager import ProductCategoriesManager

router = APIRouter(prefix="/product-categories", tags=["product-categories"])

# Initialize manager
categories_manager = ProductCategoriesManager()


@router.post("", response_model=schemas.ProductCategory, status_code=201)
async def create_category(
    request: Request, category_data: schemas.ProductCategoryCreate
) -> schemas.ProductCategory:
    """
    Create a new product category
    """
    return await categories_manager.create_category(request.state.session, category_data)


@router.get("", response_model=List[schemas.ProductCategory])
async def get_categories(request: Request) -> List[schemas.ProductCategory]:
    """
    Get list of categories
    """
    return await categories_manager.get_categories(request.state.session)


@router.get("/root", response_model=List[schemas.ProductCategory])
async def get_root_categories(request: Request) -> List[schemas.ProductCategory]:
    """
    Get root categories (without parent)
    """
    return await categories_manager.get_root_categories(request.state.session)


@router.get("/{category_id}", response_model=schemas.ProductCategory)
async def get_category(request: Request, category_id: int) -> schemas.ProductCategory:
    """
    Get category by ID
    """
    return await categories_manager.get_category_by_id(request.state.session, category_id)


@router.get("/slug/{slug}", response_model=schemas.ProductCategory)
async def get_category_by_slug(request: Request, slug: str) -> schemas.ProductCategory:
    """
    Get category by slug
    """
    return await categories_manager.get_category_by_slug(request.state.session, slug)


@router.get("/{category_id}/with-parent", response_model=schemas.ProductCategoryWithParent)
async def get_category_with_parent(request: Request, category_id: int) -> schemas.ProductCategoryWithParent:
    """
    Get category with parent category
    """
    return await categories_manager.get_category_with_parent(request.state.session, category_id)


@router.get("/{category_id}/with-subcategories", response_model=schemas.ProductCategoryWithSubcategories)
async def get_category_with_subcategories(request: Request, category_id: int) -> schemas.ProductCategoryWithSubcategories:
    """
    Get category with subcategories
    """
    return await categories_manager.get_category_with_subcategories(request.state.session, category_id)


@router.get("/{category_id}/with-products", response_model=schemas.ProductCategoryWithProducts)
async def get_category_with_products(request: Request, category_id: int) -> schemas.ProductCategoryWithProducts:
    """
    Get category with products
    """
    return await categories_manager.get_category_with_products(request.state.session, category_id)


@router.get("/{category_id}/with-details", response_model=schemas.ProductCategoryWithDetails)
async def get_category_with_details(request: Request, category_id: int) -> schemas.ProductCategoryWithDetails:
    """
    Get category with full details
    """
    return await categories_manager.get_category_with_details(request.state.session, category_id)


@router.put("/{category_id}", response_model=schemas.ProductCategory)
async def update_category(
    request: Request,
    category_id: int, 
    category_data: schemas.ProductCategoryUpdate
) -> schemas.ProductCategory:
    """
    Update category
    """
    return await categories_manager.update_category(request.state.session, category_id, category_data)


@router.delete("/{category_id}", status_code=204)
async def delete_category(request: Request, category_id: int) -> None:
    """
    Delete category
    """
    await categories_manager.delete_category(request.state.session, category_id)


@router.get("/summary/stats", response_model=schemas.ProductCategorySummary)
async def get_categories_summary(request: Request) -> schemas.ProductCategorySummary:
    """
    Get categories summary statistics
    """
    return await categories_manager.get_categories_summary(request.state.session)


@router.post("/by-ids", response_model=List[schemas.ProductCategory])
async def get_categories_by_ids(
    request: Request, category_ids: List[int]
) -> List[schemas.ProductCategory]:
    """
    Get categories by list of IDs
    """
    return await categories_manager.get_categories_by_ids(request.state.session, category_ids)