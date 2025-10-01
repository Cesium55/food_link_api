from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.shop_points import schemas
from app.shop_points.service import ShopPointsService
from app.networks import schemas as networks_schemas
from app.networks.service import NetworksService
from utils.errors_handler import handle_alchemy_error


class ShopPointsManager:
    """Manager for shop points business logic and validation"""

    def __init__(self):
        self.service = ShopPointsService()
        self.networks_service = NetworksService()

    @handle_alchemy_error
    async def create_shop_point(self, session: AsyncSession, shop_point_data: schemas.ShopPointCreate) -> schemas.ShopPoint:
        """Create a new shop point with validation"""
        # Create shop point
        shop_point = await self.service.create_shop_point(session, shop_point_data)
        await session.commit()

        # Return created shop point with images
        created_shop_point = await self.service.get_shop_point_by_id(session, shop_point.id)
        return schemas.ShopPoint.model_validate(created_shop_point)

    async def get_shop_points(self, session: AsyncSession) -> List[schemas.ShopPoint]:
        """Get list of shop points"""
        shop_points = await self.service.get_shop_points(session)
        return [schemas.ShopPoint.model_validate(shop_point) for shop_point in shop_points]

    async def get_shop_point_by_id(self, session: AsyncSession, shop_point_id: int) -> schemas.ShopPoint:
        """Get shop point by ID"""
        shop_point = await self.service.get_shop_point_by_id(session, shop_point_id)
        if not shop_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop point with id {shop_point_id} not found"
            )

        return schemas.ShopPoint.model_validate(shop_point)

    async def get_shop_points_by_network(self, session: AsyncSession, network_id: int) -> List[schemas.ShopPoint]:
        """Get shop points by network ID"""
        shop_points = await self.service.get_shop_points_by_network(session, network_id)
        return [schemas.ShopPoint.model_validate(shop_point) for shop_point in shop_points]

    async def get_shop_point_with_network(self, session: AsyncSession, shop_point_id: int) -> schemas.ShopPointWithNetwork:
        """Get shop point with network information"""
        shop_point = await self.service.get_shop_point_with_network(session, shop_point_id)
        if not shop_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop point with id {shop_point_id} not found"
            )

        # Get network data through NetworksService
        network = await self.networks_service.get_network_by_id(session, shop_point.network_id)
        if not network:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Network with id {shop_point.network_id} not found"
            )

        shop_point_schema = schemas.ShopPoint.model_validate(shop_point)
        network_schema = networks_schemas.Network.model_validate(network)
        
        return schemas.ShopPointWithNetwork(
            **shop_point_schema.model_dump(),
            network=network_schema
        )

    @handle_alchemy_error
    async def update_shop_point(
        self, 
        session: AsyncSession,
        shop_point_id: int, 
        shop_point_data: schemas.ShopPointUpdate
    ) -> schemas.ShopPoint:
        """Update shop point with validation"""
        updated_shop_point = await self.service.update_shop_point(session, shop_point_id, shop_point_data)
        await session.commit()
        return schemas.ShopPoint.model_validate(updated_shop_point)

    @handle_alchemy_error
    async def delete_shop_point(self, session: AsyncSession, shop_point_id: int) -> None:
        """Delete shop point"""
        await self.service.delete_shop_point(session, shop_point_id)
        await session.commit()

    async def get_shop_points_summary(self, session: AsyncSession) -> schemas.ShopPointSummary:
        """Get shop points summary statistics"""
        summary = await self.service.get_shop_points_summary(session)
        return summary

    async def get_shop_points_by_ids(self, session: AsyncSession, shop_point_ids: List[int]) -> List[schemas.ShopPoint]:
        """Get shop points by list of IDs"""
        shop_points = await self.service.get_shop_points_by_ids(session, shop_point_ids)
        return [schemas.ShopPoint.model_validate(shop_point) for shop_point in shop_points]