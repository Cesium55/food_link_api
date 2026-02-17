from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from app.auth.models import User


class MasterChat(Base):
    """Main support chat model."""

    __tablename__ = "master_chats"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True
    )
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User")
    messages: Mapped[List["MasterChatMessage"]] = relationship(
        "MasterChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )


class MasterChatMessage(Base):
    """Support chat message model."""

    __tablename__ = "master_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("master_chats.user_id"), nullable=False, index=True
    )
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('user', 'support', 'system')",
            name="ck_master_chat_message_sender_type_valid",
        ),
        CheckConstraint(
            "length(message_text) >= 1",
            name="ck_master_chat_message_text_min_length",
        ),
    )

    chat: Mapped["MasterChat"] = relationship(
        "MasterChat", back_populates="messages"
    )
