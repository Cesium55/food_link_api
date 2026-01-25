from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional
import json
import asyncio
from pydantic import BaseModel, Field, model_validator
from app.debug.init import initialize_categories_from_json_file
from app.debug.recalculate_purchase_statuses import recalculate_purchase_statuses
from app.purchases.tasks import cancel_all_expired_purchases
from app.auth.service import AuthService
from app.offers.init_pricing_strategies import init_pricing_strategies
from config import settings

router = APIRouter(prefix="/debug", tags=["debug"])
auth_service = AuthService()


class SendSMSRequest(BaseModel):
    """Request model for sending SMS"""
    destination: str = Field(..., description="Recipient phone number (will be formatted automatically)")
    text: str = Field(..., min_length=1, description="Message text")


class SendVerificationCodeRequest(BaseModel):
    """Request model for sending verification code SMS"""
    destination: str = Field(..., description="Recipient phone number (will be formatted automatically)")
    code_length: int = Field(default=6, ge=4, le=10, description="Length of verification code (4-10 digits)")


class SendFirebaseNotificationRequest(BaseModel):
    """Request model for sending Firebase push notification"""
    user_id: Optional[int] = Field(None, description="User ID to send notification to (will use user's firebase_token from DB)")
    token: Optional[str] = Field(None, description="Firebase token to send notification to (if user_id not provided)")
    title: str = Field(default="Test Notification", description="Notification title")
    body: str = Field(default="This is a test notification from debug endpoint", description="Notification body text")
    image_url: Optional[str] = Field(None, description="Optional image URL for rich notification")
    
    @model_validator(mode='after')
    def validate_user_id_or_token(self):
        """Validate that either user_id or token is provided"""
        if not self.user_id and not self.token:
            raise ValueError("Either user_id or token must be provided")
        return self


@router.post("/init-categories-from-file")
async def initialize_categories_from_file(request: Request) -> Dict[str, Any]:
    """
    Initialize product categories from categories.md file.
    This will read the JSON structure from categories.md and create/update categories.
    """
    try:
        result = await initialize_categories_from_json_file(request.state.session)
        
        return {
            "success": True,
            "message": "Categories initialized from file successfully",
            "result": result,
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON in categories file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize categories from file: {str(e)}"
        )


@router.post("/init-pricing-strategies")
async def initialize_pricing_strategies(request: Request) -> Dict[str, Any]:
    """
    Initialize default pricing strategies.
    Creates two strategies:
    - "Последняя неделя": 7 days (30%) → 6 days (40%) → ... → 1 day (90%)
    - "Мягкое снижение": 14 days (10%) → 10 days (20%) → ... → 1 day (60%)
    
    This endpoint is idempotent - can be called multiple times without creating duplicates.
    """
    try:
        strategies = await init_pricing_strategies(request.state.session)
        
        return {
            "success": True,
            "message": "Pricing strategies initialized successfully",
            "strategies": {
                "last_week": {
                    "id": strategies["last_week"].id,
                    "name": strategies["last_week"].name,
                    "steps_count": len(strategies["last_week"].steps)
                },
                "soft_reduction": {
                    "id": strategies["soft_reduction"].id,
                    "name": strategies["soft_reduction"].name,
                    "steps_count": len(strategies["soft_reduction"].steps)
                }
            }
        }
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to initialize pricing strategies",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )


@router.post("/cancel-expired-purchases")
async def cancel_expired_purchases(request: Request) -> Dict[str, Any]:
    """
    Cancel all expired purchases with pending status.
    This endpoint manually checks and cancels all expired purchases without using Celery.
    Useful for debugging and manual cleanup.
    """
    try:
        result = await cancel_all_expired_purchases()
        
        return {
            "success": True,
            "message": f"Cancelled {result['cancelled_count']} expired purchases",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel expired purchases: {str(e)}"
        )


class CreatePaymentRequest(BaseModel):
    """Модель запроса для создания платежа"""
    amount: float = Field(..., description="Сумма платежа", gt=0)
    currency: str = Field(default="RUB", description="Валюта платежа")
    description: Optional[str] = Field(default="Тестовый платеж", description="Описание платежа")
    return_url: Optional[str] = Field(
        default="http://localhost:3000/payment/return",
        description="URL для возврата после оплаты"
    )


