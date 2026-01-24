from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func
from fastapi import HTTPException, status
from logger import get_sync_logger

from app.payments import schemas
from app.payments.service import PaymentsService
from app.payments.models import UserPayment, PaymentStatus
from app.purchases.service import PurchasesService
from app.purchases.models import PurchaseStatus
from app.offers.service import OffersService
from app.offers.models import Offer
from app.shop_points.models import ShopPoint
from app.auth.service import AuthService
from app.sellers.manager import SellersManager
from utils.yookassa_client import create_yookassa_client
from utils.errors_handler import handle_alchemy_error
from utils.firebase_notification_manager import FirebaseNotificationManager


class PaymentsManager:
    """Manager for payments business logic and validation"""

    def __init__(self):
        self.service = PaymentsService()
        self.purchases_service = PurchasesService()
        self.offers_service = OffersService()
        self.auth_service = AuthService()
        self.notification_manager = FirebaseNotificationManager()
        self.sellers_manager = SellersManager()

    async def get_batch(self, session: AsyncSession, ids: List[int]):
        """Returns payments list by list of their ids"""
        return await self.service.get_batch(session, ids)

    async def sync_batch_status(
        self, session: AsyncSession, ids: List[int]
    ) -> Dict[str, Any]:
        """Sync payment statuses with YooKassa for multiple payments"""
        payments = await self.service.get_batch(session, ids)
        
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        
        for payment in payments:
            try:
                # Skip payments without YooKassa ID
                if not payment.yookassa_payment_id:
                    results["skipped"].append({
                        "id": payment.id,
                        "reason": "No YooKassa payment ID"
                    })
                    continue
                
                old_status = payment.status
                
                # Get status from YooKassa
                async with create_yookassa_client() as yookassa_client:
                    yookassa_data = await yookassa_client.get_payment(
                        payment.yookassa_payment_id
                    )
                    yookassa_status = yookassa_data.get("status")
                
                # Update status in DB
                await self.service.update_payment_status(
                    session, payment.id, yookassa_status
                )
                
                results["success"].append({
                    "id": payment.id,
                    "old_status": old_status,
                    "new_status": yookassa_status
                })
                
            except Exception as e:
                results["failed"].append({
                    "id": payment.id,
                    "error": str(e)
                })
        
        await session.commit()
        return results

    async def create_payment_for_purchase(
        self,
        session: AsyncSession,
        purchase_id: int,
        amount: Decimal,
        base_url: str,
    ) -> None:
        """Create a payment for a purchase (internal method, called during purchase creation)"""
        # Create payment in DB first to get payment_id for return_url
        payment_internal_temp = schemas.PaymentCreateInternal(
            purchase_id=purchase_id,
            amount=amount,
            currency="RUB",
            description=f"Payment for purchase #{purchase_id}",
            status=PaymentStatus.PENDING.value,
        )
        payment = await self.service.create_payment(session=session, payment_data=payment_internal_temp)
        await session.flush()  # Flush to get payment.id without committing
        
        # Generate return_url with payment_id
        return_url = f"{base_url}/payments/status-page?payment_id={payment.id}"
        
        # Create payment in YooKassa with return_url
        yookassa_payment = await self._create_yookassa_payment_for_purchase(
            purchase_id, amount, return_url
        )
        
        # Update payment with YooKassa data
        payment_internal = self._build_payment_create_internal_from_yookassa(
            purchase_id, yookassa_payment, amount
        )
        await self.service.update_payment(
            session=session,
            payment_id=payment.id,
            payment_data=payment_internal,
        )

    async def _create_yookassa_payment_for_purchase(
        self, purchase_id: int, amount: Decimal, return_url: str
    ) -> Dict[str, Any]:
        """Create payment in YooKassa"""
        async with create_yookassa_client() as yookassa_client:
            return await yookassa_client.create_payment(
                amount=float(amount),
                currency="RUB",
                description=f"Payment for purchase #{purchase_id}",
                return_url=return_url,
            )

    def _build_payment_create_internal_from_yookassa(
        self, purchase_id: int, yookassa_payment: Dict[str, Any], amount: Decimal
    ) -> schemas.PaymentCreateInternal:
        """Build PaymentCreateInternal from YooKassa response"""
        confirmation = yookassa_payment.get("confirmation", {})
        payment_method_obj = yookassa_payment.get("payment_method", {})
        
        return schemas.PaymentCreateInternal(
            purchase_id=purchase_id,
            amount=amount,
            currency="RUB",
            description=f"Payment for purchase #{purchase_id}",
            yookassa_payment_id=yookassa_payment.get("id"),
            status=yookassa_payment.get("status", PaymentStatus.PENDING.value),
            confirmation_url=confirmation.get("confirmation_url") if isinstance(confirmation, dict) else None,
            payment_method=payment_method_obj.get("type") if payment_method_obj else None,
            idempotence_key=None,
            paid_at=self._parse_datetime(yookassa_payment.get("paid_at")),
            captured_at=self._parse_datetime(yookassa_payment.get("captured_at")),
            expires_at=self._parse_datetime(yookassa_payment.get("expires_at")),
        )

    @handle_alchemy_error
    async def create_payment(
        self,
        session: AsyncSession,
        payment_data: schemas.PaymentCreate,
        base_url: str,
    ) -> schemas.PaymentCreateResponse:
        """Create a payment for a purchase via YooKassa"""
        purchase = await self._validate_purchase_and_get_amount(session, payment_data.purchase_id)
        
        # Create payment in DB first to get payment_id for return_url
        payment_internal_temp = schemas.PaymentCreateInternal(
            purchase_id=payment_data.purchase_id,
            amount=purchase.total_cost,
            currency="RUB",
            description=f"Payment for purchase #{payment_data.purchase_id}",
            status=PaymentStatus.PENDING.value,
        )
        payment = await self.service.create_payment(session=session, payment_data=payment_internal_temp)
        await session.flush()  # Flush to get payment.id without committing
        
        # Generate return_url with payment_id
        return_url = f"{base_url}/payments/status-page?payment_id={payment.id}"
        
        # Create payment in YooKassa with return_url
        yookassa_payment = await self._create_yookassa_payment(
            payment_data, purchase.total_cost, return_url
        )
        
        # Update payment with YooKassa data
        payment_internal = self._build_payment_create_internal(
            payment_data, yookassa_payment, purchase.total_cost
        )
        updated_payment = await self.service.update_payment(
            session=session,
            payment_id=payment.id,
            payment_data=payment_internal,
        )
        
        await session.commit()
        
        confirmation_url = self._extract_confirmation_url(yookassa_payment)
        return schemas.PaymentCreateResponse(
            payment=schemas.Payment.model_validate(updated_payment),
            confirmation_url=confirmation_url or ""
        )

    def _extract_confirmation_url(self, yookassa_payment: Dict[str, Any]) -> Optional[str]:
        """Extract confirmation URL from YooKassa payment response"""
        confirmation = yookassa_payment.get("confirmation", {})
        if isinstance(confirmation, dict):
            return confirmation.get("confirmation_url")
        return None

    async def _validate_purchase_and_get_amount(
        self, session: AsyncSession, purchase_id: int
    ):
        """Validate that purchase exists and has total_cost"""
        purchase = await self.purchases_service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        if purchase.total_cost is None or purchase.total_cost <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Purchase with id {purchase_id} has invalid total_cost"
            )
        return purchase

    async def _create_yookassa_payment(
        self, payment_data: schemas.PaymentCreate, amount: Decimal, return_url: str
    ) -> Dict[str, Any]:
        """Create payment in YooKassa"""
        async with create_yookassa_client() as yookassa_client:
            return await yookassa_client.create_payment(
                amount=float(amount),
                currency="RUB",
                description=f"Payment for purchase #{payment_data.purchase_id}",
                return_url=return_url,
            )

    def _build_payment_create_internal(
        self, payment_data: schemas.PaymentCreate, yookassa_payment: Dict[str, Any], amount: Decimal
    ) -> schemas.PaymentCreateInternal:
        """Build PaymentCreateInternal from payment data and YooKassa response"""
        confirmation = yookassa_payment.get("confirmation", {})
        payment_method_obj = yookassa_payment.get("payment_method", {})
        
        return schemas.PaymentCreateInternal(
            purchase_id=payment_data.purchase_id,
            amount=amount,
            currency="RUB",
            description=f"Payment for purchase #{payment_data.purchase_id}",
            yookassa_payment_id=yookassa_payment.get("id"),
            status=yookassa_payment.get("status", PaymentStatus.PENDING.value),
            confirmation_url=confirmation.get("confirmation_url") if isinstance(confirmation, dict) else None,
            payment_method=payment_method_obj.get("type") if payment_method_obj else None,
            idempotence_key=None,
            paid_at=self._parse_datetime(yookassa_payment.get("paid_at")),
            captured_at=self._parse_datetime(yookassa_payment.get("captured_at")),
            expires_at=self._parse_datetime(yookassa_payment.get("expires_at")),
        )

    async def get_payment_by_id(
        self, session: AsyncSession, payment_id: int
    ) -> schemas.Payment:
        """Get payment by ID"""
        payment = await self.service.get_payment_by_id(session, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found"
            )
        return schemas.Payment.model_validate(payment)

    async def get_payment_by_id_for_user(
        self, session: AsyncSession, payment_id: int, user_id: int
    ) -> schemas.Payment:
        """Get payment by ID with user ownership check"""
        payment = await self.get_payment_by_id(session, payment_id)
        
        purchase = await self.purchases_service.get_purchase_by_id(session, payment.purchase_id)
        if not purchase or purchase.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this payment"
            )
        
        return payment

    async def get_payment_by_purchase_id_for_user(
        self, session: AsyncSession, purchase_id: int, user_id: int
    ) -> schemas.Payment:
        """Get payment by purchase ID with user ownership check"""
        purchase = await self.purchases_service.get_purchase_by_id(session, purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {purchase_id} not found"
            )
        if purchase.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this purchase"
            )

        return await self.get_payment_by_purchase_id(session, purchase_id)

    async def check_payment_status_for_user(
        self, session: AsyncSession, payment_id: int, user_id: int
    ) -> schemas.Payment:
        """Check payment status with user ownership check"""
        payment = await self.get_payment_by_id_for_user(session, payment_id, user_id)
        return await self.check_payment_status(session, payment_id)

    async def cancel_payment_for_user(
        self, session: AsyncSession, payment_id: int, user_id: int
    ) -> schemas.Payment:
        """Cancel payment with user ownership check"""
        payment = await self.get_payment_by_id_for_user(session, payment_id, user_id)
        return await self.cancel_payment(session, payment_id)

    async def get_payment_by_yookassa_id(
        self, session: AsyncSession, yookassa_payment_id: str
    ) -> schemas.Payment:
        """Get payment by YooKassa payment ID"""
        payment = await self.service.get_payment_by_yookassa_id(
            session, yookassa_payment_id
        )
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with YooKassa ID {yookassa_payment_id} not found"
            )
        return schemas.Payment.model_validate(payment)

    async def get_payment_by_purchase_id(
        self, session: AsyncSession, purchase_id: int
    ) -> schemas.Payment:
        """Get payment by purchase ID (one payment per purchase)"""
        payment = await self.service.get_payment_by_purchase_id(session, purchase_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment for purchase {purchase_id} not found"
            )
        return schemas.Payment.model_validate(payment)

    @handle_alchemy_error
    async def check_payment_status(
        self, session: AsyncSession, payment_id: int
    ) -> schemas.Payment:
        """Check payment status in YooKassa and update local database"""
        payment = await self._get_payment_or_raise(session, payment_id)
        self._validate_payment_has_yookassa_id(payment)

        yookassa_payment = await self._get_yookassa_payment(payment.yookassa_payment_id)
        old_status = payment.status
        
        updated_payment = await self._update_payment_from_yookassa_response(
            session, payment, yookassa_payment
        )

        return await self._handle_payment_status_change(
            session, updated_payment, yookassa_payment.get("status"), old_status
        )

    async def _get_payment_or_raise(
        self, session: AsyncSession, payment_id: int
    ) -> UserPayment:
        """Get payment by ID or raise exception (with FOR UPDATE lock)"""
        payment = await self.service.get_payment_by_id_for_update(session, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found"
            )
        return payment

    def _validate_payment_has_yookassa_id(self, payment: UserPayment) -> None:
        """Validate that payment has YooKassa payment ID"""
        if not payment.yookassa_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment does not have YooKassa payment ID"
            )

    async def _get_yookassa_payment(self, yookassa_payment_id: str) -> Dict[str, Any]:
        """Get payment status from YooKassa"""
        async with create_yookassa_client() as yookassa_client:
            return await yookassa_client.get_payment(yookassa_payment_id)

    async def _handle_payment_status_change(
        self,
        session: AsyncSession,
        payment: UserPayment,
        new_status: str,
        old_status: str,
    ) -> schemas.Payment:
        """Handle payment status change"""
        if new_status == PaymentStatus.SUCCEEDED.value and old_status != PaymentStatus.SUCCEEDED.value:
            return await self.handle_payment_success(session, payment.id)
        elif new_status == PaymentStatus.CANCELED.value and old_status != PaymentStatus.CANCELED.value:
            return await self.handle_payment_cancellation(session, payment.id)
        else:
            await session.commit()
            return schemas.Payment.model_validate(payment)

    @handle_alchemy_error
    async def cancel_payment(
        self, session: AsyncSession, payment_id: int
    ) -> schemas.Payment:
        """Cancel payment in YooKassa and update local database"""
        payment = await self._get_payment_or_raise(session, payment_id)
        self._validate_payment_has_yookassa_id(payment)
        self._validate_payment_can_be_canceled(payment)

        yookassa_payment = await self._cancel_yookassa_payment(payment.yookassa_payment_id)
        updated_payment = await self._update_payment_from_yookassa_response(
            session, payment, yookassa_payment
        )

        await session.commit()
        return schemas.Payment.model_validate(updated_payment)

    def _validate_payment_can_be_canceled(self, payment: UserPayment) -> None:
        """Validate that payment can be canceled"""
        if payment.status == PaymentStatus.CANCELED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment is already canceled"
            )
        if payment.status == PaymentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel succeeded payment"
            )

    async def _cancel_yookassa_payment(self, yookassa_payment_id: str) -> Dict[str, Any]:
        """Cancel payment in YooKassa"""
        async with create_yookassa_client() as yookassa_client:
            return await yookassa_client.cancel_payment(yookassa_payment_id)

    async def _update_payment_from_yookassa_response(
        self,
        session: AsyncSession,
        payment: UserPayment,
        yookassa_payment: Dict[str, Any],
    ) -> UserPayment:
        """Update payment from YooKassa API response"""
        update_data = self._extract_payment_update_data(payment, yookassa_payment)
        return await self.service.update_payment(
            session=session,
            payment_id=payment.id,
            payment_data=update_data,
        )

    def _extract_payment_update_data(
        self, payment: UserPayment, yookassa_payment: Dict[str, Any]
    ) -> schemas.PaymentUpdate:
        """Extract payment update data from YooKassa response"""
        confirmation = yookassa_payment.get("confirmation", {})
        payment_method_obj = yookassa_payment.get("payment_method", {})
        cancellation = yookassa_payment.get("cancellation_details", {})
        
        return schemas.PaymentUpdate(
            status=yookassa_payment.get("status", payment.status),
            confirmation_url=confirmation.get("confirmation_url") if isinstance(confirmation, dict) else payment.confirmation_url,
            payment_method=payment_method_obj.get("type") if payment_method_obj else payment.payment_method,
            paid_at=self._parse_datetime(yookassa_payment.get("paid_at")) or payment.paid_at,
            captured_at=self._parse_datetime(yookassa_payment.get("captured_at")) or payment.captured_at,
            expires_at=self._parse_datetime(yookassa_payment.get("expires_at")) or payment.expires_at,
            cancellation_reason=cancellation.get("reason") if cancellation else None,
            cancellation_details=cancellation if cancellation else None,
        )

    @handle_alchemy_error
    async def handle_payment_success(
        self,
        session: AsyncSession,
        payment_id: int,
    ) -> schemas.Payment:
        """
        Handle successful payment:
        - Update payment status to succeeded
        - Update purchase status to confirmed
        - Decrease offer count and reserved_count - items are sold and removed from inventory
        
        Lock order: Payment -> Purchase -> Offers (to avoid deadlocks)
        """
        # Lock payment first
        payment = await self.service.get_payment_by_id_for_update(session, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found"
            )

        # Lock purchase before updating
        purchase = await self.purchases_service.get_purchase_by_id_for_update(session, payment.purchase_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase with id {payment.purchase_id} not found"
            )

        updated_payment = await self._update_payment_to_succeeded(session, payment_id)
        await self._confirm_purchase(session, payment.purchase_id)
        await self._decrease_offer_counts(session, payment.purchase_id)

        await session.commit()
        
        # Send push notification to user about successful payment
        await self._send_payment_success_notification(session, purchase.user_id, payment_id)
        
        # Send notifications to sellers about paid items
        await self._notify_sellers_about_payment(session, payment.purchase_id, payment_id)
        
        return schemas.Payment.model_validate(updated_payment)

    async def _update_payment_to_succeeded(
        self, session: AsyncSession, payment_id: int
    ) -> UserPayment:
        """Update payment status to succeeded"""
        return await self.service.update_payment(
            session=session,
            payment_id=payment_id,
            payment_data=schemas.PaymentUpdate(status=PaymentStatus.SUCCEEDED.value),
        )

    async def _confirm_purchase(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Update purchase status to confirmed (purchase should already be locked)"""
        await self.purchases_service.update_purchase_status(
            session, purchase_id, PurchaseStatus.CONFIRMED.value
        )

    async def _decrease_offer_counts(
        self, session: AsyncSession, purchase_id: int
    ) -> None:
        """Decrease offer count and reserved_count - items are sold"""
        purchase_offers = await self.purchases_service.get_purchase_offers_by_purchase_id(
            session, purchase_id
        )

        if not purchase_offers:
            return

        offer_ids = [po.offer_id for po in purchase_offers]
        await self.offers_service.get_offers_by_ids_for_update(session, offer_ids)

        for purchase_offer in purchase_offers:
            # Decrease both count (total quantity) and reserved_count
            # When item is sold, we remove it from inventory and release the reservation
            await self.offers_service.update_offer_count(
                session, purchase_offer.offer_id, -purchase_offer.quantity
            )
            await self.offers_service.update_offer_reserved_count(
                session, purchase_offer.offer_id, -purchase_offer.quantity
            )

    @handle_alchemy_error
    async def handle_payment_cancellation(
        self,
        session: AsyncSession,
        payment_id: int,
    ) -> schemas.Payment:
        """
        Handle payment cancellation:
        - Update payment status to canceled
        - Do NOT release reservations (only happens on purchase cancellation)
        """
        payment = await self.service.get_payment_by_id(session, payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with id {payment_id} not found"
            )

        # Update payment status to canceled
        updated_payment = await self.service.update_payment(
            session=session,
            payment_id=payment_id,
            payment_data=schemas.PaymentUpdate(status=PaymentStatus.CANCELED.value),
        )

        await session.commit()
        return schemas.Payment.model_validate(updated_payment)

    @handle_alchemy_error
    async def handle_webhook(
        self,
        session: AsyncSession,
        webhook_data: schemas.PaymentWebhook,
    ) -> None:
        """Handle YooKassa webhook event"""
        logger = get_sync_logger(__name__)
        
        try:
            logger.info(
                "Processing webhook event",
                extra={
                    "event_type": webhook_data.type,
                    "event": webhook_data.event
                }
            )
            
            yookassa_payment_id = await self._extract_yookassa_payment_id(webhook_data)
            logger.info(
                f"Extracted YooKassa payment ID: {yookassa_payment_id}",
                extra={"yookassa_payment_id": yookassa_payment_id}
            )
            
            payment = await self._get_payment_by_yookassa_id_or_raise(session, yookassa_payment_id)
            logger.info(
                f"Found payment in database",
                extra={
                    "payment_id": payment.id,
                    "purchase_id": payment.purchase_id,
                    "current_status": payment.status,
                    "yookassa_payment_id": yookassa_payment_id
                }
            )
            
            old_status = payment.status
            new_status = webhook_data.object.get("status")
            
            logger.info(
                f"Updating payment status",
                extra={
                    "payment_id": payment.id,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
            
            updated_payment = await self._update_payment_from_yookassa_response(
                session, payment, webhook_data.object
            )

            logger.info(
                f"Handling payment status change",
                extra={
                    "payment_id": updated_payment.id,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )

            await self._handle_payment_status_change(
                session, updated_payment, new_status, old_status
            )
            
            logger.info(
                f"Webhook processing completed successfully",
                extra={
                    "payment_id": updated_payment.id,
                    "final_status": updated_payment.status
                }
            )
            
        except HTTPException as e:
            logger.error(
                f"HTTP error processing webhook: {e.detail}",
                extra={
                    "error_type": "HTTPException",
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "yookassa_payment_id": webhook_data.object.get("id") if webhook_data and webhook_data.object else None
                }
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error processing webhook: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "yookassa_payment_id": webhook_data.object.get("id") if webhook_data and webhook_data.object else None
                }
            )
            raise

    async def _extract_yookassa_payment_id(self, webhook_data: schemas.PaymentWebhook) -> str:
        """Extract YooKassa payment ID from webhook data"""
        logger = get_sync_logger(__name__)
        
        if not webhook_data.object:
            logger.error(
                "Webhook payload missing object field",
                extra={"webhook_data": webhook_data.model_dump() if hasattr(webhook_data, 'model_dump') else str(webhook_data)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook payload missing object field"
            )
        
        yookassa_payment_id = webhook_data.object.get("id")
        if not yookassa_payment_id:
            logger.error(
                "Webhook payload missing payment ID",
                extra={
                    "webhook_object": webhook_data.object,
                    "event_type": webhook_data.type,
                    "event": webhook_data.event
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook payload missing payment ID"
            )
        return yookassa_payment_id

    async def _get_payment_by_yookassa_id_or_raise(
        self, session: AsyncSession, yookassa_payment_id: str
    ) -> UserPayment:
        """Get payment by YooKassa payment ID or raise exception (with FOR UPDATE lock)"""
        logger = get_sync_logger(__name__)
        
        payment = await self.service.get_payment_by_yookassa_id_for_update(session, yookassa_payment_id)
        if not payment:
            logger.error(
                f"Payment with YooKassa ID not found in database",
                extra={
                    "yookassa_payment_id": yookassa_payment_id,
                    "error_type": "PaymentNotFound"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with YooKassa ID {yookassa_payment_id} not found"
            )
        return payment

    async def _send_payment_success_notification(
        self, session: AsyncSession, user_id: int, payment_id: int
    ) -> None:
        """Send push notification to user about successful payment"""
        logger = get_sync_logger(__name__)
        
        try:
            user = await self.auth_service.get_user(session, user_id)
            if not user or not user.firebase_token:
                logger.info(
                    "Skipping notification: user not found or no firebase token",
                    extra={"user_id": user_id, "payment_id": payment_id}
                )
                return
            
            await self.notification_manager.send_notification(
                token=user.firebase_token,
                title="Payment confirmed",
                body=f"Your payment #{payment_id} has been successfully confirmed",
                data={
                    "type": "payment_succeeded",
                    "payment_id": str(payment_id),
                }
            )
            
            logger.info(
                "Payment success notification sent",
                extra={"user_id": user_id, "payment_id": payment_id}
            )
        except Exception as e:
            logger.error(
                f"Failed to send payment success notification: {str(e)}",
                extra={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            # Don't raise exception - notification failure shouldn't break payment processing

    async def _notify_sellers_about_payment(
        self, session: AsyncSession, purchase_id: int, payment_id: int
    ) -> None:
        """Send notifications to sellers whose items were paid"""
        logger = get_sync_logger(__name__)
        
        try:
            # Get purchase offers
            purchase_offers = await self.purchases_service.get_purchase_offers_by_purchase_id(
                session, purchase_id
            )
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
                            "cost": purchase_offer.cost_at_purchase or Decimal('0.00')
                        })
            
            # Send notifications to each seller
            for seller_id, offers_list in seller_offers.items():
                total_items = sum(offer["quantity"] for offer in offers_list)
                total_cost = sum(offer["quantity"] * offer["cost"] for offer in offers_list)
                
                await self.sellers_manager.send_notification_to_seller(
                    session=session,
                    seller_id=seller_id,
                    title="Payment received",
                    body=f"Payment received for {total_items} item(s) in order #{purchase_id}",
                    data={
                        "type": "payment_received",
                        "purchase_id": str(purchase_id),
                        "payment_id": str(payment_id),
                        "total_items": str(total_items),
                        "total_cost": f"{total_cost:.2f}"
                    }
                )
                
                logger.info(
                    "Payment notification sent to seller",
                    extra={"seller_id": seller_id, "purchase_id": purchase_id, "payment_id": payment_id, "items_count": total_items}
                )
        except Exception as e:
            logger.error(
                f"Failed to send payment notifications to sellers: {str(e)}",
                extra={
                    "purchase_id": purchase_id,
                    "payment_id": payment_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            # Don't raise exception - notification failure shouldn't break payment processing

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime from YooKassa ISO format"""
        if not value:
            return None
        
        try:
            # YooKassa returns ISO 8601 format: "2023-01-01T12:00:00.000Z"
            # Remove 'Z' and parse
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except (ValueError, AttributeError):
            return None

