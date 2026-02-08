from models import Base
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, Double
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from app.purchases.models import Purchase


class User(Base):
    """User model for mobile app authentication"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_seller: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firebase_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_latitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True, comment="Last known latitude coordinate of the user")
    last_longitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True, comment="Last known longitude coordinate of the user")

    purchases: Mapped[List["Purchase"]] = relationship(
        "Purchase", back_populates="user"
    )

    def __str__(self):
        return f"User(id={self.id}, email={self.email}, phone={self.phone}, is_seller={self.is_seller})"


class RefreshToken(Base):
    """Refresh token model"""

    __tablename__ = "refresh_tokens"
 
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

