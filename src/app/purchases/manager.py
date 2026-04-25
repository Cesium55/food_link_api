import asyncio
from typing import List, Dict, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from datetime import datetime, timezone, timedelta
from app.purchases import schemas
from app.purchases.service import PurchasesService
from app.purchases.models import PurchaseStatus, Purchase, PurchaseOffer, PurchaseOfferResult
from app.offers.service import OffersService
from app.offers.manager import OffersManager
from app.offers import schemas as offers_schemas
from app.offers.models import Offer
from app.sellers.manager import SellersManager
from app.shop_points.service import ShopPointsService
from app.payments.manager import PaymentsManager
from utils.errors_handler import handle_alchemy_error
from app.purchases.tasks import check_purchase_expiration
from config import settings
from app.auth.jwt_utils import JWTUtils
from app.payments import schemas as payment_schemas
from app.payments.models import PaymentStatus
from utils.pagination import PaginatedResponse
from logger import get_logger

logger = get_logger(__name__)


class PurchasesManager:
    """Manager for purchases business logic and validation"""

    def __init__(self):
        self.service = PurchasesService()
        self.offers_service = OffersService()
        self.offers_manager = OffersManager()
        self.payments_manager = PaymentsManager()
        self.jwt_utils = JWTUtils()
        self.sellers_manager = SellersManager()
        self.shop_points_service = ShopPointsService()

    def _validate_purchase_has_offers(
        self, purchase_data: schemas.PurchaseCreate
    ) -> None:
        if not purchase_data.offers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase must contain at least one offer"
            )

    @handle_alchemy_error
    async def _ensure_no_pending_purchase_for_user(
        self, session: AsyncSession, user_id: int, stage: str
    ) -> None:
        logger.info(
            f"Checking for existing pending purchase for user_id={user_id}",
            extra={"stage": stage},
        )
        existing_pending = await self.service.has_pending_purchase_by_user(
            session, user_id, for_update=True
        )
        logger.info(
            f"Existing pending check complete: found={existing_pending}",
            extra={"stage": stage},
        )
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a pending purchase. Only one pending purchase is allowed at a time."
            )

    @handle_alchemy_error
    async def _lock_requested_offers(
        self, session: AsyncSession, purchase_data: schemas.PurchaseCreate, stage: str
    ) -> Dict[int, Offer]:
        all_offer_ids = [offer.offer_id for offer in purchase_data.offers]
        logger.info(f"Locking offers: {all_offer_ids}", extra={"stage": stage})
        locked_offers = await self.offers_service.get_offers_by_ids_for_update(
            session, all_offer_ids
        )
        logger.info(
            f"Offers locked successfully: {len(locked_offers)} offers",
            extra={"stage": stage},
        )
        return {offer.id: offer for offer in locked_offers}

    @handle_alchemy_error
    async def _reserve_offers(
        self, session: AsyncSession, purchase_offers_data: List[dict], stage: str
    ) -> None:
        logger.info(
            f"Updating reserved counts for {len(purchase_offers_data)} offers",
            extra={"stage": stage},
        )
        for offer_data in purchase_offers_data:
            await self.offers_service.update_offer_reserved_count(
                session, offer_data["offer_id"], offer_data["quantity"]
            )

    @handle_alchemy_error
    async def _release_reservations_for_purchase(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        purchase_offers = await self.service.get_purchase_offers_by_purchase_id(
            session, purchase_id
        )
        offer_ids_to_release = [po.offer_id for po in purchase_offers]
        if offer_ids_to_release:
            await self.offers_service.get_offers_by_ids_for_update(
                session, offer_ids_to_release
            )
        for purchase_offer in purchase_offers:
            await self.offers_service.update_offer_reserved_count(
                session, purchase_offer.offer_id, -purchase_offer.quantity
            )

    @handle_alchemy_error
    async def _load_offers_dict_by_ids(
        self, session: AsyncSession, offer_ids: List[int]
    ) -> Dict[int, Offer]:
        offers = await self.offers_service.get_offers_by_ids(session, offer_ids)
        return {offer.id: offer for offer in offers}

    @handle_alchemy_error
    async def _build_purchase_with_offers_schema(
        self, session: AsyncSession, purchase: Purchase
    ) -> schemas.PurchaseWithOffers:
        purchase_offers = await self.service.get_purchase_offers_by_purchase_id(
            session, purchase.id
        )
        offer_ids = [po.offer_id for po in purchase_offers]
        offers_dict = await self._load_offers_dict_by_ids(session, offer_ids)
        offer_results = await self.service.get_purchase_offer_results_by_purchase_id(
            session, purchase.id
        )
        return self._purchase_to_schema_with_offers(
            purchase, purchase_offers, offers_dict, offer_results
        )

    def _build_success_offer_results_data(
        self, purchase_data: schemas.PurchaseCreate
    ) -> List[dict]:
        offer_results_data = []
        for offer_request in purchase_data.offers:
            offer_results_data.append({
                "offer_id": offer_request.offer_id,
                "status": schemas.OfferProcessingStatus.SUCCESS.value,
                "requested_quantity": offer_request.quantity,
                "processed_quantity": offer_request.quantity,
                "message": f"Successfully processed {offer_request.quantity} items for offer {offer_request.offer_id}"
            })
        return offer_results_data

    def _build_offer_results_data(
        self, offer_results: List[schemas.OfferProcessingResult]
    ) -> List[dict]:
        return [
            {
                "offer_id": result.offer_id,
                "status": result.status.value,
                "requested_quantity": result.requested_quantity,
                "processed_quantity": result.processed_quantity,
                "available_quantity": result.available_quantity,
                "message": result.message
            }
            for result in offer_results
        ]

    async def _schedule_purchase_expiration_task(self, purchase_id: int, stage: str) -> None:
        logger.info("Scheduling Celery task", extra={"stage": stage})
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    check_purchase_expiration.apply_async,
                    args=[purchase_id],
                    countdown=settings.purchase_expiration_seconds,
                    retry=False,
                ),
                timeout=settings.celery_publish_timeout_seconds,
            )
        except Exception as e:
            logger.error(
                f"Failed to schedule Celery task: {e}",
                extra={"stage": stage},
            )

    @handle_alchemy_error
    async def _get_paid_payment_or_400(
        self,
        session: AsyncSession,
        purchase_id: int,
        not_paid_detail: str = "Purchase is not paid"
    ):
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
                detail=not_paid_detail
            )
        return payment

    @handle_alchemy_error
    async def _get_seller_offer_ids_or_403(
        self, session: AsyncSession, seller_id: int
    ) -> List[int]:
        shop_points = await self.shop_points_service.get_shop_points_by_seller(
            session, seller_id
        )
        shop_point_ids = [shop_point.id for shop_point in shop_points]
        if not shop_point_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller has no shop points"
            )

        seller_offers = await self.offers_service.get_offers_by_shop_ids(
            session, shop_point_ids
        )
        seller_offer_ids = [offer.id for offer in seller_offers]
        if not seller_offer_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller has no offers"
            )
        return seller_offer_ids

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
        logger.info(
            f"create_purchase START for user_id={user_id}, offers={len(purchase_data.offers)}",
            extra={"stage": "MANAGER"},
        )
        
        self._validate_purchase_has_offers(purchase_data)
        await self._ensure_no_pending_purchase_for_user(session, user_id, stage="MANAGER")
        locked_offers_dict = await self._lock_requested_offers(
            session, purchase_data, stage="MANAGER"
        )
        
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
        
        await self._reserve_offers(session, purchase_offers_data, stage="MANAGER")
        
        # Create purchase
        logger.info(
            f"Creating purchase for user_id={user_id}, total_cost={total_cost}",
            extra={"stage": "MANAGER"},
        )
        purchase = await self.service.create_purchase(session, user_id, total_cost)
        logger.info(f"Purchase created with id={purchase.id}", extra={"stage": "MANAGER"})
        
        # Create purchase offers
        purchase_offers = await self.service.create_purchase_offers(
            session, purchase.id, purchase_offers_data
        )
        logger.info(
            f"Purchase offers created: {len(purchase_offers)} offers",
            extra={"stage": "MANAGER"},
        )
        
        await self.service.create_purchase_offer_results(
            session, purchase.id, self._build_success_offer_results_data(purchase_data)
        )
        
        # Create payment for this purchase (in the same transaction)
        logger.info(f"Creating payment for purchase_id={purchase.id}", extra={"stage": "MANAGER"})
        await self.payments_manager.create_payment_for_purchase(
            session, purchase.id, purchase.total_cost, base_url
        )
        logger.info("Payment created successfully", extra={"stage": "MANAGER"})
        
        
        
        # Send notifications to sellers about reserved items
        # await self._notify_sellers_about_reservation(session, purchase.id)
        
        await self._schedule_purchase_expiration_task(purchase.id, stage="MANAGER")
        
        # Reload offers to get updated reserved_count values for response
        logger.info("Reloading offers", extra={"stage": "MANAGER"})
        offers_dict = await self._load_offers_dict_by_ids(session, successful_offer_ids)
        
        # Load offer results
        offer_results = await self.service.get_purchase_offer_results_by_purchase_id(session, purchase.id)


        # Commit transaction (releases locks)
        logger.info("Committing transaction", extra={"stage": "MANAGER"})
        await session.commit()
        logger.info("Transaction committed successfully", extra={"stage": "MANAGER"})
        
        # Convert purchase to schema
        logger.info(
            f"create_purchase COMPLETE for purchase_id={purchase.id}",
            extra={"stage": "MANAGER"},
        )
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
        logger.info(
            f"create_purchase_with_partial_success START - user_id={user_id}, offers={len(purchase_data.offers)}",
            extra={"stage": "MANAGER"},
        )
        
        self._validate_purchase_has_offers(purchase_data)
        await self._ensure_no_pending_purchase_for_user(session, user_id, stage="MANAGER")

        # Process each offer individually
        offer_results: List[schemas.OfferProcessingResult] = []
        purchase_offers_data = []
        total_cost = Decimal('0.00')
        successful_offer_ids = []
        
        locked_offers_dict = await self._lock_requested_offers(
            session, purchase_data, stage="MANAGER-PARTIAL"
        )
        
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
                    # Keep DB-compatible status values (error is not allowed by DB constraint)
                    result.status = schemas.OfferProcessingStatus.EXPIRED
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
        
        await self._reserve_offers(session, purchase_offers_data, stage="MANAGER-PARTIAL")
        logger.info("Reserved counts updated", extra={"stage": "MANAGER-PARTIAL"})
        
        # Create purchase
        logger.info(
            f"Creating purchase for user_id={user_id}, total_cost={total_cost}",
            extra={"stage": "MANAGER-PARTIAL"},
        )
        purchase = await self.service.create_purchase(session, user_id, total_cost)
        logger.info(
            f"Purchase created with id={purchase.id}",
            extra={"stage": "MANAGER-PARTIAL"},
        )
        
        # Create purchase offers
        purchase_offers = await self.service.create_purchase_offers(
            session, purchase.id, purchase_offers_data
        )
        
        await self.service.create_purchase_offer_results(
            session, purchase.id, self._build_offer_results_data(offer_results)
        )
        
        # Create payment for this purchase (in the same transaction)
        logger.info(
            f"Creating payment for purchase_id={purchase.id}",
            extra={"stage": "MANAGER-PARTIAL"},
        )
        await self.payments_manager.create_payment_for_purchase(
            session, purchase.id, total_cost, base_url
        )
        logger.info("Payment created", extra={"stage": "MANAGER-PARTIAL"})
        
        # Commit transaction (releases locks)
        logger.info("Committing transaction", extra={"stage": "MANAGER-PARTIAL"})
        await session.commit()
        logger.info("Transaction committed", extra={"stage": "MANAGER-PARTIAL"})
        
        # Send notifications to sellers about reserved items
        await self._notify_sellers_about_reservation(session, purchase.id)
        
        await self._schedule_purchase_expiration_task(purchase.id, stage="MANAGER-PARTIAL")
        
        # Reload offers to get updated reserved_count values for response
        offers_dict = await self._load_offers_dict_by_ids(session, successful_offer_ids)
        
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

    @handle_alchemy_error
    async def get_purchase_by_id(
        self, session: AsyncSession, purchase_id: int
    ) -> schemas.PurchaseWithOffers:
        """Get purchase by ID"""
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        return await self._build_purchase_with_offers_schema(session, purchase)

    @handle_alchemy_error
    async def get_pending_purchase_by_user(
        self, session: AsyncSession, user_id: int
    ) -> schemas.PurchaseWithOffers:
        """Get pending purchase by user ID"""
        purchase = await self.service.get_pending_purchase_by_user(session, user_id)
        return await self._build_purchase_with_offers_schema(session, purchase)

    @handle_alchemy_error
    async def get_purchases_by_user(
        self, session: AsyncSession, user_id: int
    ) -> List[schemas.Purchase]:
        """Get purchases by user ID"""
        purchases = await self.service.get_purchases_by_user(session, user_id)
        return [schemas.Purchase.model_validate(purchase) for purchase in purchases]

    @handle_alchemy_error
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

    @handle_alchemy_error
    async def get_seller_purchases_paginated(
        self,
        session: AsyncSession,
        seller_id: int,
        page: int,
        page_size: int,
        purchase_status: Optional[str] = None,
        fulfillment_status: Optional[str] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        min_updated_at: Optional[datetime] = None,
        max_updated_at: Optional[datetime] = None
    ) -> PaginatedResponse[schemas.PurchaseWithOffers]:
        """Get paginated purchases for current seller (only seller's items in each purchase)."""
        if purchase_status is not None:
            valid_statuses = {purchase_status.value for purchase_status in PurchaseStatus}
            if purchase_status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Valid statuses: {', '.join(sorted(valid_statuses))}"
                )

        valid_fulfillment_statuses = {"fulfilled", "not_fulfilled", "unprocessed"}
        if fulfillment_status is not None and fulfillment_status not in valid_fulfillment_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid fulfillment_status. Valid values: {', '.join(sorted(valid_fulfillment_statuses))}"
            )

        purchases, total_count, purchase_offers_map, offer_results_by_purchase_id = await self.service.get_seller_purchases_paginated(
            session=session,
            seller_offer_ids=await self._get_seller_offer_ids_or_403(session, seller_id),
            page=page,
            page_size=page_size,
            status=purchase_status,
            fulfillment_status=fulfillment_status,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
            min_updated_at=min_updated_at,
            max_updated_at=max_updated_at,
        )

        offer_ids = {
            purchase_offer.offer_id
            for purchase_offers in purchase_offers_map.values()
            for purchase_offer in purchase_offers
        }
        offers = await self.offers_service.get_offers_by_ids(session, list(offer_ids))
        offers_by_id = {offer.id: offer for offer in offers}

        purchases_with_offers: List[schemas.PurchaseWithOffers] = []
        for purchase in purchases:
            seller_offers = purchase_offers_map.get(purchase.id, [])
            offers_dict = {
                purchase_offer.offer_id: offers_by_id.get(purchase_offer.offer_id)
                for purchase_offer in seller_offers
                if purchase_offer.offer_id in offers_by_id
            }
            purchases_with_offers.append(
                self._purchase_to_schema_with_offers(
                    purchase=purchase,
                    purchase_offers=seller_offers,
                    offers_dict=offers_dict,
                    offer_results=offer_results_by_purchase_id.get(purchase.id, []),
                )
            )

        return PaginatedResponse.create(
            items=purchases_with_offers,
            page=page,
            page_size=page_size,
            total_items=total_count
        )
    
    @handle_alchemy_error
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
                await self._release_reservations_for_purchase(session, purchase_id)
            
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
        """Deleting purchases is forbidden."""
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Deleting purchases is not allowed",
        )

    async def _notify_sellers_about_reservation(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Send notifications to sellers whose items were reserved in purchase"""
        logger = get_logger(__name__)
        
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
            shop_points = await self.shop_points_service.get_shop_points_by_ids(
                session, shop_point_ids
            )
            
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
                        id=result.id,
                        offer_id=result.offer_id,
                        status=schemas.OfferProcessingStatus(result.status),
                        requested_quantity=result.requested_quantity,
                        processed_quantity=result.processed_quantity,
                        available_quantity=result.available_quantity,
                        refund_id=result.refund_id,
                        refunded_quantity=result.refunded_quantity,
                        money_flow_status=result.money_flow_status,
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
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        
        # Check if purchase belongs to user
        if purchase.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this purchase"
            )
        
        await self._get_paid_payment_or_400(
            session, purchase_id, not_paid_detail="Order token can only be generated for paid orders"
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
        
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        await self._get_paid_payment_or_400(session, purchase_id)
        
        seller_offer_ids = await self._get_seller_offer_ids_or_403(session, seller_id)

        # Get purchase offers for this seller only
        purchase_offers = await self.service.get_purchase_offers_by_purchase_and_offer_ids(
            session, purchase_id, seller_offer_ids
        )

        offer_ids = [po.offer_id for po in purchase_offers]
        offers = await self.offers_service.get_offers_by_ids_with_products(session, offer_ids)
        offers_by_id = {offer.id: offer for offer in offers}
        offer_results = await self.service.get_purchase_offer_results_by_purchase_ids_and_offer_ids(
            session=session,
            purchase_ids=[purchase_id],
            offer_ids=offer_ids,
        )
        offer_results_by_offer_id = {result.offer_id: result for result in offer_results}

        # Build response items
        items = []
        total_cost = Decimal('0.00')
        
        for po in purchase_offers:
            offer = offers_by_id.get(po.offer_id)
            if offer and offer.product:
                offer_result_model = offer_results_by_offer_id.get(po.offer_id)
                offer_result_schema = None
                if offer_result_model:
                    offer_result_schema = schemas.OfferProcessingResult(
                        id=offer_result_model.id,
                        offer_id=offer_result_model.offer_id,
                        status=schemas.OfferProcessingStatus(offer_result_model.status),
                        requested_quantity=offer_result_model.requested_quantity,
                        processed_quantity=offer_result_model.processed_quantity,
                        available_quantity=offer_result_model.available_quantity,
                        refund_id=offer_result_model.refund_id,
                        refunded_quantity=offer_result_model.refunded_quantity,
                        money_flow_status=offer_result_model.money_flow_status,
                        message=offer_result_model.message,
                    )

                items.append(schemas.PurchaseOfferForFulfillment(
                    purchase_offer_id=po.offer_id,  # Using offer_id as identifier (composite key with purchase_id)
                    offer_id=po.offer_id,
                    quantity=po.quantity,
                    fulfilled_quantity=po.fulfilled_quantity,
                    fulfillment_status=po.fulfillment_status,
                    fulfilled_at=po.fulfilled_at,
                    product_name=offer.product.name,
                    shop_point_id=offer.shop_id,
                    cost_at_purchase=po.cost_at_purchase,
                    offer_result=offer_result_schema,
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
        purchase = await self.service.get_purchase_by_id(session, purchase_id)
        if purchase.status != PurchaseStatus.CONFIRMED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Order fulfillment is allowed only for confirmed purchases. "
                    f"Current status: {purchase.status}"
                ),
            )
        await self._get_paid_payment_or_400(session, purchase_id)
        seller_offer_ids = await self._get_seller_offer_ids_or_403(session, seller_id)
        
        request_offer_ids = [item.offer_id for item in fulfillment_data.items]
        offer_results = await self.service.get_purchase_offer_results_by_purchase_and_offer_ids_for_update(
            session,
            purchase_id,
            request_offer_ids,
        )
        offer_results_map = {offer_result.offer_id: offer_result for offer_result in offer_results}

        # Validate and update each item
        fulfilled_items = []
        refund_items: List[payment_schemas.RefundByOfferResultsRequest.Item] = []
        
        for item in fulfillment_data.items:
            if item.status not in {"fulfilled", "not_fulfilled"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Invalid fulfillment status '{item.status}' for offer {item.offer_id}. "
                        "Allowed values: fulfilled, not_fulfilled"
                    ),
                )
            if item.status == "not_fulfilled" and item.fulfilled_quantity != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Invalid fulfilled_quantity {item.fulfilled_quantity} for status "
                        f"'not_fulfilled' in offer {item.offer_id}. Expected 0."
                    ),
                )

            # Get purchase offer
            po = await self.service.get_purchase_offer_by_purchase_and_offer(
                session, purchase_id, item.offer_id
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

            offer_result = offer_results_map.get(item.offer_id)
            if not offer_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"PurchaseOfferResult for offer {item.offer_id} not found in purchase {purchase_id}"
                )

            max_fulfillable_after_refunds = po.quantity - offer_result.refunded_quantity
            if item.fulfilled_quantity > max_fulfillable_after_refunds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Fulfilled quantity {item.fulfilled_quantity} exceeds remaining "
                        f"fulfillable quantity {max_fulfillable_after_refunds} after refunds "
                        f"for offer {item.offer_id}"
                    ),
                )

            target_refunded_quantity = max(0, po.quantity - item.fulfilled_quantity)
            additional_refund_quantity = target_refunded_quantity - offer_result.refunded_quantity
            if additional_refund_quantity > 0:
                refund_items.append(
                    payment_schemas.RefundByOfferResultsRequest.Item(
                        purchase_offer_result_id=offer_result.id,
                        quantity=additional_refund_quantity,
                    )
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

        if refund_items:
            await self.payments_manager.create_refund_by_offer_results(
                session=session,
                request_data=payment_schemas.RefundByOfferResultsRequest(
                    items=refund_items,
                    reason=(
                        f"Auto refund due to partial fulfillment in purchase {purchase_id} "
                        f"by seller {seller_id}"
                    ),
                ),
                seller_id=seller_id,
            )
        
        # Check if purchase is fully resolved (all items issued and/or refunded)
        purchase_resolved = await self.service.check_all_offers_fulfilled(session, purchase_id)

        if purchase_resolved:
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
