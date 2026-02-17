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
