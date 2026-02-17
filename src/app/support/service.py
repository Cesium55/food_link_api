from typing import List, Optional

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.support.models import MasterChat, MasterChatMessage


class SupportService:
    """Service for support chat database operations."""

    async def get_master_chat_by_user_id(
        self, session: AsyncSession, user_id: int
    ) -> Optional[MasterChat]:
        result = await session.execute(
            select(MasterChat).where(MasterChat.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_master_chat(self, session: AsyncSession, user_id: int) -> MasterChat:
        result = await session.execute(
            insert(MasterChat).values(user_id=user_id).returning(MasterChat)
        )
        return result.scalar_one()

    async def set_master_chat_closed(
        self, session: AsyncSession, user_id: int, is_closed: bool
    ) -> Optional[MasterChat]:
        result = await session.execute(
            update(MasterChat)
            .where(MasterChat.user_id == user_id)
            .values(is_closed=is_closed)
            .returning(MasterChat)
        )
        return result.scalar_one_or_none()

    async def create_master_chat_message(
        self, session: AsyncSession, user_id: int, sender_type: str, message_text: str
    ) -> MasterChatMessage:
        result = await session.execute(
            insert(MasterChatMessage)
            .values(
                user_id=user_id,
                sender_type=sender_type,
                message_text=message_text,
                is_read=(sender_type == "user"),
            )
            .returning(MasterChatMessage)
        )
        return result.scalar_one()

    async def get_master_chat_messages(
        self, session: AsyncSession, user_id: int
    ) -> List[MasterChatMessage]:
        result = await session.execute(
            select(MasterChatMessage)
            .where(MasterChatMessage.user_id == user_id)
            .order_by(MasterChatMessage.created_at.desc())
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def mark_master_chat_messages_as_read_for_user(
        self, session: AsyncSession, user_id: int
    ) -> int:
        result = await session.execute(
            update(MasterChatMessage)
            .where(
                MasterChatMessage.user_id == user_id,
                MasterChatMessage.is_read.is_(False),
                MasterChatMessage.sender_type != "user",
            )
            .values(is_read=True)
        )
        return result.rowcount or 0
