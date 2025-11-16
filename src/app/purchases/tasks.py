"""Celery tasks for purchase expiration"""
from datetime import datetime, timedelta
from celery import Task
from sqlalchemy import select, update
from database import get_sync_session
from config import settings

# Импортируем celery_app первым, чтобы все модели были загружены
from celery_app import celery_app

# Импортируем модели после celery_app для правильной инициализации relationships
from app.purchases.models import Purchase, PurchaseStatus, PurchaseOffer
from app.offers.models import Offer


def cancel_expired_purchase(purchase_id: int) -> None:
    """
    Cancel an expired purchase and release reserved items.
    
    Args:
        purchase_id: ID of the purchase to cancel
    """
    with get_sync_session() as session:
        # Lock purchase first to prevent race conditions
        purchase = session.query(Purchase).filter(
            Purchase.id == purchase_id
        ).with_for_update().first()
        
        if not purchase:
            # Purchase might have been deleted already
            return
        
        # Only cancel if purchase is still pending
        # If purchase was confirmed, reserved_count was already decreased on successful payment
        if purchase.status != PurchaseStatus.PENDING.value:
            # Purchase was already paid or cancelled
            return
        
        # Get purchase offers to release reservations
        purchase_offers = session.query(PurchaseOffer).filter(
            PurchaseOffer.purchase_id == purchase_id
        ).all()
        
        if purchase_offers:
            # Get offer IDs and lock them before updating
            offer_ids = [po.offer_id for po in purchase_offers]
            offers_service = OffersService()
            
            # Lock offers in order to prevent deadlocks
            locked_offers = session.query(Offer).filter(
                Offer.id.in_(offer_ids)
            ).order_by(Offer.id).with_for_update().all()
            
            # Release reservations using service method
            for purchase_offer in purchase_offers:
                from sqlalchemy import func
                session.execute(
                    update(Offer)
                    .where(Offer.id == purchase_offer.offer_id)
                    .values(reserved_count=func.coalesce(Offer.reserved_count, 0) - purchase_offer.quantity)
                )
        
        # Update purchase status to cancelled
        session.execute(
            update(Purchase)
            .where(Purchase.id == purchase_id)
            .values(status=PurchaseStatus.CANCELLED.value)
        )
        
        session.commit()
        print(f"Purchase {purchase_id} expired and cancelled automatically")


@celery_app.task(bind=True, name="check_purchase_expiration")
def check_purchase_expiration(self: Task, purchase_id: int) -> None:
    """
    Celery task to check if a purchase has expired and cancel it if needed.
    This task is scheduled to run after purchase_expiration_seconds.
    
    Args:
        purchase_id: ID of the purchase to check
    """
    cancel_expired_purchase(purchase_id)


async def cancel_all_expired_purchases() -> dict:
    """
    Cancel all expired purchases with pending status.
    This function is used for manual cleanup via debug endpoint.
    
    Returns:
        dict with information about cancelled purchases
    """
    from database import get_async_session
    from app.purchases.service import PurchasesService
    from app.offers.service import OffersService
    
    async with get_async_session() as session:
        try:
            service = PurchasesService()
            offers_service = OffersService()
            
            # Calculate expiration time
            expiration_time = datetime.utcnow() - timedelta(seconds=settings.purchase_expiration_seconds)
            
            # Find all pending purchases that are older than expiration time
            result = await session.execute(
                select(Purchase).where(
                    Purchase.status == PurchaseStatus.PENDING.value,
                    Purchase.created_at < expiration_time
                )
            )
            expired_purchases = result.scalars().all()
            
            cancelled_count = 0
            errors = []
            
            for purchase in expired_purchases:
                try:
                    # Get purchase offers to release reservations
                    purchase_offers = await service.get_purchase_offers_by_purchase_id(
                        session, purchase.id
                    )
                    
                    if purchase_offers:
                        # Get offer IDs that need to be unlocked
                        offer_ids_to_release = [po.offer_id for po in purchase_offers]
                        
                        # Lock offers before releasing reservations
                        await offers_service.get_offers_by_ids_for_update(
                            session, offer_ids_to_release
                        )
                        
                        # Release reservations
                        for purchase_offer in purchase_offers:
                            await offers_service.update_offer_reserved_count(
                                session, purchase_offer.offer_id, -purchase_offer.quantity
                            )
                    
                    # Update purchase status to cancelled
                    await service.update_purchase_status(
                        session, purchase.id, PurchaseStatus.CANCELLED.value
                    )
                    cancelled_count += 1
                except Exception as e:
                    errors.append(f"Error cancelling purchase {purchase.id}: {e}")
            
            await session.commit()
            
            return {
                "cancelled_count": cancelled_count,
                "total_expired": len(expired_purchases),
                "errors": errors
            }
        except Exception as e:
            await session.rollback()
            raise

