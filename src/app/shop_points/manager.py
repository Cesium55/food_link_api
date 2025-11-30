from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.shop_points import schemas
from app.shop_points.service import ShopPointsService
from app.sellers import schemas as sellers_schemas
from app.sellers.service import SellersService
from app.maps.yandex_geocoder import create_geocoder
from utils.errors_handler import handle_alchemy_error
from utils.image_manager import ImageManager
from fastapi import UploadFile


class ShopPointsManager:
    """Manager for shop points business logic and validation"""

    def __init__(self):
        self.service = ShopPointsService()
        self.sellers_service = SellersService()
        self.image_manager = ImageManager()

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
        seller_schema = sellers_schemas.PublicSeller.model_validate(seller)
        
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
    
    @handle_alchemy_error
    async def create_shop_point_by_address(
        self, session: AsyncSession, user_id: int, shop_point_data: schemas.ShopPointCreateByAddress
    ) -> schemas.ShopPoint:
        """Create shop point by raw address"""
        # Check if user is seller
        seller = await self.sellers_service.get_seller_by_master_id(session, user_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a seller"
            )
        
        # Geocode address
        geocoder = create_geocoder()
        try:
            result = await geocoder.geocode_address(shop_point_data.raw_address)
            
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Address not found"
                )
            
            if not result.formatted_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Address could not be formatted"
                )
            
            if "Россия" not in result.formatted_address and "Russia" not in result.formatted_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Address must be in Russia"
                )
            
            # Prepare geocoded data
            geocoded_data = {
                "latitude": result.latitude,
                "longitude": result.longitude,
                "address_raw": result.address_raw,
                "formatted_address": result.formatted_address,
                "region": result.region,
                "city": result.city,
                "street": result.street,
                "house": result.house,
                "geo_id": result.geo_id
            }
            
            # Create shop point
            shop_point = await self.service.create_shop_point_by_address(
                session, seller.id, geocoded_data
            )
            await session.commit()
            
            # Return created shop point with images
            created_shop_point = await self.service.get_shop_point_by_id(session, shop_point.id)
            return schemas.ShopPoint.model_validate(created_shop_point)
        finally:
            await geocoder.close()

    @handle_alchemy_error
    async def upload_shop_point_image(
        self,
        session: AsyncSession,
        shop_point_id: int,
        file: UploadFile,
        order: int = 0
    ) -> schemas.ShopPointImage:
        """Upload image for shop point"""
        return await self.image_manager.upload_and_create_image_record(
            session=session,
            entity_id=shop_point_id,
            file=file,
            prefix="shop-points",
            order=order,
            entity_name="shop point",
            get_entity_func=self.service.get_shop_point_by_id,
            create_image_func=self.service.create_shop_point_image,
            schema_class=schemas.ShopPointImage
        )

    @handle_alchemy_error
    async def upload_shop_point_images(
        self,
        session: AsyncSession,
        shop_point_id: int,
        files: list[UploadFile],
        start_order: int = 0
    ) -> list[schemas.ShopPointImage]:
        """Upload multiple images for shop point"""
        return await self.image_manager.upload_multiple_and_create_image_records(
            session=session,
            entity_id=shop_point_id,
            files=files,
            prefix="shop-points",
            start_order=start_order,
            entity_name="shop point",
            get_entity_func=self.service.get_shop_point_by_id,
            create_image_func=self.service.create_shop_point_image,
            schema_class=schemas.ShopPointImage
        )

    @handle_alchemy_error
    async def delete_shop_point_image(
        self,
        session: AsyncSession,
        image_id: int
    ) -> None:
        """Delete shop point image"""
        await self.image_manager.delete_image_record(
            session=session,
            image_id=image_id,
            entity_name="shop point",
            get_image_func=self.service.get_shop_point_image_by_id,
            delete_image_func=self.service.delete_shop_point_image
        )