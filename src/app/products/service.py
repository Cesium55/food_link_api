from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.products import schemas
from app.products.models import Product, ProductImage, ProductEntry
from app.product_categories.models import ProductCategory, product_category_relations


class ProductsService:
    """Service for working with products"""

    async def create_product(
        self, session: AsyncSession, schema: schemas.ProductCreate
    ) -> Product:
        """Create a new product"""
        # Insert product and get the ID
        result = await session.execute(
            insert(Product)
            .values(
                name=schema.name,
                description=schema.description,
                article=schema.article,
                code=schema.code,
                seller_id=schema.seller_id
            )
            .returning(Product)
        )
        product = result.scalar_one()
        
        # Add categories if provided
        if schema.category_ids:
            await self._add_categories_to_product(session, product.id, schema.category_ids)
        
        return product

    async def get_product_by_id(
        self, session: AsyncSession, product_id: int
    ) -> Optional[Product]:
        """Get product by ID"""
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.images))
        )
        return result.scalar_one_or_none()

    async def get_products(
        self, session: AsyncSession
    ) -> List[Product]:
        """Get list of all products"""
        result = await session.execute(
            select(Product)
            .options(selectinload(Product.images))
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def get_products_by_seller(
        self, session: AsyncSession, seller_id: int
    ) -> List[Product]:
        """Get products by seller ID"""
        result = await session.execute(
            select(Product)
            .where(Product.seller_id == seller_id)
            .options(selectinload(Product.images))
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def get_products_by_category(
        self, session: AsyncSession, category_id: int
    ) -> List[Product]:
        """Get products by category ID"""
        result = await session.execute(
            select(Product)
            .join(Product.categories)
            .where(ProductCategory.id == category_id)
            .options(selectinload(Product.images))
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def update_product(
        self, session: AsyncSession, product_id: int, schema: schemas.ProductUpdate
    ) -> Product:
        """Update product"""
        # Prepare update data
        update_data = {}
        if schema.name is not None:
            update_data['name'] = schema.name
        if schema.description is not None:
            update_data['description'] = schema.description
        if schema.article is not None:
            update_data['article'] = schema.article
        if schema.code is not None:
            update_data['code'] = schema.code

        # Update product and get the updated record
        if update_data:
            result = await session.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(**update_data)
                .returning(Product)
            )
            updated_product = result.scalar_one()
        else:
            # If no data to update, just get the product
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            updated_product = result.scalar_one()

        # Update categories if provided
        if schema.category_ids is not None:
            await self._update_categories_for_product(session, product_id, schema.category_ids)

        # Return updated product with images
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.images))
        )
        updated_product = result.scalar_one()
        return updated_product

    async def delete_product(
        self, session: AsyncSession, product_id: int
    ) -> None:
        """Delete product"""
        await session.execute(
            delete(Product).where(Product.id == product_id)
        )

    async def get_products_summary(
        self, session: AsyncSession
    ) -> schemas.ProductSummary:
        """Get summary statistics for products"""
        total_products_result = await session.execute(
            select(func.count(Product.id))
        )
        total_products = total_products_result.scalar() or 0

        total_sellers_result = await session.execute(
            select(func.count(func.distinct(Product.seller_id)))
        )
        total_sellers = total_sellers_result.scalar() or 0

        avg_products_per_seller = (
            total_products / total_sellers if total_sellers > 0 else 0.0
        )

        return schemas.ProductSummary(
            total_products=total_products,
            total_sellers=total_sellers,
            avg_products_per_seller=avg_products_per_seller
        )

    async def get_products_by_ids(
        self, session: AsyncSession, product_ids: List[int]
    ) -> List[Product]:
        """Get products by list of IDs"""
        result = await session.execute(
            select(Product)
            .where(Product.id.in_(product_ids))
            .options(selectinload(Product.images))
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def _add_categories_to_product(
        self, session: AsyncSession, product_id: int, category_ids: List[int]
    ) -> None:
        """Add categories to product"""
        if not category_ids:
            return
            
        # Insert category relations using SQLAlchemy Core
        values = [{"product_id": product_id, "category_id": cat_id} for cat_id in category_ids]
        await session.execute(
            insert(product_category_relations).values(values)
        )

    async def _update_categories_for_product(
        self, session: AsyncSession, product_id: int, category_ids: List[int]
    ) -> None:
        """Update product categories"""
        # Clear existing categories
        await session.execute(
            delete(product_category_relations).where(
                product_category_relations.c.product_id == product_id
            )
        )
        
        # Add new categories if provided
        if category_ids:
            await self._add_categories_to_product(session, product_id, category_ids)