from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import update
from app.sellers import schemas
from app.sellers.service import SellersService
from app.shop_points.service import ShopPointsService
from app.shop_points import schemas as shop_points_schemas
from app.products.service import ProductsService
from app.products import schemas as products_schemas
from app.auth.models import User
from app.auth.password_utils import PasswordUtils
from utils.errors_handler import handle_alchemy_error
from app.sellers.models import Seller
from app.auth.service import AuthService
from utils.image_manager import ImageManager
from utils.firebase_notification_manager import FirebaseNotificationManager
from fastapi import UploadFile
from utils.pagination import PaginatedResponse
from utils.seller_dependencies import verify_seller_owns_resource


class SellersManager:
    """Manager for seller business logic and validation"""

    def __init__(self):
        self.service = SellersService()
        self.shop_points_service = ShopPointsService()
        self.products_service = ProductsService()
        self.password_utils = PasswordUtils()
        self.auth_service = AuthService()
        self.image_manager = ImageManager()
        self.notification_manager = FirebaseNotificationManager()

    @handle_alchemy_error
    async def create_seller(
        self,
        session: AsyncSession,
        seller_data: schemas.SellerCreate,
        current_user: User,
    ) -> schemas.Seller:
        """Создать продавца для текущего пользователя"""

        # Проверка: у пользователя уже есть продавец
        existing_seller = await self.service.get_seller_by_master_id(
            session, current_user.id
        )
        if existing_seller:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У пользователя уже есть аккаунт продавца",
            )

        # Создаем продавца
        seller = await self.service.create_seller(session, seller_data, current_user.id, current_user.email)
        user = await self.auth_service.update_user_is_seller(session, current_user.id, True)
        
        await session.commit()

        return schemas.Seller.model_validate(seller)

    async def get_sellers(self, session: AsyncSession) -> List[schemas.PublicSeller]:
        """Get list of sellers"""
        sellers = await self.service.get_sellers(session)
        return [schemas.PublicSeller.model_validate(seller) for seller in sellers]

    async def get_sellers_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        status: Optional[int] = None, verification_level: Optional[int] = None
    ) -> PaginatedResponse[schemas.PublicSeller]:
        """Get paginated list of sellers with optional filters"""
        sellers, total_count = await self.service.get_sellers_paginated(
            session, page, page_size, status, verification_level
        )
        seller_schemas = [
            schemas.PublicSeller.model_validate(seller) for seller in sellers
        ]
        return PaginatedResponse.create(
            items=seller_schemas,
            page=page,
            page_size=page_size,
            total_items=total_count
        )

    async def get_seller_by_id(
        self, session: AsyncSession, seller_id: int
    ) -> schemas.PublicSeller:
        """Get seller by ID"""
        seller = await self.service.get_seller_by_id(session, seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {seller_id} not found",
            )

        return schemas.PublicSeller.model_validate(seller)

    async def get_seller_by_email(
        self, session: AsyncSession, email: str
    ) -> schemas.Seller:
        """Get seller by email"""
        # Находим пользователя по email, затем его продавца
        user = await self.auth_service.get_user_by_email(session, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found",
            )

        seller = await self.service.get_seller_by_master_id(session, user.id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with email '{email}' not found",
            )

        return schemas.Seller.model_validate(seller)

    async def get_seller_with_shop_points(
        self, session: AsyncSession, seller_id: int
    ) -> schemas.PublicSellerWithShopPoints:
        """Get seller with shop points"""
        seller = await self.service.get_seller_with_shop_points(session, seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {seller_id} not found",
            )

        shop_points = await self.shop_points_service.get_shop_points_by_seller(
            session, seller_id
        )

        seller_schema = schemas.PublicSeller.model_validate(seller)
        shop_points_as_schemas = [
            shop_points_schemas.ShopPoint.model_validate(sp) for sp in shop_points
        ]

        return schemas.PublicSellerWithShopPoints(
            **seller_schema.model_dump(), shop_points=shop_points_as_schemas
        )

    async def get_seller_with_details(
        self, session: AsyncSession, seller_id: int
    ) -> schemas.PublicSellerWithDetails:
        """Get seller with full details"""
        seller = await self.service.get_seller_with_details(session, seller_id)
        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with id {seller_id} not found",
            )

        shop_points = await self.shop_points_service.get_shop_points_by_seller(
            session, seller_id
        )
        products = await self.products_service.get_products_by_seller(
            session, seller_id
        )

        seller_schema = schemas.PublicSeller.model_validate(seller)
        shop_points_as_schemas = [
            shop_points_schemas.ShopPoint.model_validate(sp) for sp in shop_points
        ]
        products_schemas_list = [
            products_schemas.Product.model_validate(p) for p in products
        ]

        return schemas.PublicSellerWithDetails(
            **seller_schema.model_dump(),
            shop_points=shop_points_as_schemas,
            products=products_schemas_list,
        )

    @handle_alchemy_error
    async def update_seller(
        self, session: AsyncSession, seller_id: int, seller_data: schemas.SellerUpdate, current_seller: Seller
    ) -> schemas.Seller:
        """Update seller with validation"""
        # Check ownership
        await verify_seller_owns_resource(seller_id, current_seller)
        
        updated_seller = await self.service.update_seller(
            session, seller_id, seller_data
        )
        await session.commit()
        return schemas.Seller.model_validate(updated_seller)

    @handle_alchemy_error
    async def delete_seller(self, session: AsyncSession, seller_id: int, current_seller: Seller) -> None:
        """Delete seller"""
        # Check ownership
        await verify_seller_owns_resource(seller_id, current_seller)
        
        await self.service.delete_seller(session, seller_id)
        await session.commit()

    async def get_sellers_summary(self, session: AsyncSession) -> schemas.SellerSummary:
        """Get sellers summary statistics"""
        summary = await self.service.get_sellers_summary(session)
        return summary

    async def get_sellers_by_ids(
        self, session: AsyncSession, seller_ids: List[int]
    ) -> List[schemas.PublicSeller]:
        """Get sellers by list of IDs"""
        sellers = await self.service.get_sellers_by_ids(session, seller_ids)
        return [schemas.PublicSeller.model_validate(seller) for seller in sellers]

    @handle_alchemy_error
    async def upload_seller_image(
        self,
        session: AsyncSession,
        seller_id: int,
        file: UploadFile,
        order: int = 0,
        current_seller: Seller = None
    ) -> schemas.SellerImage:
        """Upload image for seller"""
        # Check ownership
        if current_seller:
            await verify_seller_owns_resource(seller_id, current_seller)
        
        return await self.image_manager.upload_and_create_image_record(
            session=session,
            entity_id=seller_id,
            file=file,
            prefix="sellers",
            order=order,
            entity_name="seller",
            get_entity_func=self.service.get_seller_by_id,
            create_image_func=self.service.create_seller_image,
            schema_class=schemas.SellerImage
        )

    @handle_alchemy_error
    async def upload_seller_images(
        self,
        session: AsyncSession,
        seller_id: int,
        files: list[UploadFile],
        start_order: int = 0,
        current_seller: Seller = None
    ) -> list[schemas.SellerImage]:
        """Upload multiple images for seller"""
        # Check ownership
        if current_seller:
            await verify_seller_owns_resource(seller_id, current_seller)
        
        return await self.image_manager.upload_multiple_and_create_image_records(
            session=session,
            entity_id=seller_id,
            files=files,
            prefix="sellers",
            start_order=start_order,
            entity_name="seller",
            get_entity_func=self.service.get_seller_by_id,
            create_image_func=self.service.create_seller_image,
            schema_class=schemas.SellerImage
        )

    @handle_alchemy_error
    async def delete_seller_image(
        self,
        session: AsyncSession,
        image_id: int,
        current_seller: Seller = None
    ) -> None:
        """Delete seller image"""
        # Check ownership
        if current_seller:
            image = await self.service.get_seller_image_by_id(session, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Seller image not found"
                )
            await verify_seller_owns_resource(image.seller_id, current_seller)
        
        await self.image_manager.delete_image_record(
            session=session,
            image_id=image_id,
            entity_name="seller",
            get_image_func=self.service.get_seller_image_by_id,
            delete_image_func=self.service.delete_seller_image
        )

    @handle_alchemy_error
    async def update_seller_firebase_token(
        self,
        session: AsyncSession,
        seller_id: int,
        firebase_token: str
    ) -> schemas.Seller:
        """Update seller firebase_token"""
        updated_seller = await self.service.update_seller_firebase_token(
            session, seller_id, firebase_token
        )
        await session.commit()
        return schemas.Seller.model_validate(updated_seller)

    async def get_seller_firebase_token(
        self,
        session: AsyncSession,
        seller_id: int
    ) -> Optional[str]:
        """Get seller firebase_token"""
        return await self.service.get_seller_firebase_token(session, seller_id)

    async def send_notification_to_seller(
        self,
        session: AsyncSession,
        seller_id: int,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> None:
        """Send push notification to seller"""
        from logger import get_sync_logger
        logger = get_sync_logger(__name__)
        
        try:
            seller = await self.service.get_seller_by_id(session, seller_id)
            if not seller or not seller.firebase_token:
                logger.info(
                    "Skipping notification: seller not found or no firebase token",
                    extra={"seller_id": seller_id}
                )
                return
            
            await self.notification_manager.send_notification(
                token=seller.firebase_token,
                title=title,
                body=body,
                data=data or {}
            )
            
            logger.info(
                "Notification sent to seller",
                extra={"seller_id": seller_id, "title": title}
            )
        except Exception as e:
            logger.error(
                f"Failed to send notification to seller: {str(e)}",
                extra={
                    "seller_id": seller_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            # Don't raise exception - notification failure shouldn't break business logic
