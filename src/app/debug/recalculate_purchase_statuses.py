"""
Script to recalculate purchase statuses based on fulfillment status.
Checks all purchases and updates their status to 'completed' if all offers are fulfilled.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.purchases.models import Purchase, PurchaseOffer, PurchaseStatus
from app.purchases.service import PurchasesService
from logger import get_sync_logger

logger = get_sync_logger(__name__)


async def recalculate_purchase_statuses(
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Recalculate purchase statuses based on fulfillment status.
    
    Checks all purchases (except completed and cancelled) and updates
    their status to 'completed' if all offers are fulfilled.
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with statistics about the recalculation process.
    """
    purchases_service = PurchasesService()
    
    # Build query to get all purchases except completed and cancelled
    query = select(Purchase).where(
        and_(
            Purchase.status != PurchaseStatus.COMPLETED.value,
            Purchase.status != PurchaseStatus.CANCELLED.value
        )
    )
    
    # Execute query
    result = await session.execute(query)
    purchases = list(result.scalars().all())
    
    if not purchases:
        return {
            "success": True,
            "message": "No purchases found matching criteria",
            "processed_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "purchases": []
        }
    
    updated_purchases = []
    skipped_purchases = []
    processed_count = 0
    updated_count = 0
    
    # Process each purchase
    for purchase in purchases:
        processed_count += 1
        
        try:
            # Check if all offers are fulfilled
            all_fulfilled = await purchases_service.check_all_offers_fulfilled(
                session, purchase.id
            )
            
            if all_fulfilled:
                # Update purchase status to completed
                if purchase.status != PurchaseStatus.COMPLETED.value:
                    await purchases_service.update_purchase_status(
                        session, purchase.id, PurchaseStatus.COMPLETED.value
                    )
                    updated_count += 1
                    updated_purchases.append({
                        "purchase_id": purchase.id,
                        "old_status": purchase.status,
                        "new_status": PurchaseStatus.COMPLETED.value
                    })
                    logger.info(
                        f"Updated purchase {purchase.id} status from {purchase.status} to completed"
                    )
                else:
                    skipped_purchases.append({
                        "purchase_id": purchase.id,
                        "status": purchase.status,
                        "reason": "Already completed"
                    })
            else:
                # Get purchase offers to provide details
                purchase_offers_result = await session.execute(
                    select(PurchaseOffer)
                    .where(PurchaseOffer.purchase_id == purchase.id)
                )
                purchase_offers = list(purchase_offers_result.scalars().all())
                
                # Check which offers are not fulfilled
                not_fulfilled_offers = []
                for po in purchase_offers:
                    if po.fulfillment_status != 'fulfilled':
                        not_fulfilled_offers.append({
                            "offer_id": po.offer_id,
                            "fulfillment_status": po.fulfillment_status,
                            "fulfilled_quantity": po.fulfilled_quantity,
                            "requested_quantity": po.quantity
                        })
                    elif po.fulfilled_quantity is None or po.fulfilled_quantity < po.quantity:
                        not_fulfilled_offers.append({
                            "offer_id": po.offer_id,
                            "fulfillment_status": po.fulfillment_status,
                            "fulfilled_quantity": po.fulfilled_quantity,
                            "requested_quantity": po.quantity,
                            "reason": "Insufficient fulfilled quantity"
                        })
                
                skipped_purchases.append({
                    "purchase_id": purchase.id,
                    "status": purchase.status,
                    "reason": "Not all offers fulfilled",
                    "not_fulfilled_offers": not_fulfilled_offers
                })
        
        except Exception as e:
            logger.error(
                f"Error processing purchase {purchase.id}: {str(e)}",
                extra={
                    "purchase_id": purchase.id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            skipped_purchases.append({
                "purchase_id": purchase.id,
                "status": purchase.status,
                "reason": f"Error: {str(e)}"
            })
    
    # Commit all changes
    await session.commit()
    
    return {
        "success": True,
        "message": f"Processed {processed_count} purchases, updated {updated_count} to completed status",
        "processed_count": processed_count,
        "updated_count": updated_count,
        "skipped_count": len(skipped_purchases),
        "updated_purchases": updated_purchases,
        "skipped_purchases": skipped_purchases[:10]  # Limit to first 10 for response size
    }
