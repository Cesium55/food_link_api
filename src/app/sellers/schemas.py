from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, EmailStr, model_validator, ConfigDict
import re

if TYPE_CHECKING:
    from app.shop_points.schemas import ShopPoint
    from app.products.schemas import Product


class SellerImage(BaseModel):
    """Schema for seller image"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier")
    path: str = Field(
        ..., min_length=1, max_length=2048, description="Path to image"
    )
    order: int = Field(0, ge=0, description="Image display order")


class SellerBase(BaseModel):
    """Base schema for seller"""

    full_name: str = Field(..., min_length=1, max_length=1000, description="Full name")
    short_name: str = Field(..., min_length=1, max_length=255, description="Short name")
    description: Optional[str] = Field(default=None, description="Seller description")
    inn: str = Field(..., min_length=10, max_length=12, description="INN")
    is_IP: bool = Field(..., description="Is Individual Entrepreneur")
    ogrn: str = Field(..., min_length=13, max_length=15, description="OGRN")
    status: int = Field(..., ge=0, description="Status")
    verification_level: int = Field(..., ge=0, description="Verification level")
    registration_doc_url: str = Field(default="", max_length=2048, description="Registration document URL")

    @model_validator(mode='after')
    def validate_inn_ogrn(self):
        """Validate INN and OGRN format based on organization type"""
        if self.is_IP:
            if not re.match(r'^\d{12}$', self.inn):
                raise ValueError('ИНН для ИП должен содержать 12 цифр')
            if not re.match(r'^\d{15}$', self.ogrn):
                raise ValueError('ОГРНИП для ИП должен содержать 15 цифр')
        else:
            if not re.match(r'^\d{10}$', self.inn):
                raise ValueError('ИНН для юридического лица должен содержать 10 цифр')
            if not re.match(r'^\d{13}$', self.ogrn):
                raise ValueError('ОГРН для юридического лица должен содержать 13 цифр')
        return self


class SellerCreate(BaseModel):
    """Schema for creating seller with only required fields"""

    full_name: str = Field(..., min_length=1, max_length=1000, description="Full name")
    short_name: str = Field(..., min_length=1, max_length=255, description="Short name")
    description: Optional[str] = Field(default=None, description="Seller description")
    inn: str = Field(..., min_length=10, max_length=12, description="INN")
    is_IP: bool = Field(..., description="Is Individual Entrepreneur")
    ogrn: str = Field(..., min_length=13, max_length=15, description="OGRN")

    @model_validator(mode='after')
    def validate_inn_ogrn(self):
        """Validate INN and OGRN format based on organization type"""
        if self.is_IP:
            if not re.match(r'^\d{12}$', self.inn):
                raise ValueError('ИНН для ИП должен содержать 12 цифр')
            if not re.match(r'^\d{15}$', self.ogrn):
                raise ValueError('ОГРНИП для ИП должен содержать 15 цифр')
        else:
            if not re.match(r'^\d{10}$', self.inn):
                raise ValueError('ИНН для юридического лица должен содержать 10 цифр')
            if not re.match(r'^\d{13}$', self.ogrn):
                raise ValueError('ОГРН для юридического лица должен содержать 13 цифр')
        return self



class SellerUpdate(BaseModel):
    """Schema for updating seller"""

    full_name: Optional[str] = Field(None, min_length=1, max_length=1000, description="Полное название организации")
    short_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название")
    description: Optional[str] = Field(None, description="Описание продавца")
    inn: Optional[str] = Field(None, min_length=10, max_length=12, description="ИНН")
    is_IP: Optional[bool] = Field(None, description="Индивидуальный предпрениматель?")
    ogrn: Optional[str] = Field(None, min_length=13, max_length=15, description="ОГРН \ ОГРНИП")
    email: Optional[EmailStr] = Field(None, description="Email")
    phone: Optional[str] = Field(None, min_length=1, max_length=20, description="Phone number")
    status: Optional[int] = Field(None, ge=0, description="Status")
    verification_level: Optional[int] = Field(None, ge=0, description="Verification level")
    registration_doc_url: Optional[str] = Field(None, min_length=1, max_length=2048, description="Registration document URL")


class Seller(SellerBase):
    """Schema for displaying seller"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier")
    master_id: int = Field(..., description="Master ID")
    email: str = Field(..., description="Email")
    phone: Optional[str] = Field(None, description="Phone number")
    balance: float = Field(..., description="Account balance")
    images: List[SellerImage] = Field(
        default_factory=list, description="Seller images"
    )


