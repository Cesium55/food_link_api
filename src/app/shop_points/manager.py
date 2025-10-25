from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.shop_points import schemas
from app.shop_points.service import ShopPointsService
from app.sellers import schemas as sellers_schemas
from app.sellers.service import SellersService
from utils.errors_handler import handle_alchemy_error


class ShopPointsManager:
    """Manager for shop points business logic and validation"""

    def __init__(self):
        self.service = ShopPointsService()
        self.sellers_service = SellersService()

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

    async def get_shop_points_by_seller(self, session: AsyncSession, seller_id: int) -> List[schemas.ShopPoint]:
        """Get shop points by seller ID"""
        shop_points = await self.service.get_shop_points_by_seller(session, seller_id)
        return [schemas.ShopPoint.model_validate(shop_point) for shop_point in shop_points]

    async def get_shop_point_with_seller(self, session: AsyncSession, shop_point_id: int) -> schemas.ShopPointWithSeller:
        """Get shop point with seller information"""
        shop_point = await self.service.get_shop_point_with_seller(session, shop_point_id)
        if not shop_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop point with id {shop_point_id} not found"
            )

        # Get seller data through SellersService
        seller = await self.sellers_service.get_seller_by_id(session, shop_point.seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {shop_point.seller_id} not found"
            )

        shop_point_schema = schemas.ShopPoint.model_validate(shop_point)
        seller_schema = sellers_schemas.Seller.model_validate(seller)
        
        return schemas.ShopPointWithSeller(
            **shop_point_schema.model_dump(),
            seller=seller_schema
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