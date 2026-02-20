from fastapi import APIRouter, Depends, Request, WebSocket

from app.auth.models import User
from app.support import schemas
from app.support.master_chat_ws_manager import MasterChatWebSocketManager
from app.support.manager import SupportManager
from utils.auth_dependencies import get_current_user

router = APIRouter(prefix="/support", tags=["support"])

support_manager = SupportManager()
master_chat_ws_manager = MasterChatWebSocketManager()


@router.get("/master-chat", response_model=schemas.MasterChatWithMessages)
async def get_master_chat(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    session = request.state.session
    return await support_manager.get_master_chat_with_messages(
        session=session,
        user_id=current_user.id,
    )


@router.post("/master-chat/messages", response_model=schemas.MasterChatMessage, status_code=201)
async def create_master_chat_message(
    request: Request,
    message_data: schemas.MasterChatMessageCreate,
    current_user: User = Depends(get_current_user),
):
    session = request.state.session
    master_chat_message = await support_manager.create_master_chat_message(
        session=session,
        user_id=current_user.id,
        message_data=message_data,
        sender_type="user",
    )
    await master_chat_ws_manager.broadcast_master_chat_message(
        user_id=current_user.id,
        master_chat_message=master_chat_message,
    )
    updated_master_chat = await support_manager.get_or_create_master_chat(
        session=session,
        user_id=current_user.id,
    )
    await master_chat_ws_manager.broadcast_master_chat_updated(
        user_id=current_user.id,
        master_chat=updated_master_chat,
    )
    return master_chat_message


@router.post("/master-chat/messages/read", response_model=schemas.MasterChatMessagesReadResponse)
async def mark_master_chat_messages_as_read(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    session = request.state.session
    mark_read_result = await support_manager.mark_master_chat_messages_as_read(
        session=session,
        user_id=current_user.id,
    )
    await master_chat_ws_manager.broadcast_master_chat_read_state(
        user_id=current_user.id,
        updated_count=mark_read_result.updated_count,
    )
    return mark_read_result

@router.websocket("/master-chat/ws")
async def support_ws(websocket: WebSocket):
    await master_chat_ws_manager.handle_master_chat_websocket(websocket)


@router.get("/master-chat/admin/chats", response_model=schemas.MasterChatAdminChatsPage)
async def get_master_chat_admin_chats_page(
    request: Request,
    page: int = 1,
    page_size: int = 20,
):
    session = request.state.session
    return await support_manager.get_open_master_chats_page(
        session=session,
        page=page,
        page_size=page_size,
    )


@router.get("/master-chat/admin/chats/{user_id}", response_model=schemas.MasterChatWithMessages)
async def get_master_chat_admin_chat(
    request: Request,
    user_id: int,
):
    session = request.state.session
    return await support_manager.get_master_chat_with_messages(
        session=session,
        user_id=user_id,
    )


@router.post("/master-chat/admin/chats/{user_id}/messages", response_model=schemas.MasterChatMessage, status_code=201)
async def create_master_chat_admin_message(
    request: Request,
    user_id: int,
    message_data: schemas.MasterChatMessageCreate,
):
    session = request.state.session
    master_chat_message = await support_manager.create_master_chat_message(
        session=session,
        user_id=user_id,
        message_data=message_data,
        sender_type="support",
    )
    await master_chat_ws_manager.broadcast_master_chat_message(
        user_id=user_id,
        master_chat_message=master_chat_message,
    )
    updated_master_chat = await support_manager.get_or_create_master_chat(
        session=session,
        user_id=user_id,
    )
    await master_chat_ws_manager.broadcast_master_chat_updated(
        user_id=user_id,
        master_chat=updated_master_chat,
    )
    return master_chat_message


@router.post("/master-chat/admin/chats/{user_id}/close", response_model=schemas.MasterChat)
async def close_master_chat_admin_chat(
    request: Request,
    user_id: int,
):
    session = request.state.session
    updated_master_chat = await support_manager.set_master_chat_closed(
        session=session,
        user_id=user_id,
        is_closed=True,
    )
    await master_chat_ws_manager.broadcast_master_chat_updated(
        user_id=user_id,
        master_chat=updated_master_chat,
    )
    return updated_master_chat


@router.websocket("/master-chat/admin/ws")
async def master_chat_admin_ws(websocket: WebSocket):
    await master_chat_ws_manager.handle_master_chat_admin_websocket(websocket)
