"""
Unit tests for support domain.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.support import schemas
from app.support.manager import SupportManager
from app.support.master_chat_ws_manager import MasterChatWebSocketManager
from app.support.models import MasterChat, MasterChatMessage
from app.support.service import SupportService


TEST_USER_ID = 1
TEST_MESSAGE_ID = 10


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def support_service():
    return SupportService()


@pytest.fixture
def support_manager():
    return SupportManager()


def create_mock_execute_result(return_value, scalar_method: str = "scalar_one"):
    result = Mock()
    getattr(result, scalar_method).return_value = return_value
    return result


def create_mock_scalars_result(return_value_list):
    result = Mock()
    scalars = Mock()
    scalars.all.return_value = return_value_list
    result.scalars.return_value = scalars
    return result


def create_master_chat(
    user_id: int = TEST_USER_ID,
    is_closed: bool = False,
):
    obj = Mock(spec=MasterChat)
    obj.user_id = user_id
    obj.is_closed = is_closed
    obj.created_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    return obj


def create_master_chat_message(
    message_id: int = TEST_MESSAGE_ID,
    user_id: int = TEST_USER_ID,
    sender_type: str = "user",
    is_read: bool = False,
    message_text: str = "hello",
):
    obj = Mock(spec=MasterChatMessage)
    obj.id = message_id
    obj.user_id = user_id
    obj.sender_type = sender_type
    obj.is_read = is_read
    obj.message_text = message_text
    obj.created_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    return obj


class TestSupportSchemas:
    def test_master_chat_message_create_trims_text(self):
        data = schemas.MasterChatMessageCreate(message_text="  hello  ")
        assert data.message_text == "hello"

    def test_master_chat_message_create_rejects_empty_text(self):
        with pytest.raises(ValidationError):
            schemas.MasterChatMessageCreate(message_text="   ")

    def test_ws_incoming_send_message_requires_message_text(self):
        with pytest.raises(ValidationError):
            schemas.MasterChatWebSocketIncoming(action="send_message")

    def test_ws_incoming_send_message_trims_message_text(self):
        data = schemas.MasterChatWebSocketIncoming(
            action="send_message", message_text="  ping  "
        )
        assert data.message_text == "ping"

    def test_ws_incoming_mark_read_without_message_text(self):
        data = schemas.MasterChatWebSocketIncoming(action="mark_read")
        assert data.action == "mark_read"


class TestSupportService:
    @pytest.mark.asyncio
    async def test_get_master_chat_by_user_id_found(self, support_service, mock_session):
        master_chat = create_master_chat()
        mock_session.execute.return_value = create_mock_execute_result(
            master_chat, "scalar_one_or_none"
        )

        result = await support_service.get_master_chat_by_user_id(mock_session, TEST_USER_ID)

        assert result is master_chat
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_master_chat(self, support_service, mock_session):
        master_chat = create_master_chat()
        mock_session.execute.return_value = create_mock_execute_result(master_chat)

        result = await support_service.create_master_chat(mock_session, TEST_USER_ID)

        assert result is master_chat
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_master_chat_closed(self, support_service, mock_session):
        master_chat = create_master_chat(is_closed=True)
        mock_session.execute.return_value = create_mock_execute_result(
            master_chat, "scalar_one_or_none"
        )

        result = await support_service.set_master_chat_closed(
            mock_session, TEST_USER_ID, True
        )

        assert result is master_chat
        assert result.is_closed is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_master_chat_message(self, support_service, mock_session):
        master_chat_message = create_master_chat_message()
        mock_session.execute.return_value = create_mock_execute_result(master_chat_message)

        result = await support_service.create_master_chat_message(
            mock_session, TEST_USER_ID, "user", "hello"
        )

        assert result is master_chat_message
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_master_chat_messages_reversed(self, support_service, mock_session):
        m1 = create_master_chat_message(message_id=1)
        m2 = create_master_chat_message(message_id=2)
        m3 = create_master_chat_message(message_id=3)
        mock_session.execute.return_value = create_mock_scalars_result([m3, m2, m1])

        result = await support_service.get_master_chat_messages(mock_session, TEST_USER_ID)

        assert [m.id for m in result] == [1, 2, 3]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_master_chat_messages_as_read_for_user(self, support_service, mock_session):
        exec_result = Mock()
        exec_result.rowcount = 3
        mock_session.execute.return_value = exec_result

        updated_count = await support_service.mark_master_chat_messages_as_read_for_user(
            mock_session, TEST_USER_ID
        )

        assert updated_count == 3
        mock_session.execute.assert_called_once()


class TestSupportManager:
    @pytest.mark.asyncio
    async def test_get_or_create_master_chat_existing(self, support_manager, mock_session):
        master_chat = create_master_chat()
        support_manager.service.get_master_chat_by_user_id = AsyncMock(return_value=master_chat)
        support_manager.service.create_master_chat = AsyncMock()

        result = await support_manager.get_or_create_master_chat(mock_session, TEST_USER_ID)

        assert isinstance(result, schemas.MasterChat)
        assert result.user_id == TEST_USER_ID
        support_manager.service.create_master_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_master_chat_creates_if_missing(self, support_manager, mock_session):
        master_chat = create_master_chat()
        support_manager.service.get_master_chat_by_user_id = AsyncMock(return_value=None)
        support_manager.service.create_master_chat = AsyncMock(return_value=master_chat)

        result = await support_manager.get_or_create_master_chat(mock_session, TEST_USER_ID)

        assert isinstance(result, schemas.MasterChat)
        support_manager.service.create_master_chat.assert_called_once_with(
            mock_session, TEST_USER_ID
        )

    @pytest.mark.asyncio
    async def test_create_master_chat_message_invalid_sender_type(self, support_manager, mock_session):
        with pytest.raises(HTTPException) as exc:
            await support_manager.create_master_chat_message(
                session=mock_session,
                user_id=TEST_USER_ID,
                message_data=schemas.MasterChatMessageCreate(message_text="hello"),
                sender_type="invalid",
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_master_chat_message_reopens_chat_for_user_message(self, support_manager, mock_session):
        closed_chat = create_master_chat(is_closed=True)
        created_message = create_master_chat_message(message_text="hello")
        support_manager.service.get_master_chat_by_user_id = AsyncMock(return_value=closed_chat)
        support_manager.service.set_master_chat_closed = AsyncMock(return_value=create_master_chat(is_closed=False))
        support_manager.service.create_master_chat_message = AsyncMock(return_value=created_message)

        result = await support_manager.create_master_chat_message(
            session=mock_session,
            user_id=TEST_USER_ID,
            message_data=schemas.MasterChatMessageCreate(message_text="hello"),
            sender_type="user",
        )

        assert isinstance(result, schemas.MasterChatMessage)
        support_manager.service.set_master_chat_closed.assert_called_once_with(
            session=mock_session,
            user_id=TEST_USER_ID,
            is_closed=False,
        )
        support_manager.service.create_master_chat_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_master_chat_message_creates_chat_if_missing(self, support_manager, mock_session):
        open_chat = create_master_chat(is_closed=False)
        created_message = create_master_chat_message(message_text="hello")
        support_manager.service.get_master_chat_by_user_id = AsyncMock(side_effect=[None, open_chat])
        support_manager.service.create_master_chat = AsyncMock(return_value=open_chat)
        support_manager.service.create_master_chat_message = AsyncMock(return_value=created_message)

        result = await support_manager.create_master_chat_message(
            session=mock_session,
            user_id=TEST_USER_ID,
            message_data=schemas.MasterChatMessageCreate(message_text="  hello "),
            sender_type="user",
        )

        assert isinstance(result, schemas.MasterChatMessage)
        support_manager.service.create_master_chat.assert_called_once_with(
            mock_session, TEST_USER_ID
        )
        support_manager.service.create_master_chat_message.assert_called_once_with(
            session=mock_session,
            user_id=TEST_USER_ID,
            sender_type="user",
            message_text="hello",
        )

    @pytest.mark.asyncio
    async def test_mark_master_chat_messages_as_read(self, support_manager, mock_session):
        support_manager.service.mark_master_chat_messages_as_read_for_user = AsyncMock(
            return_value=5
        )

        result = await support_manager.mark_master_chat_messages_as_read(
            mock_session, TEST_USER_ID
        )

        assert result.updated_count == 5

    @pytest.mark.asyncio
    async def test_set_master_chat_closed_not_found(self, support_manager, mock_session):
        support_manager.service.get_master_chat_by_user_id = AsyncMock(
            return_value=create_master_chat()
        )
        support_manager.service.set_master_chat_closed = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await support_manager.set_master_chat_closed(
                mock_session, TEST_USER_ID, True
            )
        assert exc.value.status_code == 404


class TestMasterChatWebSocketManager:
    def test_extract_access_token_from_query(self):
        websocket = SimpleNamespace(
            query_params={"token": "abc"},
            headers={},
        )
        token = MasterChatWebSocketManager.extract_access_token(websocket)
        assert token == "abc"

    def test_extract_access_token_from_header(self):
        websocket = SimpleNamespace(
            query_params={},
            headers={"authorization": "Bearer test-token"},
        )
        token = MasterChatWebSocketManager.extract_access_token(websocket)
        assert token == "test-token"

    def test_extract_access_token_missing(self):
        websocket = SimpleNamespace(query_params={}, headers={})
        token = MasterChatWebSocketManager.extract_access_token(websocket)
        assert token is None

    @pytest.mark.asyncio
    async def test_broadcast_master_chat_message(self):
        manager = MasterChatWebSocketManager()
        manager.connection_manager.broadcast = AsyncMock()
        message = schemas.MasterChatMessage(
            id=1,
            user_id=TEST_USER_ID,
            sender_type="user",
            is_read=False,
            message_text="hello",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await manager.broadcast_master_chat_message(TEST_USER_ID, message)

        manager.connection_manager.broadcast.assert_called_once()
        args = manager.connection_manager.broadcast.call_args[0]
        assert args[0] == TEST_USER_ID
        assert args[1]["event"] == "new_message"

    @pytest.mark.asyncio
    async def test_handle_master_chat_websocket_rejects_when_token_missing(self):
        manager = MasterChatWebSocketManager()
        websocket = AsyncMock()
        websocket.query_params = {}
        websocket.headers = {}

        await manager.handle_master_chat_websocket(websocket)

        websocket.close.assert_awaited_once()
        close_kwargs = websocket.close.call_args.kwargs
        assert close_kwargs["code"] == 1008