@router.post("/create-payment")
async def create_payment(request_body: CreatePaymentRequest) -> Dict[str, Any]:
    """
    Создать платеж через YooKassa.
    
    Пользователь сможет выбрать способ оплаты на странице YooKassa.
    Способ оплаты не указывается - YooKassa покажет все доступные варианты.
    
    Требуются настройки в .env:
    - YOOKASSA_SHOP_ID
    - YOOKASSA_SECRET_KEY
    
    Пример запроса:
    ```json
    {
        "amount": 100.00,
        "description": "Оплата заказа",
        "return_url": "http://localhost:3000/payment/return"
    }
    ```
    """
    # Проверяем наличие настроек YooKassa
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        raise HTTPException(
            status_code=500,
            detail="YooKassa credentials not configured. Please set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY in .env"
        )
    
    try:
        # Импортируем библиотеку yookassa
        from yookassa import Configuration, Payment
        
        # Настраиваем YooKassa (синхронно)
        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key
        
        # Формируем параметры платежа
        payment_data = {
            "amount": {
                "value": f"{request_body.amount:.2f}",
                "currency": request_body.currency
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request_body.return_url
            },
            "description": request_body.description,
            "capture": True  # Автоматическое подтверждение после оплаты
        }
        
        # Создаем платеж синхронно в отдельном потоке (чтобы не блокировать event loop)
        def create_payment_sync():
            payment_response = Payment.create(payment_data, idempotency_key=None)
            return payment_response
        
        # Выполняем синхронную функцию в пуле потоков
        payment_response = await asyncio.to_thread(create_payment_sync)
        
        # Преобразуем ответ в словарь для JSON-сериализации
        payment_dict = {
            "id": payment_response.id,
            "status": payment_response.status,
            "amount": {
                "value": payment_response.amount.value,
                "currency": payment_response.amount.currency
            },
            "description": payment_response.description,
            "confirmation": {
                "type": payment_response.confirmation.type,
                "confirmation_url": payment_response.confirmation.confirmation_url
            },
            "created_at": payment_response.created_at.isoformat() if hasattr(payment_response.created_at, 'isoformat') else str(payment_response.created_at),
            "paid": payment_response.paid,
        }
        
        # Добавляем информацию о способе оплаты, если она есть
        if hasattr(payment_response, 'payment_method') and payment_response.payment_method:
            payment_dict["payment_method"] = {
                "type": payment_response.payment_method.type if hasattr(payment_response.payment_method, 'type') else None,
            }
        
        return {
            "success": True,
            "message": "Payment created successfully",
            "payment": payment_dict
        }
        
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import yookassa library: {str(e)}. Make sure yookassa>=3.8.0 is installed."
        )
    except Exception as e:
        # Проверяем, является ли это ошибкой YooKassa API
        error_message = str(e)
        error_type = type(e).__name__
        
        # Извлекаем дополнительную информацию об ошибке
        error_code = getattr(e, 'code', None)
        error_description = getattr(e, 'description', None)
        error_id = getattr(e, 'id', None)
        
        # Пытаемся получить детали из ответа API
        if hasattr(e, 'response') and e.response:
            try:
                if hasattr(e.response, 'json'):
                    error_data = e.response.json()
                    if isinstance(error_data, dict):
                        error_description = error_data.get('description', error_description)
                        error_code = error_data.get('code', error_code)
                        error_id = error_data.get('id', error_id)
            except:
                pass
        
        # Пытаемся распарсить строку ошибки, если она содержит словарь
        # Например: "{'type': 'error', 'id': '...', 'description': '...', 'code': '...'}"
        # или: "{'type': 'error', 'id': '019a8368-996e-7b45-9a73-e4f064e0c92e', 'description': 'Payment method is not available', 'code': 'invalid_request'}"
        if not error_code and not error_description:
            try:
                import ast
                # Пытаемся распарсить через ast.literal_eval (безопасный способ)
                if (error_message.startswith('{') and error_message.endswith('}')) or \
                   (error_message.startswith("'") and "'" in error_message):
                    error_dict = ast.literal_eval(error_message)
                    if isinstance(error_dict, dict):
                        error_description = error_dict.get('description', error_description)
                        error_code = error_dict.get('code', error_code)
                        error_id = error_dict.get('id', error_id)
            except:
                # Если не удалось через ast, пытаемся через regex
                try:
                    import re
                    # Ищем description: '...'
                    desc_match = re.search(r"'description':\s*'([^']+)'", error_message)
                    if desc_match:
                        error_description = desc_match.group(1)
                    
                    # Ищем code: '...'
                    code_match = re.search(r"'code':\s*'([^']+)'", error_message)
                    if code_match:
                        error_code = code_match.group(1)
                    
                    # Ищем id: '...'
                    id_match = re.search(r"'id':\s*'([^']+)'", error_message)
                    if id_match:
                        error_id = id_match.group(1)
                except:
                    pass
        
        # Проверяем тип ошибки для правильного HTTP статуса
        error_lower = error_message.lower()
        description_lower = str(error_description).lower() if error_description else ""
        
        if 'ForbiddenError' in error_type or '403' in error_message or 'unauthorized' in error_lower or 'authentication' in error_lower:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "YooKassa authentication error",
                    "message": "Ошибка аутентификации. Проверьте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY.",
                    "yookassa_error": error_message,
                    "yookassa_error_type": error_type,
                    "yookassa_code": error_code
                }
            )
        elif 'NotFoundError' in error_type or '404' in error_message:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "YooKassa resource not found",
                    "message": error_message,
                    "yookassa_error_type": error_type,
                    "yookassa_code": error_code
                }
            )
        elif 'TooManyRequestsError' in error_type or '429' in error_message or 'rate limit' in error_lower:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "YooKassa rate limit exceeded",
                    "message": "Превышен лимит запросов. Попробуйте позже.",
                    "yookassa_error": error_message,
                    "yookassa_error_type": error_type
                }
            )
        elif 'BadRequestError' in error_type or 'ApiError' in error_type or error_code:
            # Общая ошибка API YooKassa (400, 422 и т.д.)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "YooKassa API error",
                    "message": error_message,
                    "yookassa_error_type": error_type,
                    "code": error_code,
                    "id": error_id,
                    "description": error_description
                }
            )
        else:
            # Если это не специфичная ошибка YooKassa, обрабатываем как общую ошибку
            import traceback
            error_details = {
                "error": "Unexpected error",
                "message": error_message,
                "type": error_type
            }
            
            # В режиме отладки добавляем трейсбек
            if settings.debug:
                error_details["traceback"] = traceback.format_exc()
            
            raise HTTPException(
                status_code=500,
                detail=error_details
            )


