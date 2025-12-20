from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

if TYPE_CHECKING:
    from app.products.schemas import Product
    from app.shop_points.schemas import ShopPoint


def validate_pricing_conflict(pricing_strategy_id: Optional[int], current_cost: Optional[Decimal]) -> None:
    """Validate that pricing_strategy_id and current_cost are not set simultaneously"""
    if pricing_strategy_id is not None and current_cost is not None:
        raise ValueError(
            "Cannot set both pricing_strategy_id and current_cost. "
            "Use pricing_strategy_id for dynamic pricing or current_cost for fixed price."
        )


class OfferBase(BaseModel):
    """Base schema for offer"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[Decimal] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[Decimal] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")
    pricing_strategy_id: Optional[int] = Field(None, gt=0, description="Pricing strategy ID (optional)")
    
    @field_validator('expires_date')
    @classmethod
    def validate_expires_date_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate that expires_date is timezone-aware"""
        if v is not None and v.tzinfo is None:
            raise ValueError("expires_date must be timezone-aware datetime")
        return v
    
    @model_validator(mode='after')
    def validate_pricing_conflict(self):
        """Validate that pricing_strategy_id and current_cost are not set simultaneously"""
        validate_pricing_conflict(self.pricing_strategy_id, self.current_cost)
        return self
    
    @model_validator(mode='after')
    def validate_cost_relationship(self):
        """Validate relationship between original_cost and current_cost"""
        if (self.original_cost is not None and 
            self.current_cost is not None and 
            self.current_cost > self.original_cost):
            raise ValueError(
                f"current_cost ({self.current_cost}) cannot exceed original_cost ({self.original_cost})"
            )
        return self


class OfferCreate(OfferBase):
    """Schema for creating offer"""
    product_id: int = Field(..., gt=0, description="Product ID")
    shop_id: int = Field(..., gt=0, description="Shop point ID")
    
    @model_validator(mode='after')
    def validate_create_requirements(self):
        """Validate requirements for offer creation"""
        # Check that either pricing strategy or current cost is provided
        if self.pricing_strategy_id is None and self.current_cost is None:
            raise ValueError(
                "Either pricing_strategy_id (for dynamic pricing) or current_cost (for fixed price) must be provided"
            )
        
        # If using dynamic pricing, require original_cost and expires_date
        if self.pricing_strategy_id is not None:
            if self.original_cost is None:
                raise ValueError(
                    "original_cost is required when using pricing_strategy_id for dynamic pricing"
                )
            if self.expires_date is None:
                raise ValueError(
                    "expires_date is required when using pricing_strategy_id for dynamic pricing"
                )
            # Check that expires_date is in the future
            if self.expires_date <= datetime.now(timezone.utc):
                raise ValueError(
                    "expires_date must be in the future when creating an offer with dynamic pricing"
                )
        
        # Validate expires_date is in the future if provided
        if self.expires_date is not None and self.expires_date <= datetime.now(timezone.utc):
            raise ValueError("expires_date must be in the future")
        
        # Validate count is provided and positive when creating offer
        if self.count is None or self.count <= 0:
            raise ValueError("count must be provided and greater than 0 when creating an offer")
        
        return self


class OfferUpdate(BaseModel):
    """Schema for updating offer"""
    expires_date: Optional[datetime] = Field(None, description="Expiration date")
    original_cost: Optional[Decimal] = Field(None, ge=0, description="Original cost")
    current_cost: Optional[Decimal] = Field(None, ge=0, description="Current cost")
    count: Optional[int] = Field(None, ge=0, description="Product quantity")
    pricing_strategy_id: Optional[int] = Field(None, gt=0, description="Pricing strategy ID (optional, set to null to disable)")
    
    @field_validator('expires_date')
    @classmethod
    def validate_expires_date_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate that expires_date is timezone-aware"""
        if v is not None and v.tzinfo is None:
            raise ValueError("expires_date must be timezone-aware datetime")
        return v
    
    @model_validator(mode='after')
    def validate_pricing_conflict(self):
        """Validate that pricing_strategy_id and current_cost are not set simultaneously"""
        validate_pricing_conflict(self.pricing_strategy_id, self.current_cost)
        return self
    
    @model_validator(mode='after')
    def validate_cost_relationship(self):
        """Validate relationship between original_cost and current_cost"""
        if (self.original_cost is not None and 
            self.current_cost is not None and 
            self.current_cost > self.original_cost):
            raise ValueError(
                f"current_cost ({self.current_cost}) cannot exceed original_cost ({self.original_cost})"
            )
        return self
    
    @model_validator(mode='after')
    def validate_update_requirements(self):
        """Validate requirements for offer update"""
        # If expires_date is being updated, check it's in the future
        if self.expires_date is not None and self.expires_date <= datetime.now(timezone.utc):
            raise ValueError("expires_date must be in the future")
        
        # If count is being updated to 0 or negative, raise error
        if self.count is not None and self.count == 0:
            raise ValueError("count cannot be set to 0. Delete the offer instead if no longer available")
        
        return self


class Offer(OfferBase):
    """Schema for displaying offer"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    product_id: int = Field(..., description="Product ID")
    shop_id: int = Field(..., description="Shop point ID")
    reserved_count: Optional[int] = Field(None, ge=0, description="Product reserved quantity")


