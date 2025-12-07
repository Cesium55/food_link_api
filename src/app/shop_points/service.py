from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload

from app.shop_points import schemas
from app.shop_points.models import ShopPoint, ShopPointImage
from app.sellers.models import Seller


class ShopPointsService:
    """Service for working with shop points"""

    async def create_shop_point(
        self, session: AsyncSession, schema: schemas.ShopPointCreate
    ) -> ShopPoint:
        """Create a new shop point"""
        result = await session.execute(
            insert(ShopPoint)
            .values(
                seller_id=schema.seller_id,
                latitude=schema.latitude,
                longitude=schema.longitude,
                address_raw=schema.address_raw,
                address_formated=schema.address_formated,
                region=schema.region,
                city=schema.city,
                street=schema.street,
                house=schema.house,
                geo_id=schema.geo_id
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

    async def get_shop_points_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        region: Optional[str] = None,
        city: Optional[str] = None,
        seller_id: Optional[int] = None,
        min_latitude: Optional[float] = None,
        max_latitude: Optional[float] = None,
        min_longitude: Optional[float] = None,
        max_longitude: Optional[float] = None
    ) -> tuple[List[ShopPoint], int]:
        """Get paginated list of shop points with optional filters"""
        # Build base query with filters
        base_query = select(ShopPoint)
        
        # Apply filters
        conditions = []
        if region is not None:
            conditions.append(ShopPoint.region == region)
        if city is not None:
            conditions.append(ShopPoint.city == city)
        if seller_id is not None:
            conditions.append(ShopPoint.seller_id == seller_id)
        if min_latitude is not None:
            conditions.append(ShopPoint.latitude >= min_latitude)
        if max_latitude is not None:
            conditions.append(ShopPoint.latitude <= max_latitude)
        if min_longitude is not None:
            conditions.append(ShopPoint.longitude >= min_longitude)
        if max_longitude is not None:
            conditions.append(ShopPoint.longitude <= max_longitude)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Get total count with filters
        count_query = select(func.count(ShopPoint.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results with filters
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query
            .options(selectinload(ShopPoint.images))
            .order_by(ShopPoint.id)
            .limit(page_size)
            .offset(offset)
        )
        shop_points = result.scalars().all()
        
        return shop_points, total_count

    async def get_shop_points_by_seller(
        self, session: AsyncSession, seller_id: int
    ) -> List[ShopPoint]:
        """Get shop points by seller ID"""
        result = await session.execute(
            select(ShopPoint)
            .where(ShopPoint.seller_id == seller_id)
            .options(selectinload(ShopPoint.images))
            .order_by(ShopPoint.id)
        )
        return result.scalars().all()

    async def get_shop_point_with_seller(
        self, session: AsyncSession, shop_point_id: int
    ) -> Optional[ShopPoint]:
        """Get shop point with seller information"""
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
        if schema.address_raw is not None:
            update_data['address_raw'] = schema.address_raw
        if schema.address_formated is not None:
            update_data['address_formated'] = schema.address_formated
        if schema.region is not None:
            update_data['region'] = schema.region
        if schema.city is not None:
            update_data['city'] = schema.city
        if schema.street is not None:
            update_data['street'] = schema.street
        if schema.house is not None:
            update_data['house'] = schema.house
        if schema.geo_id is not None:
            update_data['geo_id'] = schema.geo_id

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

        # Number of unique sellers
        total_sellers_result = await session.execute(
            select(func.count(func.distinct(ShopPoint.seller_id)))
        )
        total_sellers = total_sellers_result.scalar() or 0

        # Average number of points per seller
        avg_shop_points_per_seller = (
            total_shop_points / total_sellers if total_sellers > 0 else 0.0
        )

        return schemas.ShopPointSummary(
            total_shop_points=total_shop_points,
            total_sellers=total_sellers,
            avg_shop_points_per_seller=avg_shop_points_per_seller
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
    
    async def create_shop_point_by_address(
        self, session: AsyncSession, seller_id: int, geocoded_data: dict
    ) -> ShopPoint:
        """Create shop point with geocoded data"""
        result = await session.execute(
            insert(ShopPoint)
            .values(
                seller_id=seller_id,
                latitude=geocoded_data.get("latitude"),
                longitude=geocoded_data.get("longitude"),
                address_raw=geocoded_data.get("address_raw"),
                address_formated=geocoded_data.get("formatted_address"),
                region=geocoded_data.get("region"),
                city=geocoded_data.get("city"),
                street=geocoded_data.get("street"),
                house=geocoded_data.get("house"),
                geo_id=geocoded_data.get("geo_id")
            )
            .returning(ShopPoint)
        )
        return result.scalar_one()

    async def create_shop_point_image(
        self, session: AsyncSession, shop_point_id: int, s3_path: str, order: int = 0
    ) -> ShopPointImage:
        """Create a new shop point image"""
        result = await session.execute(
            insert(ShopPointImage)
            .values(
                shop_point_id=shop_point_id,
                path=s3_path,
                order=order
            )
            .returning(ShopPointImage)
        )
        return result.scalar_one()

    async def get_shop_point_image_by_id(
        self, session: AsyncSession, image_id: int
    ) -> Optional[ShopPointImage]:
        """Get shop point image by ID"""
        result = await session.execute(
            select(ShopPointImage).where(ShopPointImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def delete_shop_point_image(
        self, session: AsyncSession, image_id: int
    ) -> None:
        """Delete shop point image"""
        await session.execute(
            delete(ShopPointImage).where(ShopPointImage.id == image_id)
        )