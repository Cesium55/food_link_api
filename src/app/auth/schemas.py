from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegistration(BaseModel):
    """Schema for user registration"""
    email: Optional[EmailStr] = Field(None, description="Email address (required if phone not provided)")
    phone: Optional[str] = Field(None, description="Phone number in format 79... (required if email not provided)")
    password: str = Field(..., min_length=8, max_length=255, description="Password must be between 8 and 255 characters")
    
    @model_validator(mode='after')
    def validate_email_or_phone(self):
        """Validate that either email or phone is provided"""
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")
        if self.email and self.phone:
            raise ValueError("Provide either email or phone, not both")
        return self


class UserLogin(BaseModel):
    """Schema for user login"""
    email: Optional[EmailStr] = Field(None, description="Email address (required if phone not provided)")
    phone: Optional[str] = Field(None, description="Phone number in format 79... (required if email not provided)")
    password: str = Field(..., min_length=8, max_length=255, description="Password must be between 8 and 255 characters")
    
    @model_validator(mode='after')
    def validate_email_or_phone(self):
        """Validate that either email or phone is provided"""
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")
        if self.email and self.phone:
            raise ValueError("Provide either email or phone, not both")
        return self


class VerifyPhoneRequest(BaseModel):
    """Schema for verifying phone with code"""
    code: str = Field(..., min_length=4, max_length=10, description="Verification code")


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: Optional[str]
    phone: Optional[str]
    phone_verified: bool
    is_seller: bool