class PublicSeller(BaseModel):
    """Public schema for displaying seller (without sensitive data)"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier")
    short_name: str = Field(..., min_length=1, max_length=255, description="Short name")
    full_name: str = Field(..., min_length=1, max_length=1000, description="Full name")
    description: Optional[str] = Field(default=None, description="Seller description")
    is_IP: bool = Field(..., description="Is Individual Entrepreneur")
    status: int = Field(..., ge=0, description="Status")
    verification_level: int = Field(..., ge=0, description="Verification level")
    images: List[SellerImage] = Field(
        default_factory=list, description="Seller images"
    )


class SellerWithShopPoints(Seller):
    """Seller schema with shop points"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Seller shop points"
    )


class SellerWithDetails(Seller):
    """Seller schema with full information"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Seller shop points"
    )
    products: List["Product"] = Field(
        default_factory=list, description="Seller products"
    )


class PublicSellerWithShopPoints(PublicSeller):
    """Public seller schema with shop points (without sensitive data)"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Seller shop points"
    )


class PublicSellerWithDetails(PublicSeller):
    """Public seller schema with full information (without sensitive data)"""

    shop_points: List["ShopPoint"] = Field(
        default_factory=list, description="Seller shop points"
    )
    products: List["Product"] = Field(
        default_factory=list, description="Seller products"
    )


class SellerFirebaseTokenUpdate(BaseModel):
    """Schema for updating seller firebase token"""

    firebase_token: str = Field(..., min_length=1, max_length=500, description="Firebase FCM token")


class SellerRegistrationRequestStatus(str, Enum):
    PENDING = "pending"
    REJECTED = "rejected"
    APPROVED = "approved"


class SellerRegistrationRequestBase(BaseModel):
    """Base schema for seller registration requests."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=1000, description="Full name")
    short_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Short name")
    description: Optional[str] = Field(None, description="Seller description")
    inn: Optional[str] = Field(None, min_length=10, max_length=12, description="INN")
    is_IP: Optional[bool] = Field(None, description="Is Individual Entrepreneur")
    ogrn: Optional[str] = Field(None, min_length=13, max_length=15, description="OGRN")
    terms_accepted: bool = Field(False, description="Terms accepted flag")

    @model_validator(mode='after')
    def validate_inn_ogrn(self):
        """Validate INN and OGRN only when all required fields are provided."""
        if self.is_IP is None or self.inn is None or self.ogrn is None:
            return self
        if self.is_IP:
            if not re.match(r'^\d{12}$', self.inn):
                raise ValueError('ИНН для ИП должен содержать 12 цифр')
            if not re.match(r'^\d{15}$', self.ogrn):
                raise ValueError('ОГРНИП для ИП должен содержать 15 цифр')
        else:
            if not re.match(r'^\d{10}$', self.inn):
                raise ValueError('ИНН для юридического лица должен содержать 10 цифр')
            if not re.match(r'^\d{13}$', self.ogrn):
                raise ValueError('ОГРН для юридического лица должен содержать 13 цифр')
        return self


class SellerRegistrationRequestCreate(SellerRegistrationRequestBase):
    """Schema for creating seller registration request."""


class SellerRegistrationRequestUpdate(SellerRegistrationRequestBase):
    """Schema for updating seller registration request."""


class SellerRegistrationRequest(BaseModel):
    """Schema for displaying seller registration request."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier")
    user_id: int = Field(..., description="User ID")
    full_name: Optional[str] = Field(None, description="Full name")
    short_name: Optional[str] = Field(None, description="Short name")
    description: Optional[str] = Field(None, description="Seller description")
    inn: Optional[str] = Field(None, description="INN")
    is_IP: Optional[bool] = Field(None, description="Is Individual Entrepreneur")
    ogrn: Optional[str] = Field(None, description="OGRN")
    status: SellerRegistrationRequestStatus = Field(
        ..., description="Request status"
    )
    terms_accepted: bool = Field(..., description="Terms accepted flag")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")


class SellerSummary(BaseModel):
    """Sellers summary schema"""

    total_sellers: int = Field(..., description="Total number of sellers")
    total_products: int = Field(..., description="Total number of products from sellers")
    avg_products_per_seller: float = Field(
        ..., description="Average number of products per seller"
    )


# Update forward references
def _rebuild_models():
    try:
        from app.shop_points.schemas import ShopPoint
        from app.products.schemas import Product

        SellerWithShopPoints.model_rebuild()
        SellerWithDetails.model_rebuild()
        PublicSellerWithShopPoints.model_rebuild()
        PublicSellerWithDetails.model_rebuild()
    except ImportError:
        pass


_rebuild_models()
