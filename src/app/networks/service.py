from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.networks import schemas
from models import Network, NetworkImage, ShopPoint, Product


class NetworksService:
    """Service for working with store networks"""

    async def create_network(
        self, session: AsyncSession, schema: schemas.NetworkCreate
    ) -> Network:
        """Create a new store network"""
        result = await session.execute(
            insert(Network)
            .values(
                name=schema.name,
                slug=schema.slug
            )
            .returning(Network)
        )
        return result.scalar_one()

    async def get_network_by_id(
        self, session: AsyncSession, network_id: int
    ) -> Optional[Network]:
        """Get network by ID"""
        result = await session.execute(
            select(Network)
            .where(Network.id == network_id)
            .options(selectinload(Network.images))
        )
        return result.scalar_one_or_none()

    async def get_network_by_slug(
        self, session: AsyncSession, slug: str
    ) -> Optional[Network]:
        """Get network by slug"""
        result = await session.execute(
            select(Network)
            .where(Network.slug == slug)
            .options(selectinload(Network.images))
        )
        return result.scalar_one_or_none()

    async def get_networks(self, session: AsyncSession) -> List[Network]:
        """Get list of all networks"""
        result = await session.execute(
            select(Network)
            .options(selectinload(Network.images))
            .order_by(Network.name)
        )
        return result.scalars().all()

    async def get_network_with_shop_points(
        self, session: AsyncSession, network_id: int
    ) -> Optional[Network]:
        """Get network with shop points"""
        result = await session.execute(
            select(Network)
            .where(Network.id == network_id)
            .options(selectinload(Network.images))
        )
        return result.scalar_one_or_none()

    async def get_network_with_details(
        self, session: AsyncSession, network_id: int
    ) -> Optional[Network]:
        """Get network with full information"""
        result = await session.execute(
            select(Network)
            .where(Network.id == network_id)
            .options(selectinload(Network.images))
        )
        return result.scalar_one_or_none()

    async def update_network(
        self, session: AsyncSession, network_id: int, schema: schemas.NetworkUpdate
    ) -> Network:
        """Update network"""
        # Prepare update data
        update_data = {}
        if schema.name is not None:
            update_data['name'] = schema.name
        if schema.slug is not None:
            update_data['slug'] = schema.slug

        # Update network
        if update_data:
            await session.execute(
                update(Network)
                .where(Network.id == network_id)
                .values(**update_data)
            )

        # Return updated network with images
        result = await session.execute(
            select(Network)
            .where(Network.id == network_id)
            .options(selectinload(Network.images))
        )
        updated_network = result.scalar_one()
        return updated_network

    async def delete_network(
        self, session: AsyncSession, network_id: int
    ) -> None:
        """Delete store network"""
        await session.execute(
            delete(Network).where(Network.id == network_id)
        )


    async def get_networks_summary(
        self, session: AsyncSession
    ) -> schemas.NetworkSummary:
        """Get summary statistics for networks"""
        # Total number of networks
        total_networks_result = await session.execute(
            select(func.count(Network.id))
        )
        total_networks = total_networks_result.scalar() or 0

        # Total number of products in all networks
        total_products_result = await session.execute(
            select(func.count(Product.id))
        )
        total_products = total_products_result.scalar() or 0

        # Average number of products per network
        avg_products_per_network = (
            total_products / total_networks if total_networks > 0 else 0.0
        )

        return schemas.NetworkSummary(
            total_networks=total_networks,
            total_products=total_products,
            avg_products_per_network=avg_products_per_network
        )


    async def get_networks_by_ids(
        self, session: AsyncSession, network_ids: List[int]
    ) -> List[Network]:
        """Get networks by list of IDs"""
        result = await session.execute(
            select(Network)
            .where(Network.id.in_(network_ids))
            .options(selectinload(Network.images))
            .order_by(Network.name)
        )
        return result.scalars().all()