@router.post("/send-sms")
async def send_sms(request_body: SendSMSRequest) -> Dict[str, Any]:
    """
    Send SMS to specified phone number with given text.
    
    Requires settings in .env:
    - EXOLVE_API_KEY
    - EXOLVE_NUMBER
    
    Example request:
    ```json
    {
        "destination": "79123456789",
        "text": "Test message"
    }
    ```
    """
    # Check if Exolve settings are configured
    if not settings.exolve_api_key or not settings.exolve_number:
        raise HTTPException(
            status_code=500,
            detail="Exolve credentials not configured. Please set EXOLVE_API_KEY and EXOLVE_NUMBER in .env"
        )
    
    try:
        from utils.exolve_sms_manager import create_exolve_sms_manager
        
        async with create_exolve_sms_manager() as sms_manager:
            result = await sms_manager.send_sms(
                destination=request_body.destination,
                text=request_body.text
            )
            
            return {
                "success": True,
                "message": "SMS sent successfully",
                "result": result
            }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to send SMS",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )


@router.post("/send-verification-code")
async def send_verification_code(request_body: SendVerificationCodeRequest) -> Dict[str, Any]:
    """
    Send SMS with generated verification code and return the code.
    
    Requires settings in .env:
    - EXOLVE_API_KEY
    - EXOLVE_NUMBER
    
    Example request:
    ```json
    {
        "destination": "79123456789",
        "code_length": 6
    }
    ```
    """
    # Check if Exolve settings are configured
    if not settings.exolve_api_key or not settings.exolve_number:
        raise HTTPException(
            status_code=500,
            detail="Exolve credentials not configured. Please set EXOLVE_API_KEY and EXOLVE_NUMBER in .env"
        )
    
    try:
        from utils.exolve_sms_manager import create_exolve_sms_manager
        
        async with create_exolve_sms_manager() as sms_manager:
            code = await sms_manager.send_verification_code(
                destination=request_body.destination,
                code_length=request_body.code_length
            )
            
            return {
                "success": True,
                "message": "Verification code SMS sent successfully",
                "code": code,
                "destination": request_body.destination,
                "code_length": request_body.code_length
            }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to send verification code SMS",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )


