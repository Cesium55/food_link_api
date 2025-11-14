from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.offers import schemas
from app.offers.service import OffersService
from app.products import schemas as products_schemas
from app.products.service import ProductsService
from app.shop_points.service import ShopPointsService
from utils.errors_handler import handle_alchemy_error


class OffersManager:
    """Manager for offers business logic and validation"""

    def __init__(self):
        self.service = OffersService()
        self.products_service = ProductsService()
        self.shop_points_service = ShopPointsService()

    @handle_alchemy_error
    async def create_offer(
        self, 
        session: AsyncSession, 
        offer_data: schemas.OfferCreate
    ) -> schemas.Offer:
        """Create a new offer with validation"""
        # Validate product exists
        product = await self.products_service.get_product_by_id(session, offer_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {offer_data.product_id} not found"
            )

        # Validate shop point exists
        shop_point = await self.shop_points_service.get_shop_point_by_id(session, offer_data.shop_id)
        if not shop_point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shop point with id {offer_data.shop_id} not found"
            )

        # Create offer
        offer = await self.service.create_offer(session, offer_data)
        await session.commit()
        
        return schemas.Offer.model_validate(offer)

    async def get_offers(
        self, session: AsyncSession
    ) -> List[schemas.Offer]:
        """Get list of offers"""
        offers = await self.service.get_offers(session)
        return [schemas.Offer.model_validate(offer) for offer in offers]

    async def get_offers_with_products(
        self, session: AsyncSession
    ) -> List[schemas.OfferWithProduct]:
        """Get list of offers with product information"""
        offers = await self.service.get_offers_with_products(session)
        result = []
        for offer in offers:
            offer_schema = schemas.Offer.model_validate(offer)
            product_schema = products_schemas.Product.model_validate(offer.product)
            result.append(schemas.OfferWithProduct(
                **offer_schema.model_dump(),
                product=product_schema
            ))
        return result

    async def get_offer_by_id(
        self, session: AsyncSession, offer_id: int
    ) -> schemas.Offer:
        """Get offer by ID"""
        offer = await self.service.get_offer_by_id(session, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )
        return schemas.Offer.model_validate(offer)

    async def get_offer_with_product(
        self, session: AsyncSession, offer_id: int
    ) -> schemas.OfferWithProduct:
        """Get offer with product information"""
        offer = await self.service.get_offer_with_product(session, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )
        
        offer_schema = schemas.Offer.model_validate(offer)
        product_schema = products_schemas.Product.model_validate(offer.product)
        
        return schemas.OfferWithProduct(
            **offer_schema.model_dump(),
            product=product_schema
        )

    @handle_alchemy_error
    async def update_offer(
        self, 
        session: AsyncSession,
        offer_id: int, 
        offer_data: schemas.OfferUpdate
    ) -> schemas.Offer:
        """Update offer with validation"""
        # Check if offer exists
        existing_offer = await self.service.get_offer_by_id(session, offer_id)
        if not existing_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )

        # Update offer
        updated_offer = await self.service.update_offer(session, offer_id, offer_data)
        await session.commit()
        
        return schemas.Offer.model_validate(updated_offer)

    @handle_alchemy_error
    async def delete_offer(
        self, session: AsyncSession, offer_id: int
    ) -> None:
        """Delete offer"""
        # Check if offer exists
        existing_offer = await self.service.get_offer_by_id(session, offer_id)
        if not existing_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offer with id {offer_id} not found"
            )

        await self.service.delete_offer(session, offer_id)
        await session.commit()
