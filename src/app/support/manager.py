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

        if master_chat.is_closed and sender_type == "user":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat is closed",
            )

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
