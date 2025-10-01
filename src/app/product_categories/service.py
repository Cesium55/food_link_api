from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.product_categories import schemas
from models import ProductCategory, Product


class ProductCategoriesService:
    """Service for working with product categories"""

    async def create_category(
        self, session: AsyncSession, schema: schemas.ProductCategoryCreate
    ) -> ProductCategory:
        """Create a new product category"""
        result = await session.execute(
            insert(ProductCategory)
            .values(
                name=schema.name,
                slug=schema.slug,
                parent_category_id=schema.parent_category_id
            )
            .returning(ProductCategory)
        )
        return result.scalar_one()

    async def get_category_by_id(
        self, session: AsyncSession, category_id: int
    ) -> Optional[ProductCategory]:
        """Get category by ID"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_category_by_slug(
        self, session: AsyncSession, slug: str
    ) -> Optional[ProductCategory]:
        """Get category by slug"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_categories(
        self, session: AsyncSession
    ) -> List[ProductCategory]:
        """Get list of all categories"""
        result = await session.execute(
            select(ProductCategory)
            .order_by(ProductCategory.name)
        )
        return result.scalars().all()

    async def get_root_categories(
        self, session: AsyncSession
    ) -> List[ProductCategory]:
        """Get root categories (without parent)"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.parent_category_id.is_(None))
            .order_by(ProductCategory.name)
        )
        return result.scalars().all()

    async def get_category_with_parent(
        self, session: AsyncSession, category_id: int
    ) -> Optional[ProductCategory]:
        """Get category with parent category"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
            .options(selectinload(ProductCategory.parent_category))
        )
        return result.scalar_one_or_none()

    async def get_category_with_subcategories(
        self, session: AsyncSession, category_id: int
    ) -> Optional[ProductCategory]:
        """Get category with subcategories"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
            .options(selectinload(ProductCategory.subcategories))
        )
        return result.scalar_one_or_none()

    async def get_category_with_products(
        self, session: AsyncSession, category_id: int
    ) -> Optional[ProductCategory]:
        """Get category with products"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_category_with_details(
        self, session: AsyncSession, category_id: int
    ) -> Optional[ProductCategory]:
        """Get category with full information"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
            .options(
                selectinload(ProductCategory.parent_category),
                selectinload(ProductCategory.subcategories)
            )
        )
        return result.scalar_one_or_none()

    async def update_category(
        self, session: AsyncSession, category_id: int, schema: schemas.ProductCategoryUpdate
    ) -> ProductCategory:
        """Update category"""
        # Prepare update data
        update_data = {}
        if schema.name is not None:
            update_data['name'] = schema.name
        if schema.slug is not None:
            update_data['slug'] = schema.slug
        if schema.parent_category_id is not None:
            update_data['parent_category_id'] = schema.parent_category_id

        # Update category
        if update_data:
            await session.execute(
                update(ProductCategory)
                .where(ProductCategory.id == category_id)
                .values(**update_data)
            )

        # Return updated category
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
        )
        updated_category = result.scalar_one()
        return updated_category

    async def delete_category(
        self, session: AsyncSession, category_id: int
    ) -> None:
        """Delete product category"""
        await session.execute(
            delete(ProductCategory).where(ProductCategory.id == category_id)
        )

    async def get_categories_summary(
        self, session: AsyncSession
    ) -> schemas.ProductCategorySummary:
        """Get summary statistics for categories"""
        # Total number of categories
        total_categories_result = await session.execute(
            select(func.count(ProductCategory.id))
        )
        total_categories = total_categories_result.scalar() or 0

        # Number of root categories
        total_root_categories_result = await session.execute(
            select(func.count(ProductCategory.id))
            .where(ProductCategory.parent_category_id.is_(None))
        )
        total_root_categories = total_root_categories_result.scalar() or 0

        # Total number of products
        total_products_result = await session.execute(
            select(func.count(Product.id))
        )
        total_products = total_products_result.scalar() or 0

        # Average number of products per category
        avg_products_per_category = (
            total_products / total_categories if total_categories > 0 else 0.0
        )

        return schemas.ProductCategorySummary(
            total_categories=total_categories,
            total_root_categories=total_root_categories,
            avg_products_per_category=avg_products_per_category
        )

    async def get_categories_by_ids(
        self, session: AsyncSession, category_ids: List[int]
    ) -> List[ProductCategory]:
        """Get categories by list of IDs"""
        result = await session.execute(
            select(ProductCategory)
            .where(ProductCategory.id.in_(category_ids))
            .order_by(ProductCategory.name)
        )
        return result.scalars().all()

    async def get_categories_by_product(
        self, session: AsyncSession, product_id: int
    ) -> List[ProductCategory]:
        """Get categories by product ID"""
        result = await session.execute(
            select(ProductCategory)
            .join(ProductCategory.products)
            .where(Product.id == product_id)
            .order_by(ProductCategory.name)
        )
        return result.scalars().all()