from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.auth.manager import AuthManager
from app.support import schemas
from app.support.manager import SupportManager
from database import get_async_session
from utils.websocket_manager import KeyedWebSocketManager


class MasterChatWebSocketManager:
    """Support-domain websocket orchestration for MasterChat."""

    def __init__(self) -> None:
        self.auth_manager = AuthManager()
        self.support_manager = SupportManager()
        self.connection_manager = KeyedWebSocketManager()

    @staticmethod
    def extract_access_token(websocket: WebSocket) -> str | None:
        token = websocket.query_params.get("token")
        if token:
            return token

        auth_header = websocket.headers.get("authorization")
        if not auth_header:
            return None
        if not auth_header.lower().startswith("bearer "):
            return None
        return auth_header[7:].strip()

    async def broadcast_master_chat_message(
        self, user_id: int, master_chat_message: schemas.MasterChatMessage
    ) -> None:
        payload = schemas.MasterChatWebSocketOutgoing(
            event="new_message",
            message=master_chat_message,
        ).model_dump()
        await self.connection_manager.broadcast(user_id, payload)

    async def broadcast_master_chat_read_state(
        self, user_id: int, updated_count: int
    ) -> None:
        payload = schemas.MasterChatWebSocketOutgoing(
            event="messages_read",
            updated_count=updated_count,
        ).model_dump()
        await self.connection_manager.broadcast(user_id, payload)

    async def broadcast_master_chat_updated(
        self, user_id: int, master_chat: schemas.MasterChat
    ) -> None:
        payload = schemas.MasterChatWebSocketOutgoing(
            event="chat_updated",
            chat=master_chat,
        ).model_dump()
        await self.connection_manager.broadcast(user_id, payload)

    async def handle_master_chat_websocket(self, websocket: WebSocket) -> None:
        token = self.extract_access_token(websocket)
        if not token:
            await websocket.close(code=1008, reason="Missing access token")
            return

        async with get_async_session() as session:
            try:
                current_user = await self.auth_manager.get_current_user_by_token(
                    session, token
                )
            except HTTPException:
                await websocket.close(code=1008, reason="Invalid access token")
                return

        await self.connection_manager.connect(current_user.id, websocket)

        try:
            async with get_async_session() as session:
                master_chat_state = await self.support_manager.get_master_chat_with_messages(
                    session=session,
                    user_id=current_user.id,
                )

            await websocket.send_json(
                schemas.MasterChatWebSocketOutgoing(
                    event="chat_state",
                    chat=schemas.MasterChat(
                        user_id=master_chat_state.user_id,
                        is_closed=master_chat_state.is_closed,
                        created_at=master_chat_state.created_at,
                        updated_at=master_chat_state.updated_at,
                    ),
                    messages=master_chat_state.messages,
                ).model_dump()
            )

            while True:
                raw_payload = await websocket.receive_json()
                try:
                    incoming_payload = schemas.MasterChatWebSocketIncoming.model_validate(
                        raw_payload
                    )
                except ValidationError as exc:
                    await websocket.send_json(
                        schemas.MasterChatWebSocketOutgoing(
                            event="error",
                            detail=str(exc),
                        ).model_dump()
                    )
                    continue

                if incoming_payload.action == "ping":
                    await websocket.send_json(
                        schemas.MasterChatWebSocketOutgoing(event="pong").model_dump()
                    )
                    continue

                if incoming_payload.action == "mark_read":
                    async with get_async_session() as session:
                        read_result = await self.support_manager.mark_master_chat_messages_as_read(
                            session=session,
                            user_id=current_user.id,
                        )
                    await self.broadcast_master_chat_read_state(
                        user_id=current_user.id,
                        updated_count=read_result.updated_count,
                    )
                    continue

                async with get_async_session() as session:
                    created_master_chat_message = await self.support_manager.create_master_chat_message(
                        session=session,
                        user_id=current_user.id,
                        message_data=schemas.MasterChatMessageCreate(
                            message_text=incoming_payload.message_text or ""
                        ),
                        sender_type="user",
                    )
                await self.broadcast_master_chat_message(
                    user_id=current_user.id,
                    master_chat_message=created_master_chat_message,
                )

        except WebSocketDisconnect:
            await self.connection_manager.disconnect(current_user.id, websocket)
        except Exception:
            await self.connection_manager.disconnect(current_user.id, websocket)
            try:
                await websocket.close(code=1011, reason="Internal websocket error")
            except Exception:
                pass
