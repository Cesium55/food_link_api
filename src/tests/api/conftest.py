"""
Test configuration for API tests with in-memory database
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import uuid as uuid_module

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth.models import RefreshToken, User
import database
import middleware.insert_session_middleware as middleware_module
from database import get_async_session
from main import app
from models import Base
import logger


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)


class GUID(TypeDecorator):
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid_module.UUID):
                return str(value)
            return str(value) if value else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, (str, bytes)):
                try:
                    return uuid_module.UUID(str(value))
                except (ValueError, AttributeError):
                    return value
            return value


TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function")
async def test_db():
    original_type = RefreshToken.__table__.columns['token'].type
    RefreshToken.__table__.columns['token'].type = GUID()
    
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        RefreshToken.__table__.columns['token'].type = original_type


@pytest.fixture(scope="function")
async def test_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def override_get_async_session(test_session):
    original_get_async_session = get_async_session
    
    @asynccontextmanager
    async def _get_test_session():
        yield test_session
    
    database.get_async_session = _get_test_session
    middleware_module.get_async_session = _get_test_session
    
    yield
    
    database.get_async_session = original_get_async_session
    middleware_module.get_async_session = original_get_async_session


@pytest.fixture(scope="function")
async def client(override_get_async_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
def mock_loggers():
    mock_log = MagicMock()
    mock_sync_log = MagicMock()
    
    with patch('logger.get_logger', return_value=mock_log), \
         patch('logger.get_sync_logger', return_value=mock_sync_log):
        yield


@pytest.fixture
def mock_settings():
    with patch('app.auth.manager.settings') as mock_settings:
        mock_settings.auth_enable_email = True
        mock_settings.auth_enable_phone = True
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_secret_key = "test-secret-key-for-testing-only"
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.jwt_refresh_token_expire_days = 30
        yield mock_settings


@pytest.fixture
def mock_sms_manager():
    with patch('app.auth.manager.create_exolve_sms_manager') as mock_sms:
        mock_sms_manager = AsyncMock()
        mock_sms_manager.__aenter__ = AsyncMock(return_value=mock_sms_manager)
        mock_sms_manager.__aexit__ = AsyncMock(return_value=None)
        mock_sms_manager.send_verification_code = AsyncMock(return_value="1234")
        mock_sms.return_value = mock_sms_manager
        yield mock_sms_manager


@pytest.fixture
def mock_redis_verification_code():
    stored_codes = {}
    
    async def mock_store(phone: str, code: str, expire_seconds: int = 300):
        stored_codes[phone] = code
    
    async def mock_verify(phone: str, code: str) -> bool:
        return stored_codes.get(phone) == code
    
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=lambda key: stored_codes.get(key.replace('verification_code:', '')))
    mock_redis.delete = AsyncMock()
    
    async def mock_get_redis():
        return mock_redis
    
    with patch('app.auth.manager.store_verification_code', side_effect=mock_store), \
         patch('app.auth.manager.verify_code', side_effect=mock_verify), \
         patch('utils.redis.verification_codes.verify_code', side_effect=mock_verify), \
         patch('utils.redis.verification_codes.store_verification_code', side_effect=mock_store), \
         patch('utils.redis.client.get_redis_client', side_effect=mock_get_redis):
        yield stored_codes


@pytest.fixture
def mock_image_manager_init():
    with patch('main.ImageManager') as mock_im:
        mock_instance = MagicMock()
        mock_instance.initialize_bucket = AsyncMock()
        mock_im.return_value = mock_instance
        yield mock_instance


def pytest_sessionfinish(session, exitstatus):
    try:
        for logger_instance in list(logger._loggers.values()):
            if hasattr(logger_instance, '_task') and logger_instance._task and not logger_instance._task.done():
                try:
                    logger_instance._task.cancel()
                except Exception:
                    pass
        logger._loggers.clear()
    except Exception:
        pass
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_engine.dispose())
        finally:
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in tasks:
                task.cancel()
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()
    except Exception:
        pass
