from typing import List, Optional

from sqlalchemy import insert, select, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
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
        bind = session.get_bind()
        dialect_name = bind.dialect.name if bind is not None else ""

        # Lazy init: create chat only when we are about to write the first message.
        if dialect_name == "postgresql":
            await session.execute(
                pg_insert(MasterChat)
                .values(user_id=user_id)
                .on_conflict_do_nothing(index_elements=[MasterChat.user_id])
            )
        elif dialect_name == "sqlite":
            await session.execute(
                insert(MasterChat)
                .values(user_id=user_id)
                .prefix_with("OR IGNORE")
            )
        else:
            master_chat = await self.get_master_chat_by_user_id(session, user_id)
            if master_chat is None:
                await self.create_master_chat(session, user_id)

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

    async def get_open_master_chats_page(
        self, session: AsyncSession, page: int, page_size: int
    ) -> tuple[List[MasterChat], int]:
        total_count_result = await session.execute(
            select(func.count()).select_from(MasterChat).where(MasterChat.is_closed.is_(False))
        )
        total_count = int(total_count_result.scalar_one() or 0)
        offset = (page - 1) * page_size
        chats_result = await session.execute(
            select(MasterChat)
            .where(MasterChat.is_closed.is_(False))
            .order_by(MasterChat.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(chats_result.scalars().all()), total_count

    async def get_master_chat_user(
        self, session: AsyncSession, user_id: int
    ) -> Optional[User]:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_last_master_chat_message(
        self, session: AsyncSession, user_id: int
    ) -> Optional[MasterChatMessage]:
        result = await session.execute(
            select(MasterChatMessage)
            .where(MasterChatMessage.user_id == user_id)
            .order_by(MasterChatMessage.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_unread_user_master_chat_messages(
        self, session: AsyncSession, user_id: int
    ) -> int:
        result = await session.execute(
            select(func.count())
            .select_from(MasterChatMessage)
            .where(
                MasterChatMessage.user_id == user_id,
                MasterChatMessage.sender_type == "user",
                MasterChatMessage.is_read.is_(False),
            )
        )
        return int(result.scalar_one() or 0)
