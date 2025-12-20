from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, UploadFile

from app.products import schemas
from app.products.service import ProductsService
from app.sellers import schemas as sellers_schemas
from app.sellers.service import SellersService
from app.sellers.models import Seller
from app.product_categories import schemas as categories_schemas
from app.product_categories.service import ProductCategoriesService
from app.auth.models import User
from utils.errors_handler import handle_alchemy_error
from utils.image_manager import ImageManager
from utils.pagination import PaginatedResponse
from utils.seller_dependencies import verify_seller_owns_resource


class ProductsManager:
    """Manager for products business logic and validation"""

    def __init__(self):
        self.service = ProductsService()
        self.sellers_service = SellersService()
        self.categories_service = ProductCategoriesService()
        self.image_manager = ImageManager()

    @handle_alchemy_error
    async def create_product(
        self, 
        session: AsyncSession, 
        product_data: schemas.ProductCreate,
        current_user: User
    ) -> schemas.Product:
        """Create a new product with validation"""
        # Check if user is a seller
        if not current_user.is_seller:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only sellers can create products"
            )
        
        # Get seller by user's master_id
        seller = await self.sellers_service.get_seller_by_master_id(session, current_user.id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seller account not found for current user"
            )
        
        # Create product with seller_id
        product = await self.service.create_product(session, product_data, seller.id)
        await session.commit()

        # Return created product with images and attributes
        created_product = await self.service.get_product_by_id(session, product.id)
        product_schema = schemas.Product.model_validate(created_product)
        
        # Add category IDs from loaded categories
        product_schema.category_ids = [cat.id for cat in created_product.categories]
        
        return product_schema

    async def get_products(self, session: AsyncSession) -> List[schemas.Product]:
        """Get list of products"""
        products = await self.service.get_products(session)
        result = []
        for product in products:
            product_schema = schemas.Product.model_validate(product)
            # Add category IDs from loaded categories
            product_schema.category_ids = [cat.id for cat in product.categories]
            result.append(product_schema)
        return result

    async def get_products_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        article: Optional[str] = None,
        code: Optional[str] = None,
        seller_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None
    ) -> PaginatedResponse[schemas.Product]:
        """Get paginated list of products with optional filters"""
        products, total_count = await self.service.get_products_paginated(
            session, page, page_size, article, code, seller_id, category_ids
        )
        result = []
        for product in products:
            product_schema = schemas.Product.model_validate(product)
            # Add category IDs from loaded categories
            product_schema.category_ids = [cat.id for cat in product.categories]
            result.append(product_schema)
        return PaginatedResponse.create(
            items=result,
            page=page,
            page_size=page_size,
            total_items=total_count
        )

    async def get_product_by_id(self, session: AsyncSession, product_id: int) -> schemas.Product:
        """Get product by ID"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        product_schema = schemas.Product.model_validate(product)
        # Add category IDs from loaded categories
        product_schema.category_ids = [cat.id for cat in product.categories]
        
        return product_schema

    async def get_products_by_seller(self, session: AsyncSession, seller_id: int) -> List[schemas.Product]:
        """Get products by seller ID"""
        products = await self.service.get_products_by_seller(session, seller_id)
        result = []
        for product in products:
            product_schema = schemas.Product.model_validate(product)
            # Add category IDs from loaded categories
            product_schema.category_ids = [cat.id for cat in product.categories]
            result.append(product_schema)
        return result

    async def get_product_with_seller(self, session: AsyncSession, product_id: int) -> schemas.ProductWithSeller:
        """Get product with seller information"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Get seller data through SellersService
        seller = await self.sellers_service.get_seller_by_id(session, product.seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {product.seller_id} not found"
            )

        product_schema = schemas.Product.model_validate(product)
        seller_schema = sellers_schemas.PublicSeller.model_validate(seller)
        
        return schemas.ProductWithSeller(
            **product_schema.model_dump(),
            seller=seller_schema
        )

    async def get_product_with_categories(self, session: AsyncSession, product_id: int) -> schemas.ProductWithCategories:
        """Get product with categories"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Get categories from loaded product
        categories_list = [categories_schemas.ProductCategory.model_validate(cat) for cat in product.categories]

        product_schema = schemas.Product.model_validate(product)
        product_schema.category_ids = [cat.id for cat in product.categories]
        
        return schemas.ProductWithCategories(
            **product_schema.model_dump(),
            categories=categories_list
        )

    async def get_product_with_details(self, session: AsyncSession, product_id: int) -> schemas.ProductWithDetails:
        """Get product with full details"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Get seller data through SellersService
        seller = await self.sellers_service.get_seller_by_id(session, product.seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {product.seller_id} not found"
            )

        # Get categories from loaded product
        categories_list = [categories_schemas.ProductCategory.model_validate(cat) for cat in product.categories]

        product_schema = schemas.Product.model_validate(product)
        product_schema.category_ids = [cat.id for cat in product.categories]
        seller_schema = sellers_schemas.PublicSeller.model_validate(seller)
        
        return schemas.ProductWithDetails(
            **product_schema.model_dump(),
            seller=seller_schema,
            categories=categories_list
        )

    @handle_alchemy_error
    async def update_product(
        self, 
        session: AsyncSession,
        product_id: int, 
        product_data: schemas.ProductUpdate,
        current_seller: Seller = None
    ) -> schemas.Product:
        """Update product with validation"""
        # Check ownership
        if current_seller:
            product = await self.service.get_product_by_id(session, product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        updated_product = await self.service.update_product(session, product_id, product_data)
        await session.commit()
        
        product_schema = schemas.Product.model_validate(updated_product)
        # Add category IDs from loaded categories
        product_schema.category_ids = [cat.id for cat in updated_product.categories]
        
        return product_schema

    @handle_alchemy_error
    async def delete_product(self, session: AsyncSession, product_id: int, current_seller: Seller = None) -> None:
        """Delete product"""
        # Check ownership
        if current_seller:
            product = await self.service.get_product_by_id(session, product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        await self.service.delete_product(session, product_id)
        await session.commit()

    async def get_products_summary(self, session: AsyncSession) -> schemas.ProductSummary:
        """Get products summary statistics"""
        summary = await self.service.get_products_summary(session)
        return summary

    async def get_products_by_ids(self, session: AsyncSession, product_ids: List[int]) -> List[schemas.Product]:
        """Get products by list of IDs"""
        products = await self.service.get_products_by_ids(session, product_ids)
        result = []
        for product in products:
            product_schema = schemas.Product.model_validate(product)
            # Add category IDs from loaded categories
            product_schema.category_ids = [cat.id for cat in product.categories]
            result.append(product_schema)
        return result

    @handle_alchemy_error
    async def create_product_attribute(
        self, session: AsyncSession, attribute_data: schemas.ProductAttributeCreate, current_seller: Seller = None
    ) -> schemas.ProductAttribute:
        """Create a new product attribute"""
        # Check ownership
        if current_seller:
            product = await self.service.get_product_by_id(session, attribute_data.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {attribute_data.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        attribute = await self.service.create_product_attribute(session, attribute_data)
        await session.commit()
        return schemas.ProductAttribute.model_validate(attribute)

    async def get_product_attribute_by_id(
        self, session: AsyncSession, attribute_id: int
    ) -> schemas.ProductAttribute:
        """Get product attribute by ID"""
        attribute = await self.service.get_product_attribute_by_id(session, attribute_id)
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product attribute with id {attribute_id} not found"
            )
        return schemas.ProductAttribute.model_validate(attribute)

    async def get_product_attributes_by_product(
        self, session: AsyncSession, product_id: int
    ) -> List[schemas.ProductAttribute]:
        """Get all attributes for a product"""
        attributes = await self.service.get_product_attributes_by_product(session, product_id)
        return [schemas.ProductAttribute.model_validate(attr) for attr in attributes]

    async def get_product_attribute_by_product_and_slug(
        self, session: AsyncSession, product_id: int, slug: str
    ) -> schemas.ProductAttribute:
        """Get product attribute by product ID and slug"""
        attribute = await self.service.get_product_attribute_by_product_and_slug(session, product_id, slug)
        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product attribute with slug '{slug}' not found for product {product_id}"
            )
        return schemas.ProductAttribute.model_validate(attribute)

    @handle_alchemy_error
    async def update_product_attribute(
        self, session: AsyncSession, attribute_id: int, attribute_data: schemas.ProductAttributeUpdate, current_seller: Seller = None
    ) -> schemas.ProductAttribute:
        """Update product attribute"""
        # Check ownership
        if current_seller:
            attribute = await self.service.get_product_attribute_by_id(session, attribute_id)
            if not attribute:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product attribute with id {attribute_id} not found"
                )
            product = await self.service.get_product_by_id(session, attribute.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {attribute.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        updated_attribute = await self.service.update_product_attribute(session, attribute_id, attribute_data)
        await session.commit()
        return schemas.ProductAttribute.model_validate(updated_attribute)

    @handle_alchemy_error
    async def delete_product_attribute(self, session: AsyncSession, attribute_id: int, current_seller: Seller = None) -> None:
        """Delete product attribute"""
        # Check ownership
        if current_seller:
            attribute = await self.service.get_product_attribute_by_id(session, attribute_id)
            if not attribute:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product attribute with id {attribute_id} not found"
                )
            product = await self.service.get_product_by_id(session, attribute.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {attribute.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        await self.service.delete_product_attribute(session, attribute_id)
        await session.commit()

    @handle_alchemy_error
    async def upload_product_image(
        self,
        session: AsyncSession,
        product_id: int,
        file: UploadFile,
        order: int = 0,
        current_seller: Seller = None
    ) -> schemas.ProductImage:
        """Upload image for product"""
        # Check ownership
        if current_seller:
            product = await self.service.get_product_by_id(session, product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        return await self.image_manager.upload_and_create_image_record(
            session=session,
            entity_id=product_id,
            file=file,
            prefix="products",
            order=order,
            entity_name="product",
            get_entity_func=self.service.get_product_by_id,
            create_image_func=self.service.create_product_image,
            schema_class=schemas.ProductImage
        )

    @handle_alchemy_error
    async def upload_product_images(
        self,
        session: AsyncSession,
        product_id: int,
        files: list[UploadFile],
        start_order: int = 0,
        current_seller: Seller = None
    ) -> list[schemas.ProductImage]:
        """Upload multiple images for product"""
        # Check ownership
        if current_seller:
            product = await self.service.get_product_by_id(session, product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        return await self.image_manager.upload_multiple_and_create_image_records(
            session=session,
            entity_id=product_id,
            files=files,
            prefix="products",
            start_order=start_order,
            entity_name="product",
            get_entity_func=self.service.get_product_by_id,
            create_image_func=self.service.create_product_image,
            schema_class=schemas.ProductImage
        )

    @handle_alchemy_error
    async def delete_product_image(
        self,
        session: AsyncSession,
        image_id: int,
        current_seller: Seller = None
    ) -> None:
        """Delete product image"""
        # Check ownership
        if current_seller:
            image = await self.service.get_product_image_by_id(session, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product image not found"
                )
            product = await self.service.get_product_by_id(session, image.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {image.product_id} not found"
                )
            await verify_seller_owns_resource(product.seller_id, current_seller)
        
        await self.image_manager.delete_image_record(
            session=session,
            image_id=image_id,
            entity_name="product",
            get_image_func=self.service.get_product_image_by_id,
            delete_image_func=self.service.delete_product_image
        )