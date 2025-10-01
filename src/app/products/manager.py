from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.products import schemas
from app.products.service import ProductsService
from app.networks import schemas as networks_schemas
from app.networks.service import NetworksService
from app.product_categories import schemas as categories_schemas
from app.product_categories.service import ProductCategoriesService
from utils.errors_handler import handle_alchemy_error


class ProductsManager:
    """Manager for products business logic and validation"""

    def __init__(self):
        self.service = ProductsService()
        self.networks_service = NetworksService()
        self.categories_service = ProductCategoriesService()

    @handle_alchemy_error
    async def create_product(self, session: AsyncSession, product_data: schemas.ProductCreate) -> schemas.Product:
        """Create a new product with validation"""
        # Create product
        product = await self.service.create_product(session, product_data)
        await session.commit()

        # Return created product with images
        created_product = await self.service.get_product_by_id(session, product.id)
        return schemas.Product.model_validate(created_product)

    async def get_products(self, session: AsyncSession) -> List[schemas.Product]:
        """Get list of products"""
        products = await self.service.get_products(session)
        return [schemas.Product.model_validate(product) for product in products]

    async def get_product_by_id(self, session: AsyncSession, product_id: int) -> schemas.Product:
        """Get product by ID"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        return schemas.Product.model_validate(product)

    async def get_products_by_network(self, session: AsyncSession, network_id: int) -> List[schemas.Product]:
        """Get products by network ID"""
        products = await self.service.get_products_by_network(session, network_id)
        return [schemas.Product.model_validate(product) for product in products]

    async def get_product_with_network(self, session: AsyncSession, product_id: int) -> schemas.ProductWithNetwork:
        """Get product with network information"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Get network data through NetworksService
        network = await self.networks_service.get_network_by_id(session, product.network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {product.network_id} not found"
            )

        product_schema = schemas.Product.model_validate(product)
        network_schema = networks_schemas.Network.model_validate(network)
        
        return schemas.ProductWithNetwork(
            **product_schema.model_dump(),
            network=network_schema
        )

    async def get_product_with_categories(self, session: AsyncSession, product_id: int) -> schemas.ProductWithCategories:
        """Get product with categories"""
        product = await self.service.get_product_by_id(session, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Get categories through ProductCategoriesService
        categories = await self.categories_service.get_categories_by_product(session, product_id)
        categories_list = [categories_schemas.ProductCategory.model_validate(cat) for cat in categories]

        product_schema = schemas.Product.model_validate(product)
        
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

        # Get network data through NetworksService
        network = await self.networks_service.get_network_by_id(session, product.network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {product.network_id} not found"
            )

        # Get categories through ProductCategoriesService
        categories = await self.categories_service.get_categories_by_product(session, product_id)
        categories_list = [categories_schemas.ProductCategory.model_validate(cat) for cat in categories]

        product_schema = schemas.Product.model_validate(product)
        network_schema = networks_schemas.Network.model_validate(network)
        
        return schemas.ProductWithDetails(
            **product_schema.model_dump(),
            network=network_schema,
            categories=categories_list
        )

    @handle_alchemy_error
    async def update_product(
        self, 
        session: AsyncSession,
        product_id: int, 
        product_data: schemas.ProductUpdate
    ) -> schemas.Product:
        """Update product with validation"""
        updated_product = await self.service.update_product(session, product_id, product_data)
        await session.commit()
        return schemas.Product.model_validate(updated_product)

    @handle_alchemy_error
    async def delete_product(self, session: AsyncSession, product_id: int) -> None:
        """Delete product"""
        await self.service.delete_product(session, product_id)
        await session.commit()

    async def get_products_summary(self, session: AsyncSession) -> schemas.ProductSummary:
        """Get products summary statistics"""
        summary = await self.service.get_products_summary(session)
        return summary

    async def get_products_by_ids(self, session: AsyncSession, product_ids: List[int]) -> List[schemas.Product]:
        """Get products by list of IDs"""
        products = await self.service.get_products_by_ids(session, product_ids)
        return [schemas.Product.model_validate(product) for product in products]