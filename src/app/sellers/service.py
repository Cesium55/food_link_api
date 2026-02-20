from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, insert
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.sellers import schemas
from app.sellers.models import Seller, SellerImage, SellerRegistrationRequest
from app.shop_points.models import ShopPoint
from app.products.models import Product
from app.auth.models import User
from app.auth.password_utils import PasswordUtils


class SellersService:
    """Service for working with sellers"""

    def __init__(self):
        self.password_utils = PasswordUtils()

    async def check_user_exists_by_email(self, session: AsyncSession, email: str) -> bool:
        """Check if user already exists by email"""
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def check_user_exists_by_phone(self, session: AsyncSession, phone: str) -> bool:
        """Check if user already exists by phone"""
        if not phone:
            return False
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none() is not None

    async def create_seller(
        self, session: AsyncSession, schema: schemas.SellerCreate, user_id: int, email: str
    ) -> Seller:
        """Create a new seller with user validation"""
        # Создаем продавца
        result = await session.execute(
            insert(Seller)
            .values(
                full_name=schema.full_name,
                short_name=schema.short_name,
                description=schema.description,
                inn=schema.inn,
                is_IP=schema.is_IP,
                ogrn=schema.ogrn,
                master_id=user_id,  # Автоматически берем из user_id
                email=email,  # Email пользователя
                phone=None,  # Пока не задано
                status=0,
                verification_level=0,
                registration_doc_url=""  # Пустая строка вместо None
            )
            .returning(Seller)
        )
        created_seller = result.scalar_one()
        # Подгружаем images для возврата
        result = await session.execute(
            select(Seller)
            .where(Seller.id == created_seller.id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one()

    async def get_seller_by_id(
        self, session: AsyncSession, seller_id: int
    ) -> Optional[Seller]:
        """Get seller by ID"""
        result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one_or_none()

    async def get_seller_by_master_id(
        self, session: AsyncSession, master_id: int
    ) -> Optional[Seller]:
        """Get seller by master_id (user_id)"""
        result = await session.execute(
            select(Seller)
            .where(Seller.master_id == master_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one_or_none()


    async def get_sellers(self, session: AsyncSession) -> List[Seller]:
        """Get list of all sellers"""
        result = await session.execute(
            select(Seller)
            .options(selectinload(Seller.images))
            .order_by(Seller.full_name)
        )
        return result.scalars().all()

    async def get_sellers_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        status: Optional[int] = None, verification_level: Optional[int] = None
    ) -> tuple[List[Seller], int]:
        """Get paginated list of sellers with total count and optional filters"""
        # Build base query with filters
        base_query = select(Seller)
        
        # Apply filters
        conditions = []
        if status is not None:
            conditions.append(Seller.status == status)
        if verification_level is not None:
            conditions.append(Seller.verification_level == verification_level)
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # Get total count with filters
        count_query = select(func.count(Seller.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results with filters
        offset = (page - 1) * page_size
        result = await session.execute(
            base_query
            .options(selectinload(Seller.images))
            .order_by(Seller.full_name)
            .limit(page_size)
            .offset(offset)
        )
        sellers = result.scalars().all()
        
        return sellers, total_count

    async def get_seller_with_shop_points(
        self, session: AsyncSession, seller_id: int
    ) -> Optional[Seller]:
        """Get seller with shop points"""
        result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one_or_none()

    async def get_seller_with_details(
        self, session: AsyncSession, seller_id: int
    ) -> Optional[Seller]:
        """Get seller with full information"""
        result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one_or_none()

    async def update_seller(
        self, session: AsyncSession, seller_id: int, schema: schemas.SellerUpdate
    ) -> Seller:
        """Update seller"""
        # Prepare update data
        update_data = {}
        if schema.full_name is not None:
            update_data['full_name'] = schema.full_name
        if schema.short_name is not None:
            update_data['short_name'] = schema.short_name
        if schema.description is not None:
            update_data['description'] = schema.description
        if schema.inn is not None:
            update_data['inn'] = schema.inn
        if schema.is_IP is not None:
            update_data['is_IP'] = schema.is_IP
        if schema.ogrn is not None:
            update_data['ogrn'] = schema.ogrn
        if schema.email is not None:
            update_data['email'] = schema.email
        if schema.phone is not None:
            update_data['phone'] = schema.phone
        # master_id не обновляется - он привязан к пользователю
        if schema.status is not None:
            update_data['status'] = schema.status
        if schema.verification_level is not None:
            update_data['verification_level'] = schema.verification_level
        if schema.registration_doc_url is not None:
            update_data['registration_doc_url'] = schema.registration_doc_url

        # Update seller
        if update_data:
            await session.execute(
                update(Seller)
                .where(Seller.id == seller_id)
                .values(**update_data)
            )
        
        # Return updated seller with images loaded
        result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one()

    async def delete_seller(
        self, session: AsyncSession, seller_id: int
    ) -> None:
        """Delete seller"""
        await session.execute(
            delete(Seller).where(Seller.id == seller_id)
        )

    async def get_sellers_summary(
        self, session: AsyncSession
    ) -> schemas.SellerSummary:
        """Get summary statistics for sellers"""
        # Total number of sellers
        total_sellers_result = await session.execute(
            select(func.count(Seller.id))
        )
        total_sellers = total_sellers_result.scalar() or 0

        # Total number of products from all sellers
        total_products_result = await session.execute(
            select(func.count(Product.id))
        )
        total_products = total_products_result.scalar() or 0

        # Average number of products per seller
        avg_products_per_seller = (
            total_products / total_sellers if total_sellers > 0 else 0.0
        )

        return schemas.SellerSummary(
            total_sellers=total_sellers,
            total_products=total_products,
            avg_products_per_seller=avg_products_per_seller
        )

    async def get_sellers_by_ids(
        self, session: AsyncSession, seller_ids: List[int]
    ) -> List[Seller]:
        """Get sellers by list of IDs"""
        result = await session.execute(
            select(Seller)
            .where(Seller.id.in_(seller_ids))
            .options(selectinload(Seller.images))
            .order_by(Seller.full_name)
        )
        return result.scalars().all()

    async def create_seller_image(
        self, session: AsyncSession, seller_id: int, s3_path: str, order: int = 0
    ) -> SellerImage:
        """Create a new seller image"""
        result = await session.execute(
            insert(SellerImage)
            .values(
                seller_id=seller_id,
                path=s3_path,
                order=order
            )
            .returning(SellerImage)
        )
        return result.scalar_one()

    async def get_seller_image_by_id(
        self, session: AsyncSession, image_id: int
    ) -> Optional[SellerImage]:
        """Get seller image by ID"""
        result = await session.execute(
            select(SellerImage).where(SellerImage.id == image_id)
        )
        return result.scalar_one_or_none()

    async def delete_seller_image(
        self, session: AsyncSession, image_id: int
    ) -> None:
        """Delete seller image"""
        await session.execute(
            delete(SellerImage).where(SellerImage.id == image_id)
        )

    async def update_seller_firebase_token(
        self, session: AsyncSession, seller_id: int, firebase_token: str
    ) -> Seller:
        """Update seller firebase_token field"""
        await session.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(firebase_token=firebase_token)
        )
        
        # Return updated seller with images loaded
        result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .options(selectinload(Seller.images))
        )
        return result.scalar_one()

    async def get_seller_firebase_token(
        self, session: AsyncSession, seller_id: int
    ) -> Optional[str]:
        """Get seller firebase_token"""
        result = await session.execute(
            select(Seller.firebase_token).where(Seller.id == seller_id)
        )
        return result.scalar_one_or_none()

    async def get_registration_request_by_user_id(
        self, session: AsyncSession, user_id: int
    ) -> Optional[SellerRegistrationRequest]:
        """Get seller registration request by user ID."""
        result = await session.execute(
            select(SellerRegistrationRequest).where(
                SellerRegistrationRequest.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def create_registration_request(
        self,
        session: AsyncSession,
        user_id: int,
        schema: schemas.SellerRegistrationRequestCreate,
    ) -> SellerRegistrationRequest:
        """Create seller registration request for user."""
        payload = schema.model_dump(exclude_unset=True)
        result = await session.execute(
            insert(SellerRegistrationRequest)
            .values(
                user_id=user_id,
                status=schemas.SellerRegistrationRequestStatus.PENDING.value,
                **payload,
            )
            .returning(SellerRegistrationRequest)
        )
        return result.scalar_one()

    async def update_registration_request(
        self,
        session: AsyncSession,
        user_id: int,
        schema: schemas.SellerRegistrationRequestUpdate,
    ) -> Optional[SellerRegistrationRequest]:
        """Update seller registration request for user."""
        payload = schema.model_dump(exclude_unset=True)
        if payload:
            await session.execute(
                update(SellerRegistrationRequest)
                .where(SellerRegistrationRequest.user_id == user_id)
                .values(**payload)
            )
        return await self.get_registration_request_by_user_id(session, user_id)

    async def delete_registration_request(
        self, session: AsyncSession, user_id: int
    ) -> None:
        """Delete seller registration request for user."""
        await session.execute(
            delete(SellerRegistrationRequest).where(
                SellerRegistrationRequest.user_id == user_id
            )
        )
