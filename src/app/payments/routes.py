from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from logger import get_sync_logger
from app.payments import schemas
from app.payments.manager import PaymentsManager
from utils.auth_dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/payments", tags=["payments"])

templates = Jinja2Templates(directory="src/templates")

payments_manager = PaymentsManager()


@router.get("/status-page", response_class=HTMLResponse)
async def payment_status_page(request: Request, payment_id: int):
    """Payment status page for return_url. Immediately emits payment status to React Native"""
    payment = await payments_manager.get_payment_by_id(
        request.state.session, payment_id
    )
    
    return templates.TemplateResponse(
        "payment_status.html",
        {
            "request": request,
            "payment_id": payment_id,
            "payment_status": payment.status,
            "purchase_id": payment.purchase_id
        }
    )


@router.post("/webhook", status_code=200)
async def handle_webhook(
    request: Request,
    webhook_data: schemas.PaymentWebhook
) -> dict:
    """
    YooKassa webhook endpoint for payment status updates.
    Returns empty dict to avoid middleware wrapping.
    """
    logger = get_sync_logger(__name__)
    
    try:
        logger.info(
            "Received webhook from YooKassa",
            extra={
                "event_type": webhook_data.type,
                "event": webhook_data.event,
                "payment_id": webhook_data.object.get("id"),
                "payment_status": webhook_data.object.get("status")
            }
        )
        
        await payments_manager.handle_webhook(
            request.state.session, webhook_data
        )
        
        logger.info(
            "Webhook processed successfully",
            extra={
                "event_type": webhook_data.type,
                "event": webhook_data.event,
                "payment_id": webhook_data.object.get("id")
            }
        )
        
        return {}
    except Exception as e:
        logger.error(
            f"Error processing webhook: {str(e)}",
            extra={
                "event_type": webhook_data.type if webhook_data else None,
                "event": webhook_data.event if webhook_data else None,
                "payment_id": webhook_data.object.get("id") if webhook_data and webhook_data.object else None,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None
            }
        )
        raise


@router.get("/purchase/{purchase_id}", response_model=schemas.Payment)
async def get_payment_by_purchase(
    request: Request,
    purchase_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.Payment:
    """Get payment for a purchase"""
    return await payments_manager.get_payment_by_purchase_id_for_user(
        request.state.session, purchase_id, current_user.id
    )


@router.get("/{payment_id}", response_model=schemas.Payment)
async def get_payment(
    request: Request,
    payment_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.Payment:
    """Get payment by ID"""
    return await payments_manager.get_payment_by_id_for_user(
        request.state.session, payment_id, current_user.id
    )


@router.get("/{payment_id}/status", response_model=schemas.PaymentStatusResponse)
async def get_payment_status(
    request: Request,
    payment_id: int
) -> schemas.PaymentStatusResponse:
    """Get current payment status from database (for polling from status page)"""
    payment = await payments_manager.get_payment_by_id(
        request.state.session, payment_id
    )
    
    return schemas.PaymentStatusResponse(
        payment_id=payment.id,
        status=payment.status,
        purchase_id=payment.purchase_id
    )


@router.post("/{payment_id}/check", response_model=schemas.Payment)
async def check_payment_status(
    request: Request,
    payment_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.Payment:
    """Manually check payment status in YooKassa and update local database"""
    return await payments_manager.check_payment_status_for_user(
        request.state.session, payment_id, current_user.id
    )


@router.post("/{payment_id}/cancel", response_model=schemas.Payment)
async def cancel_payment(
    request: Request,
    payment_id: int,
    current_user: User = Depends(get_current_user)
) -> schemas.Payment:
    """Cancel payment in YooKassa and update local database"""
    return await payments_manager.cancel_payment_for_user(
        request.state.session, payment_id, current_user.id
    )