@router.post("/send-firebase-notification")
async def send_firebase_notification(request: Request) -> Dict[str, Any]:
    """
    Send Firebase push notification to ALL users with active Firebase tokens.
    
    No parameters required - sends a test notification to everyone who has registered
    their Firebase token. Useful for testing notification delivery.
    """
    try:
        from utils.firebase_notification_manager import create_firebase_notification_manager
        from app.auth.models import User
        from sqlalchemy import select
        
        # Get all users with Firebase tokens directly from database
        result = await request.state.session.execute(
            select(User).where(
                User.firebase_token.isnot(None),
                User.firebase_token != ""
            )
        )
        users = list(result.scalars().all())
        
        if not users:
            return {
                "success": True,
                "message": "No users with Firebase tokens found",
                "total_users": 0,
                "sent_count": 0,
                "failed_count": 0
            }
        
        # Collect all tokens
        tokens = [user.firebase_token for user in users if user.firebase_token]
        
        if not tokens:
            return {
                "success": True,
                "message": "No valid Firebase tokens found",
                "total_users": len(users),
                "sent_count": 0,
                "failed_count": 0
            }
        
        # Send notification to all users using multicast
        notification_manager = create_firebase_notification_manager()
        response = await notification_manager.send_multicast_notification(
            tokens=tokens,
            title="Test Notification",
            body="This is a test notification from debug endpoint"
        )
        
        return {
            "success": True,
            "message": f"Notifications sent to {response.success_count} users",
            "total_users": len(users),
            "total_tokens": len(tokens),
            "sent_count": response.success_count,
            "failed_count": response.failure_count,
            "details": {
                "successful": response.success_count,
                "failed": response.failure_count,
                "total": len(tokens)
            }
        }
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to send Firebase notifications",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )


@router.delete("/user/{user_id}")
async def delete_user(request: Request, user_id: int) -> Dict[str, Any]:
    """
    Delete user by ID.
    
    This is a debug endpoint for testing purposes.
    """
    try:
        deleted = await auth_service.delete_user(request.state.session, user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        await request.state.session.commit()
        
        return {
            "success": True,
            "message": f"User with ID {user_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to delete user",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )


@router.post("/recalculate-purchase-statuses")
async def recalculate_purchase_statuses_endpoint(
    request: Request
) -> Dict[str, Any]:
    """
    Recalculate purchase statuses based on fulfillment status.
    
    Checks all purchases (except completed and cancelled) and updates
    their status to 'completed' if all offers are fulfilled.
    
    This endpoint is useful for fixing purchase statuses that may have been
    incorrectly set due to bugs or race conditions.
    """
    try:
        result = await recalculate_purchase_statuses(
            session=request.state.session
        )
        
        return {
            "success": True,
            "message": result["message"],
            "statistics": {
                "processed_count": result["processed_count"],
                "updated_count": result["updated_count"],
                "skipped_count": result["skipped_count"]
            },
            "updated_purchases": result["updated_purchases"],
            "skipped_purchases": result["skipped_purchases"]
        }
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        
        import traceback
        error_details = {
            "error": "Failed to recalculate purchase statuses",
            "message": error_message,
            "type": error_type
        }
        
        if settings.debug:
            error_details["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )
