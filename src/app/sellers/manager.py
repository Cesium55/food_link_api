from typing import List
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
from fastapi import UploadFile


class SellersManager:
    """Manager for seller business logic and validation"""

    def __init__(self):
        self.service = SellersService()
        self.shop_points_service = ShopPointsService()
        self.products_service = ProductsService()
        self.password_utils = PasswordUtils()
        self.auth_service = AuthService()
        self.image_manager = ImageManager()

    @handle_alchemy_error
    async def create_seller(
        self,
        session: AsyncSession,
        seller_data: schemas.SellerCreate,
        current_user: User,
    ) -> Seller:
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

        return seller

    async def get_sellers(self, session: AsyncSession) -> List[schemas.PublicSeller]:
        """Get list of sellers"""
        sellers = await self.service.get_sellers(session)
        return [schemas.PublicSeller.model_validate(seller) for seller in sellers]

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
        self, session: AsyncSession, seller_id: int, seller_data: schemas.SellerUpdate
    ) -> schemas.Seller:
        """Update seller with validation"""
        updated_seller = await self.service.update_seller(
            session, seller_id, seller_data
        )
        await session.commit()
        return schemas.Seller.model_validate(updated_seller)

    @handle_alchemy_error
    async def delete_seller(self, session: AsyncSession, seller_id: int) -> None:
        """Delete seller"""
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
        order: int = 0
    ) -> schemas.SellerImage:
        """Upload image for seller"""
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
        start_order: int = 0
    ) -> list[schemas.SellerImage]:
        """Upload multiple images for seller"""
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
        image_id: int
    ) -> None:
        """Delete seller image"""
        await self.image_manager.delete_image_record(
            session=session,
            image_id=image_id,
            entity_name="seller",
            get_image_func=self.service.get_seller_image_by_id,
            delete_image_func=self.service.delete_seller_image
        )
