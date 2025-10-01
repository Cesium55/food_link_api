from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.networks import schemas
from app.networks.service import NetworksService
from app.shop_points.service import ShopPointsService
from app.shop_points import schemas as shop_points_schemas
from app.products.service import ProductsService
from app.products import schemas as products_schemas
from src.utils.errors_handler import handle_alchemy_error


class NetworksManager:
    """Manager for network business logic and validation"""

    def __init__(self):
        self.service = NetworksService()
        self.shop_points_service = ShopPointsService()
        self.products_service = ProductsService()

    @handle_alchemy_error
    async def create_network(self, session: AsyncSession, network_data: schemas.NetworkCreate) -> schemas.Network:
        """Create a new network with validation"""
        # Create network
        network = await self.service.create_network(session, network_data)
        await session.commit()

        # Return created network with images
        created_network = await self.service.get_network_by_id(session, network.id)
        return schemas.Network.model_validate(created_network)

    async def get_networks(self, session: AsyncSession) -> List[schemas.Network]:
        """Get list of networks"""
        networks = await self.service.get_networks(session)
        return [schemas.Network.model_validate(network) for network in networks]

    async def get_network_by_id(self, session: AsyncSession, network_id: int) -> schemas.Network:
        """Get network by ID"""
        network = await self.service.get_network_by_id(session, network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {network_id} not found"
            )

        return schemas.Network.model_validate(network)

    async def get_network_by_slug(self, session: AsyncSession, slug: str) -> schemas.Network:
        network = await self.service.get_network_by_slug(session, slug)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with slug '{slug}' not found"
            )

        return schemas.Network.model_validate(network)

    async def get_network_with_shop_points(self, session: AsyncSession, network_id: int) -> schemas.NetworkWithShopPoints:
        """Get network with shop points"""
        network = await self.service.get_network_with_shop_points(session, network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {network_id} not found"
            )

        shop_points = await self.shop_points_service.get_shop_points_by_network(session, network_id)
        
        network_schema = schemas.Network.model_validate(network)
        shop_points_as_schemas = [shop_points_schemas.ShopPoint.model_validate(sp) for sp in shop_points]
        
        return schemas.NetworkWithShopPoints(
            **network_schema.model_dump(),
            shop_points=shop_points_as_schemas
        )

    async def get_network_with_details(self, session: AsyncSession, network_id: int) -> schemas.NetworkWithDetails:
        """Get network with full details"""
        network = await self.service.get_network_with_details(session, network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {network_id} not found"
            )

        shop_points = await self.shop_points_service.get_shop_points_by_network(session, network_id)
        products = await self.products_service.get_products_by_network(session, network_id)
        
        network_schema = schemas.Network.model_validate(network)
        shop_points_as_schemas = [shop_points_schemas.ShopPoint.model_validate(sp) for sp in shop_points]
        products_schemas = [products_schemas.Product.model_validate(p) for p in products]
        
        return schemas.NetworkWithDetails(
            **network_schema.model_dump(),
            shop_points=shop_points_as_schemas,
            products=products_schemas
        )

    @handle_alchemy_error
    async def update_network(
        self, 
        session: AsyncSession,
        network_id: int, 
        network_data: schemas.NetworkUpdate
    ) -> schemas.Network:
        """Update network with validation"""
        updated_network = await self.service.update_network(session, network_id, network_data)
        await session.commit()
        return schemas.Network.model_validate(updated_network)

    @handle_alchemy_error
    async def delete_network(self, session: AsyncSession, network_id: int) -> None:
        """Delete network"""
        await self.service.delete_network(session, network_id)
        await session.commit()

    async def get_networks_summary(self, session: AsyncSession) -> schemas.NetworkSummary:
        """Get networks summary statistics"""
        summary = await self.service.get_networks_summary(session)
        return summary

    async def get_networks_by_ids(self, session: AsyncSession, network_ids: List[int]) -> List[schemas.Network]:
        """Get networks by list of IDs"""
        networks = await self.service.get_networks_by_ids(session, network_ids)
        return [schemas.Network.model_validate(network) for network in networks]
