from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.support import schemas
from app.support.service import SupportService
from utils.errors_handler import handle_alchemy_error


class SupportManager:
    """Manager for support chat business logic."""

    def __init__(self):
        self.service = SupportService()

    @handle_alchemy_error
    async def get_or_create_master_chat(
        self, session: AsyncSession, user_id: int
    ) -> schemas.MasterChat:
        master_chat = await self.service.get_master_chat_by_user_id(session, user_id)
        if master_chat is None:
            master_chat = await self.service.create_master_chat(session, user_id)
        return schemas.MasterChat.model_validate(master_chat)

    @handle_alchemy_error
    async def get_master_chat_with_messages(
        self, session: AsyncSession, user_id: int
    ) -> schemas.MasterChatWithMessages:
        master_chat_schema = await self.get_or_create_master_chat(session, user_id)
        master_chat_messages = await self.service.get_master_chat_messages(session, user_id)
        master_chat_message_schemas = [
            schemas.MasterChatMessage.model_validate(master_chat_message)
            for master_chat_message in master_chat_messages
        ]
        return schemas.MasterChatWithMessages(
            **master_chat_schema.model_dump(),
            messages=master_chat_message_schemas,
        )

    @handle_alchemy_error
    async def create_master_chat_message(
        self,
        session: AsyncSession,
        user_id: int,
        message_data: schemas.MasterChatMessageCreate,
        sender_type: str = "user",
    ) -> schemas.MasterChatMessage:
        if sender_type not in ("user", "support", "system"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sender_type",
            )

        master_chat = await self.service.get_master_chat_by_user_id(session, user_id)
        if master_chat is None:
            master_chat = await self.service.create_master_chat(session, user_id)

        # Any new user message re-opens the dialog.
        if master_chat.is_closed and sender_type == "user":
            updated_chat = await self.service.set_master_chat_closed(
                session=session,
                user_id=user_id,
                is_closed=False,
            )
            if updated_chat is not None:
                master_chat = updated_chat

        master_chat_message = await self.service.create_master_chat_message(
            session=session,
            user_id=user_id,
            sender_type=sender_type,
            message_text=message_data.message_text,
        )
        return schemas.MasterChatMessage.model_validate(master_chat_message)

    @handle_alchemy_error
    async def mark_master_chat_messages_as_read(
        self, session: AsyncSession, user_id: int
    ) -> schemas.MasterChatMessagesReadResponse:
        updated_count = await self.service.mark_master_chat_messages_as_read_for_user(
            session, user_id
        )
        return schemas.MasterChatMessagesReadResponse(updated_count=updated_count)

    @handle_alchemy_error
    async def set_master_chat_closed(
        self, session: AsyncSession, user_id: int, is_closed: bool
    ) -> schemas.MasterChat:
        master_chat = await self.service.get_master_chat_by_user_id(session, user_id)
        if master_chat is None:
            master_chat = await self.service.create_master_chat(session, user_id)

        updated_master_chat = await self.service.set_master_chat_closed(
            session, user_id, is_closed=is_closed
        )
        if updated_master_chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )
        return schemas.MasterChat.model_validate(updated_master_chat)

    @handle_alchemy_error
    async def get_open_master_chats_page(
        self, session: AsyncSession, page: int = 1, page_size: int = 20
    ) -> schemas.MasterChatAdminChatsPage:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        open_chats, total_count = await self.service.get_open_master_chats_page(
            session=session,
            page=page,
            page_size=page_size,
        )
        items: list[schemas.MasterChatAdminChatListItem] = []
        for master_chat in open_chats:
            user = await self.service.get_master_chat_user(session, master_chat.user_id)
            last_message = await self.service.get_last_master_chat_message(
                session, master_chat.user_id
            )
            unread_count = await self.service.count_unread_user_master_chat_messages(
                session, master_chat.user_id
            )
            items.append(
                schemas.MasterChatAdminChatListItem(
                    user_id=master_chat.user_id,
                    user_email=user.email if user else None,
                    user_phone=user.phone if user else None,
                    is_closed=master_chat.is_closed,
                    updated_at=master_chat.updated_at,
                    last_message_text=(
                        last_message.message_text if last_message is not None else None
                    ),
                    last_message_created_at=(
                        last_message.created_at if last_message is not None else None
                    ),
                    unread_user_messages_count=unread_count,
                )
            )
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        return schemas.MasterChatAdminChatsPage(
            items=items,
            pagination={
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
        )
