from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
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
    inn: str = Field(..., min_length=10, max_length=12, description="INN")
    is_IP: bool = Field(..., description="Is Individual Entrepreneur")
    ogrn: str = Field(..., min_length=13, max_length=15, description="OGRN")
    status: int = Field(..., ge=0, description="Status")
    verification_level: int = Field(..., ge=0, description="Verification level")
    registration_doc_url: str = Field(default="", max_length=2048, description="Registration document URL")

    @field_validator('inn')
    @classmethod
    def validate_inn(cls, v, info):
        """Validate INN format based on organization type"""
        is_IP = info.data.get('is_IP')
        
        if is_IP:
            # ИП: ИНН должен быть 12 цифр
            if not re.match(r'^\d{12}$', v):
                raise ValueError('ИНН для ИП должен содержать 12 цифр')
        else:
            # Юридические лица: ИНН должен быть 10 цифр
            if not re.match(r'^\d{10}$', v):
                raise ValueError('ИНН для юридического лица должен содержать 10 цифр')
        return v

    @field_validator('ogrn')
    @classmethod
    def validate_ogrn(cls, v, info):
        """Validate OGRN format based on organization type"""
        is_IP = info.data.get('is_IP')
        
        if is_IP:
            # ИП: ОГРНИП должен быть 15 цифр
            if not re.match(r'^\d{15}$', v):
                raise ValueError('ОГРНИП для ИП должен содержать 15 цифр')
        else:
            # Юридические лица: ОГРН должен быть 13 цифр
            if not re.match(r'^\d{13}$', v):
                raise ValueError('ОГРН для юридического лица должен содержать 13 цифр')
        return v


class SellerCreate(BaseModel):
    """Schema for creating seller with only required fields"""

    full_name: str = Field(..., min_length=1, max_length=1000, description="Full name")
    short_name: str = Field(..., min_length=1, max_length=255, description="Short name")
    inn: str = Field(..., min_length=10, max_length=12, description="INN")
    is_IP: bool = Field(..., description="Is Individual Entrepreneur")
    ogrn: str = Field(..., min_length=13, max_length=15, description="OGRN")

    @field_validator('inn')
    @classmethod
    def validate_inn(cls, v, info):
        """Validate INN format based on organization type"""
        is_IP = info.data.get('is_IP')
        
        if is_IP:
            # ИП: ИНН должен быть 12 цифр
            if not re.match(r'^\d{12}$', v):
                raise ValueError('ИНН для ИП должен содержать 12 цифр')
        else:
            # Юридические лица: ИНН должен быть 10 цифр
            if not re.match(r'^\d{10}$', v):
                raise ValueError('ИНН для юридического лица должен содержать 10 цифр')
        return v

    @field_validator('ogrn')
    @classmethod
    def validate_ogrn(cls, v, info):
        """Validate OGRN format based on organization type"""
        is_IP = info.data.get('is_IP')
        
        if is_IP:
            # ИП: ОГРНИП должен быть 15 цифр
            if not re.match(r'^\d{15}$', v):
                raise ValueError('ОГРНИП для ИП должен содержать 15 цифр')
        else:
            # Юридические лица: ОГРН должен быть 13 цифр
            if not re.match(r'^\d{13}$', v):
                raise ValueError('ОГРН для юридического лица должен содержать 13 цифр')
        return v



class SellerUpdate(BaseModel):
    """Schema for updating seller"""

    full_name: Optional[str] = Field(None, min_length=1, max_length=1000, description="Полное название организации")
    short_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название")
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
    except ImportError:
        pass


_rebuild_models()
