from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.products import schemas
from app.products.models import Product, ProductImage, ProductAttribute
from app.product_categories.models import ProductCategory, product_category_relations


class ProductsService:
    """Service for working with products"""

    async def create_product(
        self, session: AsyncSession, schema: schemas.ProductCreate, seller_id: int
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
                seller_id=seller_id
            )
            .returning(Product)
        )
        product = result.scalar_one()
        
        # Add categories if provided
        if schema.category_ids:
            await self._add_categories_to_product(session, product.id, schema.category_ids)
        
        # Add attributes if provided
        if schema.attributes:
            await self._add_attributes_to_product(session, product.id, schema.attributes)
        
        return product

    async def get_product_by_id(
        self, session: AsyncSession, product_id: int
    ) -> Optional[Product]:
        """Get product by ID"""
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
        )
        return result.scalar_one_or_none()

    async def get_products(
        self, session: AsyncSession
    ) -> List[Product]:
        """Get list of all products"""
        result = await session.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
            .order_by(Product.name)
        )
        return result.scalars().all()

    async def get_products_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        article: Optional[str] = None,
        code: Optional[str] = None,
        seller_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None
    ) -> tuple[List[Product], int]:
        """Get paginated list of products with optional filters"""
        # Build base query with filters
        base_query = select(Product)
        
        # Apply category filter if provided (AND logic - product must have all categories)
        if category_ids is not None and len(category_ids) > 0:
            # Subquery to check that product has all specified categories
            category_count_subquery = (
                select(
                    product_category_relations.c.product_id,
                    func.count(func.distinct(product_category_relations.c.category_id)).label('category_count')
                )
                .where(product_category_relations.c.category_id.in_(category_ids))
                .group_by(product_category_relations.c.product_id)
                .having(func.count(func.distinct(product_category_relations.c.category_id)) == len(category_ids))
                .subquery()
            )
            base_query = base_query.join(
                category_count_subquery,
                Product.id == category_count_subquery.c.product_id
            )
        
        # Apply other filters
        conditions = []
        if article is not None:
            conditions.append(Product.article == article)
        if code is not None:
            conditions.append(Product.code == code)
        if seller_id is not None:
            conditions.append(Product.seller_id == seller_id)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Get total count with filters
        count_query = select(func.count(func.distinct(Product.id)))
        
        # Apply category filter to count query (AND logic - product must have all categories)
        if category_ids is not None and len(category_ids) > 0:
            category_count_subquery = (
                select(
                    product_category_relations.c.product_id,
                    func.count(func.distinct(product_category_relations.c.category_id)).label('category_count')
                )
                .where(product_category_relations.c.category_id.in_(category_ids))
                .group_by(product_category_relations.c.product_id)
                .having(func.count(func.distinct(product_category_relations.c.category_id)) == len(category_ids))
                .subquery()
            )
            count_query = count_query.select_from(Product).join(
                category_count_subquery,
                Product.id == category_count_subquery.c.product_id
            )
        else:
            count_query = count_query.select_from(Product)
        
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results with filters
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
            .order_by(Product.name)
            .limit(page_size)
            .offset(offset)
        )
        products = result.scalars().all()
        
        return products, total_count

    async def get_products_by_seller(
        self, session: AsyncSession, seller_id: int
    ) -> List[Product]:
        """Get products by seller ID"""
        result = await session.execute(
            select(Product)
            .where(Product.seller_id == seller_id)
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
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
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
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

        # Return updated product with images and attributes
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
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
            .options(
                selectinload(Product.images),
                selectinload(Product.attributes),
                selectinload(Product.categories)
            )
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

    async def _add_attributes_to_product(
        self, session: AsyncSession, product_id: int, attributes: List[schemas.ProductAttributeCreateInline]
    ) -> None:
        """Add attributes to product"""
        if not attributes:
            return
            
        # Insert attributes using SQLAlchemy Core
        values = [
            {
                "product_id": product_id,
                "slug": attr.slug,
                "name": attr.name,
                "value": attr.value
            }
            for attr in attributes
        ]
        await session.execute(
            insert(ProductAttribute).values(values)
        )

    async def create_product_attribute(
        self, session: AsyncSession, schema: schemas.ProductAttributeCreate
    ) -> ProductAttribute:
        """Create a new product attribute"""
        result = await session.execute(
            insert(ProductAttribute)
            .values(
                product_id=schema.product_id,
                slug=schema.slug,
                name=schema.name,
                value=schema.value
            )
            .returning(ProductAttribute)
        )
        return result.scalar_one()

    async def get_product_attribute_by_id(
        self, session: AsyncSession, attribute_id: int
    ) -> Optional[ProductAttribute]:
        """Get product attribute by ID"""
        result = await session.execute(
            select(ProductAttribute)
            .where(ProductAttribute.id == attribute_id)
        )
        return result.scalar_one_or_none()

    async def get_product_attributes_by_product(
        self, session: AsyncSession, product_id: int
    ) -> List[ProductAttribute]:
        """Get all attributes for a product"""
        result = await session.execute(
            select(ProductAttribute)
            .where(ProductAttribute.product_id == product_id)
            .order_by(ProductAttribute.slug)
        )
        return result.scalars().all()

    async def get_product_attribute_by_product_and_slug(
        self, session: AsyncSession, product_id: int, slug: str
    ) -> Optional[ProductAttribute]:
        """Get product attribute by product ID and slug"""
        result = await session.execute(
            select(ProductAttribute)
            .where(
                and_(
                    ProductAttribute.product_id == product_id,
                    ProductAttribute.slug == slug
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_product_attribute(
        self, session: AsyncSession, attribute_id: int, schema: schemas.ProductAttributeUpdate
    ) -> ProductAttribute:
        """Update product attribute"""
        update_data = {}
        if schema.name is not None:
            update_data['name'] = schema.name
        if schema.value is not None:
            update_data['value'] = schema.value

        if update_data:
            await session.execute(
                update(ProductAttribute)
                .where(ProductAttribute.id == attribute_id)
                .values(**update_data)
            )

        result = await session.execute(
            select(ProductAttribute)
            .where(ProductAttribute.id == attribute_id)
        )
        return result.scalar_one()

    async def delete_product_attribute(
        self, session: AsyncSession, attribute_id: int
    ) -> None:
        """Delete product attribute"""
        await session.execute(
            delete(ProductAttribute).where(ProductAttribute.id == attribute_id)
        )

    async def create_product_image(
        self, session: AsyncSession, product_id: int, s3_path: str, order: int = 0
    ) -> ProductImage:
        """Create a new product image"""
        result = await session.execute(
            insert(ProductImage)
            .values(
                product_id=product_id,
                path=s3_path,
                order=order
            )
            .returning(ProductImage)
        )
        return result.scalar_one()

    async def get_product_image_by_id(
        self, session: AsyncSession, image_id: int
    ) -> Optional[ProductImage]:
        """Get product image by ID"""
        result = await session.execute(
            select(ProductImage).where(ProductImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def delete_product_image(
        self, session: AsyncSession, image_id: int
    ) -> None:
        """Delete product image"""
        await session.execute(
            delete(ProductImage).where(ProductImage.id == image_id)
        )