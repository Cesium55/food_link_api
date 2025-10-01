from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.shop_points import schemas
from models import ShopPoint, ShopPointImage, Network


class ShopPointsService:
    """Service for working with shop points"""

    async def create_shop_point(
        self, session: AsyncSession, schema: schemas.ShopPointCreate
    ) -> ShopPoint:
        """Create a new shop point"""
        result = await session.execute(
            insert(ShopPoint)
            .values(
                network_id=schema.network_id,
                latitude=schema.latitude,
                longitude=schema.longitude
            )
            .returning(ShopPoint)
        )
        return result.scalar_one()

    async def get_shop_point_by_id(
        self, session: AsyncSession, shop_point_id: int
    ) -> Optional[ShopPoint]:
        """Get shop point by ID"""
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.id == shop_point_id)
            .options(selectinload(ShopPoint.images))
        )
        return result.scalar_one_or_none()

    async def get_shop_points(
        self, session: AsyncSession
    ) -> List[ShopPoint]:
        """Get list of all shop points"""
        result = await session.execute(
            select(ShopPoint)
            .options(selectinload(ShopPoint.images))
            .order_by(ShopPoint.id)
        )
        return result.scalars().all()

    async def get_shop_points_by_network(
        self, session: AsyncSession, network_id: int
    ) -> List[ShopPoint]:
        """Get shop points by network ID"""
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.network_id == network_id)
            .options(selectinload(ShopPoint.images))
            .order_by(ShopPoint.id)
        )
        return result.scalars().all()

    async def get_shop_point_with_network(
        self, session: AsyncSession, shop_point_id: int
    ) -> Optional[ShopPoint]:
        """Get shop point with network information"""
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.id == shop_point_id)
            .options(selectinload(ShopPoint.images))
        )
        return result.scalar_one_or_none()

    async def update_shop_point(
        self, session: AsyncSession, shop_point_id: int, schema: schemas.ShopPointUpdate
    ) -> ShopPoint:
        """Update shop point"""
        # Prepare update data
        update_data = {}
        if schema.latitude is not None:
            update_data['latitude'] = schema.latitude
        if schema.longitude is not None:
            update_data['longitude'] = schema.longitude

        # Update shop point
        if update_data:
            await session.execute(
                update(ShopPoint)
                .where(ShopPoint.id == shop_point_id)
                .values(**update_data)
            )

        # Return updated shop point with images
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.id == shop_point_id)
            .options(selectinload(ShopPoint.images))
        )
        updated_shop_point = result.scalar_one()
        return updated_shop_point

    async def delete_shop_point(
        self, session: AsyncSession, shop_point_id: int
    ) -> None:
        """Delete shop point"""
        await session.execute(
            delete(ShopPoint).where(ShopPoint.id == shop_point_id)
        )

    async def get_shop_points_summary(
        self, session: AsyncSession
    ) -> schemas.ShopPointSummary:
        """Get summary statistics for shop points"""
        # Total number of shop points
        total_shop_points_result = await session.execute(
            select(func.count(ShopPoint.id))
        )
        total_shop_points = total_shop_points_result.scalar() or 0

        # Number of unique networks
        total_networks_result = await session.execute(
            select(func.count(func.distinct(ShopPoint.network_id)))
        )
        total_networks = total_networks_result.scalar() or 0

        # Average number of points per network
        avg_shop_points_per_network = (
            total_shop_points / total_networks if total_networks > 0 else 0.0
        )

        return schemas.ShopPointSummary(
            total_shop_points=total_shop_points,
            total_networks=total_networks,
            avg_shop_points_per_network=avg_shop_points_per_network
        )

    async def get_shop_points_by_ids(
        self, session: AsyncSession, shop_point_ids: List[int]
    ) -> List[ShopPoint]:
        """Get shop points by list of IDs"""
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.id.in_(shop_point_ids))
            .options(selectinload(ShopPoint.images))
            .order_by(ShopPoint.id)
        )
        return result.scalars().all()