from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from app.offers.schemas import Offer
    from app.auth.schemas import User


class OfferProcessingStatus(str, Enum):
    """Status of offer processing during purchase creation"""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INSUFFICIENT_QUANTITY = "insufficient_quantity"
    EXPIRED = "expired"


class PurchaseOfferCreate(BaseModel):
    """Schema for creating purchase offer"""
    offer_id: int = Field(..., description="Offer ID")
    quantity: int = Field(..., gt=0, description="Quantity of the offer")


class PurchaseOfferBase(BaseModel):
    """Base schema for purchase offer"""
    quantity: int = Field(..., gt=0, description="Quantity of the offer")
    cost_at_purchase: Optional[float] = Field(None, ge=0, description="Cost at purchase time")


class PurchaseOffer(PurchaseOfferBase):
    """Schema for displaying purchase offer"""
    model_config = ConfigDict(from_attributes=True)
    
    offer_id: int = Field(..., description="Offer ID")
    offer: Optional["Offer"] = Field(None, description="Offer information")


class PurchaseCreate(BaseModel):
    """Schema for creating purchase"""
    offers: List[PurchaseOfferCreate] = Field(..., min_length=1, description="List of offers to purchase")


class PurchaseBase(BaseModel):
    """Base schema for purchase"""
    status: str = Field(..., description="Purchase status")
    total_cost: Optional[float] = Field(None, ge=0, description="Total cost of the purchase")


class Purchase(PurchaseBase):
    """Schema for displaying purchase"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    user_id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


class OfferProcessingResult(BaseModel):
    """Result of processing a single offer during purchase creation"""
    offer_id: int = Field(..., description="Offer ID that was processed")
    status: OfferProcessingStatus = Field(..., description="Processing status")
    requested_quantity: int = Field(..., description="Requested quantity")
    processed_quantity: Optional[int] = Field(None, description="Actually processed quantity (if partial success)")
    available_quantity: Optional[int] = Field(None, description="Available quantity (if insufficient)")
    message: Optional[str] = Field(None, description="Human-readable message about the result")


class PurchaseWithOffers(Purchase):
    """Purchase schema with offers information"""
    purchase_offers: List[PurchaseOffer] = Field(default_factory=list, description="Purchase offers")
    offer_results: List[OfferProcessingResult] = Field(default_factory=list, description="Processing results for each offer")
    ttl: int = Field(..., ge=0, description="Time to live in seconds until purchase expiration")


class PurchaseCreateResponse(BaseModel):
    """Response schema for purchase creation with detailed offer processing results"""
    purchase: PurchaseWithOffers = Field(..., description="Created purchase")
    offer_results: List[OfferProcessingResult] = Field(..., description="Processing results for each offer")
    total_processed: int = Field(..., description="Total number of offers successfully processed")
    total_failed: int = Field(..., description="Total number of offers that failed")


class PurchaseUpdate(BaseModel):
    """Schema for updating purchase"""
    status: Optional[str] = Field(None, description="Purchase status")


# Update forward references
def _rebuild_models():
    try:
        from app.offers.schemas import Offer
        PurchaseOffer.model_rebuild()
    except ImportError:
        pass

_rebuild_models()

