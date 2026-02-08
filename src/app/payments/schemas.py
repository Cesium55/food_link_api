from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.purchases.schemas import Purchase


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    WAITING_FOR_CAPTURE = "waiting_for_capture"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class PaymentCreate(BaseModel):
    """Schema for creating payment"""
    purchase_id: int = Field(..., description="Purchase ID")


class PaymentBase(BaseModel):
    """Base schema for payment"""
    purchase_id: int = Field(..., description="Purchase ID")
    yookassa_payment_id: Optional[str] = Field(None, description="YooKassa payment ID")
    status: str = Field(..., description="Payment status")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Payment currency")
    description: Optional[str] = Field(None, description="Payment description")
    confirmation_url: Optional[str] = Field(None, description="URL for payment confirmation")
    payment_method: Optional[str] = Field(None, description="Payment method")
    paid_at: Optional[datetime] = Field(None, description="Payment date")
    captured_at: Optional[datetime] = Field(None, description="Capture date")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    cancellation_details: Optional[Dict[str, Any]] = Field(None, description="Cancellation details")


class Payment(PaymentBase):
    """Schema for displaying payment"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


class PaymentWithPurchase(Payment):
    """Payment schema with purchase information"""
    purchase: Optional["Purchase"] = Field(None, description="Purchase information")


class PaymentUpdate(BaseModel):
    """Schema for updating payment"""
    yookassa_payment_id: Optional[str] = Field(None, description="YooKassa payment ID")
    status: Optional[str] = Field(None, description="Payment status")
    confirmation_url: Optional[str] = Field(None, description="URL for payment confirmation")
    payment_method: Optional[str] = Field(None, description="Payment method")
    paid_at: Optional[datetime] = Field(None, description="Payment date")
    captured_at: Optional[datetime] = Field(None, description="Capture date")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    cancellation_details: Optional[Dict[str, Any]] = Field(None, description="Cancellation details")


class PaymentCreateInternal(BaseModel):
    """Internal schema for creating payment in database"""
    purchase_id: int = Field(..., description="Purchase ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="RUB", description="Payment currency")
    description: Optional[str] = Field(None, description="Payment description")
    yookassa_payment_id: Optional[str] = Field(None, description="YooKassa payment ID")
    status: str = Field(default="pending", description="Payment status")
    confirmation_url: Optional[str] = Field(None, description="URL for payment confirmation")
    payment_method: Optional[str] = Field(None, description="Payment method")
    idempotence_key: Optional[str] = Field(None, description="Idempotence key")
    paid_at: Optional[datetime] = Field(None, description="Payment date")
    captured_at: Optional[datetime] = Field(None, description="Capture date")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    cancellation_details: Optional[Dict[str, Any]] = Field(None, description="Cancellation details")


class PaymentCreateResponse(BaseModel):
    """Response schema for payment creation with confirmation URL"""
    payment: Payment = Field(..., description="Created payment")
    confirmation_url: str = Field(..., description="URL for payment confirmation in webview")


class PaymentStatusResponse(BaseModel):
    """Response schema for payment status"""
    payment_id: int = Field(..., description="Payment ID")
    status: str = Field(..., description="Payment status")
    purchase_id: int = Field(..., description="Purchase ID")


class PaymentWebhook(BaseModel):
    """Schema for YooKassa webhook payload"""
    type: str = Field(..., description="Event type")
    event: str = Field(..., description="Event name")
    object: Dict[str, Any] = Field(..., description="Payment object from YooKassa")


# Update forward references
def _rebuild_models():
    try:
        from app.purchases.schemas import Purchase
        PaymentWithPurchase.model_rebuild()
    except ImportError:
        pass

_rebuild_models()