class OfferWithProduct(Offer):
    """Offer schema with product information"""
    product: "Product" = Field(..., description="Product information")


class OfferWithShop(Offer):
    """Offer schema with shop point information"""
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class OfferWithDetails(Offer):
    """Offer schema with full information"""
    product: "Product" = Field(..., description="Product information")
    shop_point: "ShopPoint" = Field(..., description="Shop point information")


class OffersSummary(BaseModel):
    """Offers summary schema"""
    total_entries: int = Field(..., description="Total number of offers")
    total_products: int = Field(..., description="Number of unique products")
    total_shop_points: int = Field(..., description="Number of unique shop points")
    total_value: Decimal = Field(..., description="Total offers value")


class ExpiringProductsSummary(BaseModel):
    """Expiring products summary schema"""
    expiring_soon: int = Field(..., description="Number of products expiring soon")
    expired: int = Field(..., description="Number of expired products")
    total_entries: int = Field(..., description="Total number of offers with expiration date")


class OffersFilterParams(BaseModel):
    """Schema for offers filter query parameters with validation"""
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, description="Number of items per page")
    product_id: Optional[int] = Field(default=None, ge=1, description="Filter by product ID")
    seller_id: Optional[int] = Field(default=None, ge=1, description="Filter by seller ID")
    shop_id: Optional[int] = Field(default=None, ge=1, description="Filter by shop point ID")
    category_ids: Optional[List[int]] = Field(default=None, description="Filter by category IDs (offers with products having at least one of these categories)")
    min_expires_date: Optional[datetime] = Field(default=None, description="Minimum expiration date")
    max_expires_date: Optional[datetime] = Field(default=None, description="Maximum expiration date")
    min_original_cost: Optional[Decimal] = Field(default=None, ge=0, description="Minimum original cost")
    max_original_cost: Optional[Decimal] = Field(default=None, ge=0, description="Maximum original cost")
    min_current_cost: Optional[Decimal] = Field(default=None, ge=0, description="Minimum current cost")
    max_current_cost: Optional[Decimal] = Field(default=None, ge=0, description="Maximum current cost")
    min_count: Optional[int] = Field(default=None, ge=0, description="Minimum product count")
    min_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Minimum latitude for location-based filtering")
    max_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Maximum latitude for location-based filtering")
    min_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Minimum longitude for location-based filtering")
    max_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Maximum longitude for location-based filtering")
    has_dynamic_pricing: Optional[bool] = Field(default=None, description="Filter by dynamic pricing: true - only with pricing strategy, false - only without, null - all")

    @model_validator(mode='after')
    def validate_location_filters(self):
        """Validate that location filters are used correctly"""
        if self.min_latitude is not None and self.max_latitude is not None and self.min_latitude > self.max_latitude:
            raise ValueError("min_latitude must be less than or equal to max_latitude")
        
        if self.min_longitude is not None and self.max_longitude is not None and self.min_longitude > self.max_longitude:
            raise ValueError("min_longitude must be less than or equal to max_longitude")
        
        return self


class PricingStrategyStepBase(BaseModel):
    """Base schema for pricing strategy step"""
    time_remaining_seconds: int = Field(..., ge=0, description="Time remaining in seconds")
    discount_percent: Decimal = Field(..., ge=0, le=100, description="Discount percentage")


class PricingStrategyStep(PricingStrategyStepBase):
    """Schema for displaying pricing strategy step"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    strategy_id: int = Field(..., description="Strategy ID")


class PricingStrategyBase(BaseModel):
    """Base schema for pricing strategy"""
    name: str = Field(..., min_length=1, max_length=255, description="Strategy name")


class PricingStrategy(PricingStrategyBase):
    """Schema for displaying pricing strategy"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier")
    steps: List[PricingStrategyStep] = Field(default_factory=list, description="Strategy steps")


# Update forward references
def _rebuild_models():
    try:
        from app.products.schemas import Product
        from app.shop_points.schemas import ShopPoint
        OfferWithProduct.model_rebuild()
        OfferWithShop.model_rebuild()
        OfferWithDetails.model_rebuild()
    except ImportError:
        pass

_rebuild_models()
