from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.product_categories import schemas
from app.product_categories.service import ProductCategoriesService
from app.products.service import ProductsService
from app.products import schemas as products_schemas
from utils.errors_handler import handle_alchemy_error


class ProductCategoriesManager:
    """Manager for product categories business logic and validation"""

    def __init__(self):
        self.service = ProductCategoriesService()
        self.products_service = ProductsService()

    @handle_alchemy_error
    async def create_category(self, session: AsyncSession, category_data: schemas.ProductCategoryCreate) -> schemas.ProductCategory:
        """Create a new category with validation"""
        # Create category
        category = await self.service.create_category(session, category_data)
        await session.commit()

        # Return created category
        created_category = await self.service.get_category_by_id(session, category.id)
        return schemas.ProductCategory.model_validate(created_category)

    async def get_categories(self, session: AsyncSession) -> List[schemas.ProductCategory]:
        """Get list of categories"""
        categories = await self.service.get_categories(session)
        return [schemas.ProductCategory.model_validate(category) for category in categories]

    async def get_category_by_id(self, session: AsyncSession, category_id: int) -> schemas.ProductCategory:
        """Get category by ID"""
        category = await self.service.get_category_by_id(session, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found"
            )

        return schemas.ProductCategory.model_validate(category)

    async def get_category_by_slug(self, session: AsyncSession, slug: str) -> schemas.ProductCategory:
        """Get category by slug"""
        category = await self.service.get_category_by_slug(session, slug)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with slug '{slug}' not found"
            )

        return schemas.ProductCategory.model_validate(category)

    async def get_root_categories(self, session: AsyncSession) -> List[schemas.ProductCategory]:
        """Get root categories (without parent)"""
        categories = await self.service.get_root_categories(session)
        return [schemas.ProductCategory.model_validate(category) for category in categories]

    async def get_category_with_parent(self, session: AsyncSession, category_id: int) -> schemas.ProductCategoryWithParent:
        """Get category with parent category"""
        category = await self.service.get_category_with_parent(session, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found"
            )

        category_schema = schemas.ProductCategory.model_validate(category)
        parent_schema = schemas.ProductCategory.model_validate(category.parent_category) if category.parent_category else None
        
        return schemas.ProductCategoryWithParent(
            **category_schema.model_dump(),
            parent_category=parent_schema
        )

    async def get_category_with_subcategories(self, session: AsyncSession, category_id: int) -> schemas.ProductCategoryWithSubcategories:
        """Get category with subcategories"""
        category = await self.service.get_category_with_subcategories(session, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found"
            )

        category_schema = schemas.ProductCategory.model_validate(category)
        subcategories_schemas = [schemas.ProductCategory.model_validate(sub) for sub in category.subcategories]
        
        return schemas.ProductCategoryWithSubcategories(
            **category_schema.model_dump(),
            subcategories=subcategories_schemas
        )

    async def get_category_with_products(self, session: AsyncSession, category_id: int) -> schemas.ProductCategoryWithProducts:
        """Get category with products"""
        category = await self.service.get_category_with_products(session, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found"
            )

        category_schema = schemas.ProductCategory.model_validate(category)
        # Load products through ProductsService
        products = await self.products_service.get_products_by_category(session, category_id)
        products_list = [products_schemas.Product.model_validate(product) for product in products]
        
        return schemas.ProductCategoryWithProducts(
            **category_schema.model_dump(),
            products=products_list
        )

    async def get_category_with_details(self, session: AsyncSession, category_id: int) -> schemas.ProductCategoryWithDetails:
        """Get category with full details"""
        category = await self.service.get_category_with_details(session, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {category_id} not found"
            )

        category_schema = schemas.ProductCategory.model_validate(category)
        parent_schema = schemas.ProductCategory.model_validate(category.parent_category) if category.parent_category else None
        subcategories_schemas = [schemas.ProductCategory.model_validate(sub) for sub in category.subcategories]
        # Load products through ProductsService
        products = await self.products_service.get_products_by_category(session, category_id)
        products_list = [products_schemas.Product.model_validate(product) for product in products]
        
        return schemas.ProductCategoryWithDetails(
            **category_schema.model_dump(),
            parent_category=parent_schema,
            subcategories=subcategories_schemas,
            products=products_list
        )

    @handle_alchemy_error
    async def update_category(
        self, 
        session: AsyncSession,
        category_id: int, 
        category_data: schemas.ProductCategoryUpdate
    ) -> schemas.ProductCategory:
        """Update category with validation"""
        updated_category = await self.service.update_category(session, category_id, category_data)
        await session.commit()
        return schemas.ProductCategory.model_validate(updated_category)

    @handle_alchemy_error
    async def delete_category(self, session: AsyncSession, category_id: int) -> None:
        """Delete category"""
        await self.service.delete_category(session, category_id)
        await session.commit()

    async def get_categories_summary(self, session: AsyncSession) -> schemas.ProductCategorySummary:
        """Get categories summary statistics"""
        summary = await self.service.get_categories_summary(session)
        return summary

    async def get_categories_by_ids(self, session: AsyncSession, category_ids: List[int]) -> List[schemas.ProductCategory]:
        """Get categories by list of IDs"""
        categories = await self.service.get_categories_by_ids(session, category_ids)
        return [schemas.ProductCategory.model_validate(category) for category in categories]