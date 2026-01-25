from typing import List, Dict, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from datetime import datetime, timezone, timedelta
from app.purchases import schemas
from app.purchases.service import PurchasesService
from app.purchases.models import PurchaseStatus, Purchase, PurchaseOffer
from app.offers.service import OffersService
from app.offers.manager import OffersManager
from app.offers import schemas as offers_schemas
from app.offers.models import Offer
from app.shop_points.models import ShopPoint
from app.sellers.manager import SellersManager
from app.sellers.service import SellersService
from app.sellers.models import Seller
from app.shop_points.models import ShopPoint
from app.offers.models import Offer
from sqlalchemy.orm import selectinload
from app.payments.manager import PaymentsManager
from utils.errors_handler import handle_alchemy_error
from app.purchases.tasks import check_purchase_expiration
from config import settings
from app.auth.jwt_utils import JWTUtils
from app.payments.models import PaymentStatus
from utils.pagination import PaginatedResponse
from logger import get_sync_logger
from utils.debug_logger import hard_log

logger = get_sync_logger(__name__)


class PurchasesManager:
    """Manager for purchases business logic and validation"""

    def __init__(self):
        self.service = PurchasesService()
        self.offers_service = OffersService()
        self.offers_manager = OffersManager()
        self.payments_manager = PaymentsManager()
        self.jwt_utils = JWTUtils()
        self.sellers_service = SellersService()
        self.sellers_manager = SellersManager()

    @handle_alchemy_error
    async def create_purchase(
        self,
        session: AsyncSession,
        user_id: int,
        purchase_data: schemas.PurchaseCreate,
        base_url: str
    ) -> schemas.PurchaseWithOffers:
        """
        Create a new purchase with full validation.
        All offers must be valid, otherwise an error is raised.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        hard_log(f"create_purchase START for user_id={user_id}, offers={len(purchase_data.offers)}", "MANAGER")
        
        if not purchase_data.offers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase must contain at least one offer"
            )

        # Check if user already has a pending purchase (with lock to prevent race conditions)
        hard_log(f"Checking for existing pending purchase for user_id={user_id}", "MANAGER")
        existing_pending = await self.service.get_pending_purchase_by_user(session, user_id, for_update=True)
        hard_log(f"Existing pending check complete: found={existing_pending is not None}", "MANAGER")
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a pending purchase. Only one pending purchase is allowed at a time."
            )

        # Get all offer IDs to lock them at once (prevents deadlocks)
        all_offer_ids = [offer.offer_id for offer in purchase_data.offers]
        hard_log(f"Locking offers: {all_offer_ids}", "MANAGER")
        locked_offers = await self.offers_service.get_offers_by_ids_for_update(
            session, all_offer_ids
        )
        hard_log(f"Offers locked successfully: {len(locked_offers)} offers", "MANAGER")
        locked_offers_dict = {offer.id: offer for offer in locked_offers}
        
        purchase_offers_data = []
        total_cost = Decimal('0.00')
        successful_offer_ids = []
        
        # Validate all offers before creating purchase
        for offer_request in purchase_data.offers:
            offer_id = offer_request.offer_id
            requested_quantity = offer_request.quantity
            
            # Check if offer exists
            offer = locked_offers_dict.get(offer_id)
            if not offer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Offer {offer_id} not found"
                )
            
            # Check if offer is expired
            if offer.expires_date:
                now = datetime.now(timezone.utc)
                if offer.expires_date < now:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Offer {offer_id} has expired"
                    )
            
            # Check availability
            available_count = (offer.count or 0) - (offer.reserved_count or 0)
            if available_count < requested_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient quantity for offer {offer_id}. Available: {available_count}, requested: {requested_quantity}"
                )
            
            # All validations passed, calculate price and add to purchase
            cost_per_item = self.offers_manager.calculate_dynamic_price(offer)
            if cost_per_item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot calculate price for offer {offer_id}. Offer may be expired or missing required data."
                )
            total_cost += cost_per_item * requested_quantity
            
            purchase_offers_data.append({
                "offer_id": offer_id,
                "quantity": requested_quantity,
                "cost_at_purchase": cost_per_item,
            })
            
            successful_offer_ids.append(offer_id)
        
        # Update reserved_count for all offers
        hard_log(f"Updating reserved counts for {len(purchase_offers_data)} offers", "MANAGER")
        for offer_data in purchase_offers_data:
            await self.offers_service.update_offer_reserved_count(
                session, offer_data["offer_id"], offer_data["quantity"]
            )
        
        # Create purchase
        hard_log(f"Creating purchase for user_id={user_id}, total_cost={total_cost}", "MANAGER")
        purchase = await self.service.create_purchase(session, user_id, total_cost)
        hard_log(f"Purchase created with id={purchase.id}", "MANAGER")
        
        # Create purchase offers
        purchase_offers = await self.service.create_purchase_offers(
            session, purchase.id, purchase_offers_data
        )
        hard_log(f"Purchase offers created: {len(purchase_offers)} offers", "MANAGER")
        
        # Create offer results (all offers were successful in this method)
        offer_results_data = []
        for offer_request in purchase_data.offers:
            offer_results_data.append({
                "offer_id": offer_request.offer_id,
                "status": schemas.OfferProcessingStatus.SUCCESS.value,
                "requested_quantity": offer_request.quantity,
                "processed_quantity": offer_request.quantity,
                "message": f"Successfully processed {offer_request.quantity} items for offer {offer_request.offer_id}"
            })
        
        await self.service.create_purchase_offer_results(session, purchase.id, offer_results_data)
        
        # Create payment for this purchase (in the same transaction)
        hard_log(f"Creating payment for purchase_id={purchase.id}", "MANAGER")
        await self.payments_manager.create_payment_for_purchase(
            session, purchase.id, purchase.total_cost, base_url
        )
        hard_log(f"Payment created successfully", "MANAGER")
        
        
        
        # Send notifications to sellers about reserved items
        # await self._notify_sellers_about_reservation(session, purchase.id)
        
        # Schedule Celery task to check purchase expiration
        hard_log(f"Scheduling Celery task", "MANAGER")
        try:
            check_purchase_expiration.apply_async(
                args=[purchase.id],
                countdown=settings.purchase_expiration_seconds
            )
        except Exception as e:
            # Log error but don't fail the purchase creation
            hard_log(f"Failed to schedule Celery task: {e}", "MANAGER")
        
        # Reload offers to get updated reserved_count values for response
        hard_log(f"Reloading offers", "MANAGER")
        updated_offers = await self.offers_service.get_offers_by_ids(session, successful_offer_ids)
        offers_dict = {offer.id: offer for offer in updated_offers}
        
        # Load offer results
        offer_results = await self.service.get_purchase_offer_results_by_purchase_id(session, purchase.id)


        # Commit transaction (releases locks)
        hard_log(f"Committing transaction", "MANAGER")
        await session.commit()
        hard_log(f"Transaction committed successfully", "MANAGER")
        
        # Convert purchase to schema
        hard_log(f"create_purchase COMPLETE for purchase_id={purchase.id}", "MANAGER")
        return self._purchase_to_schema_with_offers(purchase, purchase_offers, offers_dict, offer_results)

    @handle_alchemy_error
    async def create_purchase_with_partial_success(
        self,
        session: AsyncSession,
        user_id: int,
        purchase_data: schemas.PurchaseCreate,
        base_url: str
    ) -> schemas.PurchaseCreateResponse:
        """
        Create a new purchase with partial success support.
        Processes each offer individually and collects results.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        hard_log(f"create_purchase_with_partial_success START - user_id={user_id}, offers={len(purchase_data.offers)}", "MANAGER")
        
        if not purchase_data.offers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase must contain at least one offer"
            )

        # Check if user already has a pending purchase (with lock to prevent race conditions)
        hard_log(f"Checking for existing pending purchase (with lock)...", "MANAGER")
        existing_pending = await self.service.get_pending_purchase_by_user(session, user_id, for_update=True)
        hard_log(f"Existing pending check complete: found={existing_pending is not None}", "MANAGER")
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a pending purchase. Only one pending purchase is allowed at a time."
            )

        # Process each offer individually
        offer_results: List[schemas.OfferProcessingResult] = []
        purchase_offers_data = []
        total_cost = Decimal('0.00')
        successful_offer_ids = []
        
        # Get all offer IDs to lock them at once (prevents deadlocks)
        all_offer_ids = [offer.offer_id for offer in purchase_data.offers]
        hard_log(f"Locking offers: {all_offer_ids}", "MANAGER-PARTIAL")
        locked_offers = await self.offers_service.get_offers_by_ids_for_update(
            session, all_offer_ids
        )
        hard_log(f"Offers locked: {len(locked_offers)} offers", "MANAGER-PARTIAL")
        locked_offers_dict = {offer.id: offer for offer in locked_offers}
        
        # Process each offer from the request
        for offer_request in purchase_data.offers:
            offer_id = offer_request.offer_id
            requested_quantity = offer_request.quantity
            result = schemas.OfferProcessingResult(
                offer_id=offer_id,
                status=schemas.OfferProcessingStatus.SUCCESS,
                requested_quantity=requested_quantity
            )
            
            # Check if offer exists
            offer = locked_offers_dict.get(offer_id)
            if not offer:
                result.status = schemas.OfferProcessingStatus.NOT_FOUND
                result.message = f"Offer {offer_id} not found"
                offer_results.append(result)
                continue
            
            # Check if offer is expired
            if offer.expires_date:
                # Compare with timezone-aware datetime
                now = datetime.now(timezone.utc)
                if offer.expires_date < now:
                    result.status = schemas.OfferProcessingStatus.EXPIRED
                    result.message = f"Offer {offer_id} has expired"
                    offer_results.append(result)
                    continue
            
            # Check availability
            available_count = (offer.count or 0) - (offer.reserved_count or 0)
            if available_count <= 0:
                result.status = schemas.OfferProcessingStatus.INSUFFICIENT_QUANTITY
                result.available_quantity = 0
                result.message = f"Offer {offer_id} is not available"
                offer_results.append(result)
                continue
            
            # Determine how much we can actually process
            processed_quantity = min(requested_quantity, available_count)
            result.processed_quantity = processed_quantity
            
            if processed_quantity < requested_quantity:
                # Partial success - we take what's available
                result.status = schemas.OfferProcessingStatus.INSUFFICIENT_QUANTITY
                result.available_quantity = available_count
                result.message = f"Only {processed_quantity} items available for offer {offer_id}, requested {requested_quantity}"
            else:
                # Full success
                result.status = schemas.OfferProcessingStatus.SUCCESS
                result.message = f"Successfully processed {processed_quantity} items for offer {offer_id}"
            
            # Add to purchase if we can process at least something
            if processed_quantity > 0:
                cost_per_item = self.offers_manager.calculate_dynamic_price(offer)
                if cost_per_item is None:
                    # Skip this offer if price cannot be calculated
                    result.status = schemas.OfferProcessingStatus.ERROR
                    result.message = f"Cannot calculate price for offer {offer_id}. Offer may be expired or missing required data."
                    offer_results.append(result)
                    continue
                
                total_cost += cost_per_item * processed_quantity
                
                purchase_offers_data.append({
                    "offer_id": offer_id,
                    "quantity": processed_quantity,
                    "cost_at_purchase": cost_per_item,
                })
                
                successful_offer_ids.append(offer_id)
            
            offer_results.append(result)
        
        # Check if we have at least one successful offer
        if not purchase_offers_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No offers could be processed. All offers failed validation."
            )
        
        # Update reserved_count for successful offers
        hard_log(f"Updating reserved counts for {len(purchase_offers_data)} offers", "MANAGER-PARTIAL")
        for offer_data in purchase_offers_data:
            await self.offers_service.update_offer_reserved_count(
                session, offer_data["offer_id"], offer_data["quantity"]
            )
        hard_log(f"Reserved counts updated", "MANAGER-PARTIAL")
        
        # Create purchase
        hard_log(f"Creating purchase for user_id={user_id}, total_cost={total_cost}", "MANAGER-PARTIAL")
        purchase = await self.service.create_purchase(session, user_id, total_cost)
        hard_log(f"Purchase created with id={purchase.id}", "MANAGER-PARTIAL")
        
        # Create purchase offers
        purchase_offers = await self.service.create_purchase_offers(
            session, purchase.id, purchase_offers_data
        )
        
        # Save offer results to database
        offer_results_data = []
        for result in offer_results:
            offer_results_data.append({
                "offer_id": result.offer_id,
                "status": result.status.value,
                "requested_quantity": result.requested_quantity,
                "processed_quantity": result.processed_quantity,
                "available_quantity": result.available_quantity,
                "message": result.message
            })
        
        await self.service.create_purchase_offer_results(session, purchase.id, offer_results_data)
        
        # Create payment for this purchase (in the same transaction)
        hard_log(f"Creating payment for purchase_id={purchase.id}", "MANAGER-PARTIAL")
        await self.payments_manager.create_payment_for_purchase(
            session, purchase.id, total_cost, base_url
        )
        hard_log(f"Payment created", "MANAGER-PARTIAL")
        
        # Commit transaction (releases locks)
        hard_log(f"Committing transaction", "MANAGER-PARTIAL")
        await session.commit()
        hard_log(f"Transaction committed", "MANAGER-PARTIAL")
        
        # Send notifications to sellers about reserved items
        await self._notify_sellers_about_reservation(session, purchase.id)
        
        # Schedule Celery task to check purchase expiration
        try:
            check_purchase_expiration.apply_async(
                args=[purchase.id],
                countdown=settings.purchase_expiration_seconds
            )
        except Exception as e:
            # Log error but don't fail the purchase creation
            print(f"Warning: Failed to schedule Celery task for purchase {purchase.id}: {e}")
        
        # Reload offers to get updated reserved_count values for response
        updated_offers = await self.offers_service.get_offers_by_ids(session, successful_offer_ids)
        offers_dict = {offer.id: offer for offer in updated_offers}
        
        # Load offer results from database
        saved_offer_results = await self.service.get_purchase_offer_results_by_purchase_id(session, purchase.id)
        
        # Convert purchase to schema
        purchase_schema = self._purchase_to_schema_with_offers(purchase, purchase_offers, offers_dict, saved_offer_results)
        
        # Count successful and failed offers
        # Success includes both full success and partial success (when processed_quantity > 0)
        total_processed = sum(1 for r in offer_results if r.processed_quantity and r.processed_quantity > 0)
        total_failed = len(offer_results) - total_processed
        
        return schemas.PurchaseCreateResponse(
            purchase=purchase_schema,
            offer_results=purchase_schema.offer_results,
            total_processed=total_processed,
            total_failed=total_failed
        )

    async def get_purchase_by_id(
        self, session: AsyncSession, purchase_id: int
    ) -> schemas.PurchaseWithOffers:
        """Get purchase by ID"""
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        # Get purchase offers
        purchase_offers = await self.service.get_purchase_offers_by_purchase_id(session, purchase_id)
        
        # Get all offer IDs from purchase_offers
        offer_ids = [po.offer_id for po in purchase_offers]
        
        # Load offers
        offers = await self.offers_service.get_offers_by_ids(session, offer_ids)
        offers_dict = {offer.id: offer for offer in offers}
        
        # Load offer results
        offer_results = await self.service.get_purchase_offer_results_by_purchase_id(session, purchase_id)
        
        return self._purchase_to_schema_with_offers(purchase, purchase_offers, offers_dict, offer_results)

    async def get_pending_purchase_by_user(
        self, session: AsyncSession, user_id: int
    ) -> schemas.PurchaseWithOffers:
        """Get pending purchase by user ID"""
        purchase = await self.service.get_pending_purchase_by_user(session, user_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending purchase found for this user"
            )
        
        # Get purchase offers
        purchase_offers = await self.service.get_purchase_offers_by_purchase_id(session, purchase.id)
        
        # Get all offer IDs from purchase_offers
        offer_ids = [po.offer_id for po in purchase_offers]
        
        # Load offers
        offers = await self.offers_service.get_offers_by_ids(session, offer_ids)
        offers_dict = {offer.id: offer for offer in offers}
        
        # Load offer results
        offer_results = await self.service.get_purchase_offer_results_by_purchase_id(session, purchase.id)
        
        return self._purchase_to_schema_with_offers(purchase, purchase_offers, offers_dict, offer_results)

    async def get_purchases_by_user(
        self, session: AsyncSession, user_id: int
    ) -> List[schemas.Purchase]:
        """Get purchases by user ID"""
        purchases = await self.service.get_purchases_by_user(session, user_id)
        return [schemas.Purchase.model_validate(purchase) for purchase in purchases]

    async def get_purchases_paginated(
        self, session: AsyncSession, page: int, page_size: int,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> PaginatedResponse[schemas.Purchase]:
        """Get paginated list of purchases with optional filters"""
        purchases, total_count = await self.service.get_purchases_paginated(
            session, page, page_size, status, user_id,
            min_created_at, max_created_at, min_updated_at, max_updated_at
        )
        purchase_schemas = [
            schemas.Purchase.model_validate(purchase) for purchase in purchases
        ]
        return PaginatedResponse.create(
            items=purchase_schemas,
            page=page,
            page_size=page_size,
            total_items=total_count
        )
    
    async def get_purchases(
        self, session: AsyncSession,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> PaginatedResponse[schemas.Purchase]:
        """Get paginated list of purchases with optional filters"""
        purchases = await self.service.get_purchases(
            session, status, user_id,
            min_created_at, max_created_at, min_updated_at, max_updated_at
        )
        purchase_schemas = [
            schemas.Purchase.model_validate(purchase) for purchase in purchases
        ]
        return purchase_schemas

    @handle_alchemy_error
    async def update_purchase_status(
        self,
        session: AsyncSession,
        purchase_id: int,
        status_data: schemas.PurchaseUpdate
    ) -> schemas.Purchase:
        """Update purchase status"""
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        if status_data.status:
            # Validate status
            valid_statuses = [status.value for status in PurchaseStatus]
            if status_data.status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Valid statuses: {', '.join(valid_statuses)}"
                )
            
            # If cancelling, release reserved items (only if purchase was pending)
            # If purchase was confirmed, reserved_count was already decreased on successful payment
            if status_data.status == PurchaseStatus.CANCELLED.value and purchase.status == PurchaseStatus.PENDING.value:
                # Get purchase offers to release reservations
                purchase_offers = await self.service.get_purchase_offers_by_purchase_id(session, purchase_id)
                
                # Get offer IDs that need to be unlocked
                offer_ids_to_release = [po.offer_id for po in purchase_offers]
                
                # Lock offers before releasing reservations to ensure consistency
                if offer_ids_to_release:
                    await self.offers_service.get_offers_by_ids_for_update(session, offer_ids_to_release)
                
                # Release reservations
                for purchase_offer in purchase_offers:
                    await self.offers_service.update_offer_reserved_count(
                        session, purchase_offer.offer_id, -purchase_offer.quantity
                    )
            
            updated_purchase = await self.service.update_purchase_status(
                session, purchase_id, status_data.status
            )
            await session.commit()
            return schemas.Purchase.model_validate(updated_purchase)
        
        return schemas.Purchase.model_validate(purchase)

    @handle_alchemy_error
    async def delete_purchase(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Delete purchase and release reservations"""
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        # Release reserved items only if purchase was pending
        # If purchase was confirmed, reserved_count was already decreased on successful payment
        if purchase.status == PurchaseStatus.PENDING.value:
            purchase_offers = await self.service.get_purchase_offers_by_purchase_id(session, purchase_id)
            
            # Get offer IDs that need to be unlocked
            offer_ids_to_release = [po.offer_id for po in purchase_offers]
            
            # Lock offers before releasing reservations to ensure consistency
            if offer_ids_to_release:
                await self.offers_service.get_offers_by_ids_for_update(session, offer_ids_to_release)
            
            # Release reservations
            for purchase_offer in purchase_offers:
                await self.offers_service.update_offer_reserved_count(
                    session, purchase_offer.offer_id, -purchase_offer.quantity
                )
        
        await self.service.delete_purchase(session, purchase_id)
        await session.commit()

    async def _notify_sellers_about_reservation(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Send notifications to sellers whose items were reserved in purchase"""
        logger = get_sync_logger(__name__)
        
        try:
            # Get purchase offers
            purchase_offers = await self.service.get_purchase_offers_by_purchase_id(session, purchase_id)
            if not purchase_offers:
                return
            
            # Get offers with shop points
            offer_ids = [po.offer_id for po in purchase_offers]
            offers = await self.offers_service.get_offers_by_ids(session, offer_ids)
            
            # Get shop point IDs
            shop_point_ids = list(set([offer.shop_id for offer in offers]))
            
            # Get shop points with sellers
            from sqlalchemy import select
            shop_points_result = await session.execute(
                select(ShopPoint).where(ShopPoint.id.in_(shop_point_ids))
            )
            shop_points = shop_points_result.scalars().all()
            
            # Group offers by seller
            seller_offers: Dict[int, List[Dict[str, Any]]] = {}
            for offer in offers:
                shop_point = next((sp for sp in shop_points if sp.id == offer.shop_id), None)
                if shop_point:
                    seller_id = shop_point.seller_id
                    if seller_id not in seller_offers:
                        seller_offers[seller_id] = []
                    
                    purchase_offer = next((po for po in purchase_offers if po.offer_id == offer.id), None)
                    if purchase_offer:
                        seller_offers[seller_id].append({
                            "offer_id": offer.id,
                            "quantity": purchase_offer.quantity,
                            "cost": purchase_offer.cost_at_purchase or 0.0
                        })
            
            # Send notifications to each seller
            for seller_id, offers_list in seller_offers.items():
                total_items = sum(offer["quantity"] for offer in offers_list)
                total_cost = sum(offer["quantity"] * offer["cost"] for offer in offers_list)
                
                await self.sellers_manager.send_notification_to_seller(
                    session=session,
                    seller_id=seller_id,
                    title="Items reserved",
                    body=f"{total_items} item(s) reserved in order #{purchase_id}",
                    data={
                        "type": "items_reserved",
                        "purchase_id": str(purchase_id),
                        "total_items": str(total_items),
                        "total_cost": f"{total_cost:.2f}"
                    }
                )
                
                logger.info(
                    "Reservation notification sent to seller",
                    extra={"seller_id": seller_id, "purchase_id": purchase_id, "items_count": total_items}
                )
        except Exception as e:
            logger.error(
                f"Failed to send reservation notifications to sellers: {str(e)}",
                extra={
                    "purchase_id": purchase_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            # Don't raise exception - notification failure shouldn't break purchase creation

    def _purchase_to_schema_with_offers(
        self, 
        purchase: Purchase, 
        purchase_offers: List[PurchaseOffer], 
        offers_dict: Dict[int, Offer],
        offer_results: List = None
    ) -> schemas.PurchaseWithOffers:
        """Convert Purchase model to PurchaseWithOffers schema"""
        from app.purchases.models import PurchaseOfferResult
        
        purchase_schema = schemas.Purchase.model_validate(purchase)
        
        purchase_offers_schemas = []
        for po in purchase_offers:
            offer = offers_dict.get(po.offer_id)
            offer_schema = offers_schemas.Offer.model_validate(offer) if offer else None
            # Use model_validate to automatically include all fields including fulfillment fields
            purchase_offer_schema = schemas.PurchaseOffer.model_validate(po)
            # Set offer separately as it's not part of PurchaseOffer model
            purchase_offer_schema.offer = offer_schema
            purchase_offers_schemas.append(purchase_offer_schema)
        
        # Convert offer_results to schemas
        offer_results_schemas = []
        if offer_results:
            for result in offer_results:
                if isinstance(result, PurchaseOfferResult):
                    offer_results_schemas.append(schemas.OfferProcessingResult(
                        offer_id=result.offer_id,
                        status=schemas.OfferProcessingStatus(result.status),
                        requested_quantity=result.requested_quantity,
                        processed_quantity=result.processed_quantity,
                        available_quantity=result.available_quantity,
                        message=result.message
                    ))
                elif isinstance(result, schemas.OfferProcessingResult):
                    offer_results_schemas.append(result)
        
        # Calculate TTL: time remaining until expiration
        # For pending purchases, TTL is based on expiration time
        # For other statuses, TTL is 0
        ttl = 0
        if purchase.status == PurchaseStatus.PENDING.value:
            now = datetime.now(timezone.utc)
            # Ensure created_at is timezone-aware (should be from DB, but check to be safe)
            created_at = purchase.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            expiration_time = created_at + timedelta(seconds=settings.purchase_expiration_seconds)
            remaining_seconds = int((expiration_time - now).total_seconds())
            ttl = max(0, remaining_seconds)
        
        return schemas.PurchaseWithOffers(
            **purchase_schema.model_dump(),
            purchase_offers=purchase_offers_schemas,
            offer_results=offer_results_schemas,
            ttl=ttl
        )

    @handle_alchemy_error
    async def generate_order_token(
        self, session: AsyncSession, purchase_id: int, user_id: int
    ) -> schemas.OrderTokenResponse:
        """
        Generate JWT token for order information.
        Token can only be generated if the order is paid.
        
        Args:
            session: Database session
            purchase_id: Purchase ID
            user_id: User ID (to verify ownership)
        
        Returns:
            OrderTokenResponse with JWT token and order ID
        
        Raises:
            HTTPException: If purchase not found, doesn't belong to user, or is not paid
        """
        # Get purchase
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        # Check if purchase belongs to user
        if purchase.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this purchase"
            )
        
        # Check if purchase is paid
        payment = await self.payments_manager.service.get_payment_by_purchase_id(
            session, purchase_id
        )
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase has no payment record"
            )
        
        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order token can only be generated for paid orders"
            )
        
        # Generate JWT token with order ID
        token = self.jwt_utils.create_order_token(purchase_id)
        
        return schemas.OrderTokenResponse(
            token=token,
            order_id=purchase_id
        )

    @handle_alchemy_error
    async def verify_purchase_token(
        self, session: AsyncSession, token: str, seller_id: int
    ) -> schemas.PurchaseInfoByTokenResponse:
        """
        Verify purchase token and get purchase information (only seller's items).
        
        Args:
            session: Database session
            token: JWT token containing order ID
            seller_id: Seller ID of current user
        
        Returns:
            PurchaseInfoByTokenResponse with purchase info (only seller's items)
        
        Raises:
            HTTPException: If token is invalid, purchase not found, or not paid
        """
        # Verify token
        payload = self.jwt_utils.verify_order_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        purchase_id = payload.get("order_id")
        if not purchase_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not contain order_id"
            )
        
        # Get purchase
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        # Check if purchase is paid
        payment = await self.payments_manager.service.get_payment_by_purchase_id(
            session, purchase_id
        )
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase has no payment record"
            )
        
        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase is not paid"
            )
        
        # Get purchase offers for this seller only
        purchase_offers = await self.service.get_purchase_offers_by_seller_and_purchase(
            session, purchase_id, seller_id
        )
        
        # Build response items
        items = []
        total_cost = Decimal('0.00')
        
        for po in purchase_offers:
            if po.offer and po.offer.product:
                items.append(schemas.PurchaseOfferForFulfillment(
                    purchase_offer_id=po.offer_id,  # Using offer_id as identifier (composite key with purchase_id)
                    offer_id=po.offer_id,
                    quantity=po.quantity,
                    fulfilled_quantity=po.fulfilled_quantity,
                    fulfillment_status=po.fulfillment_status,
                    product_name=po.offer.product.name,
                    shop_point_id=po.offer.shop_id,
                    cost_at_purchase=po.cost_at_purchase
                ))
                if po.cost_at_purchase:
                    total_cost += po.cost_at_purchase * po.quantity
        
        return schemas.PurchaseInfoByTokenResponse(
            purchase_id=purchase.id,
            status=purchase.status,
            items=items,
            total_cost=total_cost if total_cost > Decimal('0.00') else None
        )

    @handle_alchemy_error
    async def fulfill_order_items(
        self,
        session: AsyncSession,
        purchase_id: int,
        fulfillment_data: schemas.OrderFulfillmentRequest,
        seller_id: int
    ) -> schemas.OrderFulfillmentResponse:
        """
        Fulfill order items for a seller.
        
        Args:
            session: Database session
            purchase_id: Purchase ID
            fulfillment_data: Order fulfillment request with items
            seller_id: Seller ID of current user
        
        Returns:
            OrderFulfillmentResponse with fulfilled items and purchase status
        
        Raises:
            HTTPException: If validation fails
        """
        # Get purchase
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        
        # Check if purchase is paid
        payment = await self.payments_manager.service.get_payment_by_purchase_id(
            session, purchase_id
        )
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase has no payment record"
            )
        
        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase is not paid"
            )
        
        # Get seller's shop point IDs
        from app.shop_points.models import ShopPoint
        from sqlalchemy import select
        shop_points_result = await session.execute(
            select(ShopPoint.id)
            .where(ShopPoint.seller_id == seller_id)
        )
        shop_point_ids = [row[0] for row in shop_points_result.all()]
        
        if not shop_point_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller has no shop points"
            )
        
        # Get offers for these shop points
        from app.offers.models import Offer
        offers_result = await session.execute(
            select(Offer.id)
            .where(Offer.shop_id.in_(shop_point_ids))
        )
        seller_offer_ids = [row[0] for row in offers_result.all()]
        
        if not seller_offer_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller has no offers"
            )
        
        # Validate and update each item
        fulfilled_items = []
        
        for item in fulfillment_data.items:
            # Get purchase offer
            purchase_offer = await session.execute(
                select(PurchaseOffer)
                .where(
                    and_(
                        PurchaseOffer.purchase_id == purchase_id,
                        PurchaseOffer.offer_id == item.offer_id
                    )
                )
            )
            po = purchase_offer.scalar_one_or_none()
            
            if not po:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Purchase offer with offer_id {item.offer_id} not found in purchase {purchase_id}"
                )
            
            # Validate that offer belongs to seller
            if item.offer_id not in seller_offer_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Offer {item.offer_id} does not belong to seller {seller_id}"
                )
            
            # Validate quantity
            if item.fulfilled_quantity > po.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fulfilled quantity {item.fulfilled_quantity} exceeds requested quantity {po.quantity} for offer {item.offer_id}"
                )
            
            # Update fulfillment
            updated_po = await self.service.update_purchase_offer_fulfillment(
                session=session,
                purchase_id=purchase_id,
                offer_id=item.offer_id,
                fulfillment_status=item.status,
                fulfilled_quantity=item.fulfilled_quantity,
                fulfilled_by_seller_id=seller_id,
                unfulfilled_reason=item.unfulfilled_reason
            )
            
            fulfilled_items.append(schemas.PurchaseOfferFulfillmentStatus(
                purchase_offer_id=item.offer_id,  # Using offer_id as identifier (composite key with purchase_id)
                offer_id=item.offer_id,
                status=item.status,
                fulfilled_quantity=item.fulfilled_quantity,
                unfulfilled_reason=item.unfulfilled_reason
            ))
        
        # Check if all offers are fulfilled
        all_fulfilled = await self.service.check_all_offers_fulfilled(session, purchase_id)
        
        if all_fulfilled:
            # Update purchase status to completed
            await self.service.update_purchase_status(session, purchase_id, PurchaseStatus.COMPLETED.value)
            purchase.status = PurchaseStatus.COMPLETED.value
        else:
            # Refresh purchase to get updated status
            purchase = await self.service.get_purchase_by_id(session, purchase_id)
        
        return schemas.OrderFulfillmentResponse(
            fulfilled_items=fulfilled_items,
            purchase_status=purchase.status
        )

