from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MasterChat(BaseModel):
    """Support chat schema."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    is_closed: bool
    created_at: datetime
    updated_at: datetime


class MasterChatMessage(BaseModel):
    """Support chat message schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    sender_type: str
    is_read: bool
    message_text: str
    created_at: datetime
    updated_at: datetime


class MasterChatMessageCreate(BaseModel):
    """Schema for creating support chat message."""

    message_text: str = Field(..., min_length=1)

    @field_validator("message_text")
    @classmethod
    def validate_message_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message text cannot be empty")
        return value


class MasterChatWithMessages(MasterChat):
    """Master chat with messages."""

    messages: List[MasterChatMessage] = Field(default_factory=list)


class MasterChatMessagesReadResponse(BaseModel):
    """Response schema for marking messages as read."""

    updated_count: int


class MasterChatWebSocketIncoming(BaseModel):
    """Incoming master chat websocket message schema."""

    action: Literal["send_message", "mark_read", "ping"]
    message_text: Optional[str] = None

    @model_validator(mode="after")
    def validate_for_action(self):
        if self.action != "send_message":
            return self
        if self.message_text is None:
            raise ValueError("message_text is required for send_message")
        clean_text = self.message_text.strip()
        if not clean_text:
            raise ValueError("message_text cannot be empty")
        self.message_text = clean_text
        return self


class MasterChatWebSocketOutgoing(BaseModel):
    """Outgoing master chat websocket payload schema."""

    event: str
    chat: Optional[MasterChat] = None
    message: Optional[MasterChatMessage] = None
    messages: List[MasterChatMessage] = Field(default_factory=list)
    updated_count: Optional[int] = None
    detail: Optional[str] = None


class MasterChatAdminChatListItem(BaseModel):
    """Single open MasterChat item for admin sidebar list."""

    user_id: int
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    is_closed: bool
    updated_at: datetime
    last_message_text: Optional[str] = None
    last_message_created_at: Optional[datetime] = None
    unread_user_messages_count: int = 0


class MasterChatAdminChatsPage(BaseModel):
    """Paginated admin response for open MasterChat list."""

    items: List[MasterChatAdminChatListItem]
    pagination: dict
