"""Test configuration for API tests with temporary Docker PostgreSQL."""

import asyncio
import os
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncpg
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import database
import logger
import middleware.insert_session_middleware as middleware_module
from database import get_async_session
from main import app
from models import Base


POSTGRES_IMAGE = os.getenv("TEST_POSTGRES_IMAGE", "postgres:16-alpine")
TEST_DB_USER = os.getenv("TEST_DB_USER", "test_user")
TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", "test_password")
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "test_db")
STARTUP_TIMEOUT_SECONDS = int(os.getenv("TEST_POSTGRES_STARTUP_TIMEOUT", "60"))
CONNECTION_RETRIES = 10
CONNECTION_DELAY_SECONDS = 1


def _run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _parse_host_port(raw: str) -> int:
    # docker port output format: "0.0.0.0:32775" or ":::32775"
    line = raw.strip().splitlines()[0].strip()
    return int(line.rsplit(":", 1)[1])


def _wait_for_postgres(container_name: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = _run_cmd(
            [
                "docker",
                "exec",
                container_name,
                "pg_isready",
                "-U",
                TEST_DB_USER,
                "-d",
                TEST_DB_NAME,
            ],
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)

    raise RuntimeError(
        f"PostgreSQL container did not become ready within {timeout_seconds}s."
    )


async def _check_host_connection(host_port: int) -> None:
    conn = await asyncpg.connect(
        host="127.0.0.1",
        port=host_port,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database=TEST_DB_NAME,
        timeout=3,
    )
    try:
        await conn.execute("SELECT 1")
    finally:
        await conn.close()


def _verify_host_connection_with_retries(
    host_port: int,
    retries: int = CONNECTION_RETRIES,
    delay_seconds: int = CONNECTION_DELAY_SECONDS,
) -> None:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_check_host_connection(host_port))
            return
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay_seconds)
        finally:
            loop.close()

    raise RuntimeError(
        f"Cannot connect to PostgreSQL at 127.0.0.1:{host_port} after "
        f"{retries} attempts (delay={delay_seconds}s). Last error: {last_error}"
    )


@pytest.fixture(scope="session")
def postgres_container():
    """Start and stop ephemeral PostgreSQL container for test session."""
    container_name = f"food-link-api-test-db-{uuid.uuid4().hex[:8]}"

    try:
        _run_cmd(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                container_name,
                "-e",
                f"POSTGRES_USER={TEST_DB_USER}",
                "-e",
                f"POSTGRES_PASSWORD={TEST_DB_PASSWORD}",
                "-e",
                f"POSTGRES_DB={TEST_DB_NAME}",
                "-p",
                "127.0.0.1::5432",
                POSTGRES_IMAGE,
            ]
        )
    except FileNotFoundError as exc:
        pytest.exit("docker command not found. Install Docker to run API tests.")
    except subprocess.CalledProcessError as exc:
        pytest.exit(
            f"Failed to start PostgreSQL container: {exc.stderr.strip() or exc.stdout.strip()}"
        )

    try:
        port_result = _run_cmd(["docker", "port", container_name, "5432/tcp"])
        host_port = _parse_host_port(port_result.stdout)
        _wait_for_postgres(container_name, STARTUP_TIMEOUT_SECONDS)
        _verify_host_connection_with_retries(host_port)

        async_url = (
            f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@127.0.0.1:{host_port}/{TEST_DB_NAME}"
        )
        yield {
            "container_name": container_name,
            "host_port": host_port,
            "async_url": async_url,
        }
    finally:
        _run_cmd(["docker", "rm", "-f", container_name], check=False)


@pytest.fixture(scope="function")
async def test_engine(postgres_container):
    engine = create_async_engine(
        postgres_container["async_url"],
        pool_pre_ping=True,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function")
async def test_db(test_engine):
    """Clean database state before each test."""
    table_names = [f'"{table.name}"' for table in Base.metadata.sorted_tables]

    if table_names:
        truncate_query = text(
            f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"
        )
        async with test_engine.begin() as conn:
            await conn.execute(truncate_query)

    yield


@pytest.fixture(scope="function")
async def test_session(test_db, test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provides a DB session for direct assertions in tests."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_async_session(test_session):
    """Each HTTP request gets the same session for tests."""
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
    """Mock logger factory globally for tests."""
    mock_log = MagicMock()
    with patch("logger.get_logger", return_value=mock_log):
        yield


@pytest.fixture
def mock_settings():
    with patch("app.auth.manager.settings") as mock_settings:
        mock_settings.auth_enable_email = True
        mock_settings.auth_enable_phone = True
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_secret_key = "test-secret-key-for-testing-only"
        mock_settings.access_token_ttl = 1800
        mock_settings.refresh_token_ttl = 2592000
        yield mock_settings


@pytest.fixture
def mock_sms_manager():
    with patch("app.auth.manager.create_exolve_sms_manager") as mock_sms:
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
    mock_redis.get = AsyncMock(
        side_effect=lambda key: stored_codes.get(key.replace("verification_code:", ""))
    )
    mock_redis.delete = AsyncMock()

    async def mock_get_redis():
        return mock_redis

    with (
        patch("app.auth.manager.store_verification_code", side_effect=mock_store),
        patch("app.auth.manager.verify_code", side_effect=mock_verify),
        patch("utils.redis.verification_codes.verify_code", side_effect=mock_verify),
        patch("utils.redis.verification_codes.store_verification_code", side_effect=mock_store),
        patch("utils.redis.client.get_redis_client", side_effect=mock_get_redis),
    ):
        yield stored_codes


@pytest.fixture
def mock_image_manager_init():
    with patch("main.ImageManager") as mock_im:
        mock_instance = MagicMock()
        mock_instance.initialize_bucket = AsyncMock()
        mock_im.return_value = mock_instance
        yield mock_instance


def pytest_sessionfinish(session, exitstatus):
    try:
        logger._loggers.clear()
    except Exception:
        pass

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in tasks:
                task.cancel()
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        finally:
            loop.close()
    except Exception:
        pass
