"""API integration tests for authentication endpoints."""

from unittest.mock import patch

import pytest
from fastapi import status
from sqlalchemy import select

from app.auth.models import User


TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


def get_response_data(response_data: dict) -> dict:
    """Extract wrapped response body from middleware payload."""
    return response_data.get("data", response_data)


@pytest.fixture
def mock_refresh_rotation_cache():
    """Mock Redis lock/cache primitives for refresh endpoint tests."""
    rotated_tokens: dict[str, dict] = {}
    active_locks: set[str] = set()

    async def _get_rotated_tokens(refresh_token: str):
        return rotated_tokens.get(refresh_token)

    async def _store_rotated_tokens(refresh_token: str, tokens, expire_seconds: int | None = None):
        rotated_tokens[refresh_token] = tokens

    async def _acquire_refresh_lock(refresh_token: str, timeout_seconds: int | None = None):
        if refresh_token in active_locks:
            return False
        active_locks.add(refresh_token)
        return True

    async def _release_refresh_lock(refresh_token: str):
        active_locks.discard(refresh_token)

    async def _wait_for_rotated_tokens(
        refresh_token: str,
        timeout_seconds: int | None = None,
        poll_interval_seconds: float = 0.05,
    ):
        return rotated_tokens.get(refresh_token)

    with (
        patch("app.auth.manager.get_rotated_tokens", side_effect=_get_rotated_tokens),
        patch("app.auth.manager.store_rotated_tokens", side_effect=_store_rotated_tokens),
        patch("app.auth.manager.acquire_refresh_lock", side_effect=_acquire_refresh_lock),
        patch("app.auth.manager.release_refresh_lock", side_effect=_release_refresh_lock),
        patch("app.auth.manager.wait_for_rotated_tokens", side_effect=_wait_for_rotated_tokens),
    ):
        yield


async def register_and_get_tokens(client, email: str = TEST_EMAIL) -> dict:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    return get_response_data(response.json())


class TestAuthRegisterAPI:
    @pytest.mark.asyncio
    async def test_register_with_email_success(self, client, test_session, mock_settings, mock_image_manager_init):
        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        result = await test_session.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == TEST_EMAIL
        assert user.password_hash != TEST_PASSWORD

    @pytest.mark.asyncio
    async def test_register_existing_email_returns_400(self, client, mock_settings, mock_image_manager_init):
        await register_and_get_tokens(client, email=TEST_EMAIL)

        response = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_validation_error(self, client, mock_settings, mock_image_manager_init):
        response = await client.post(
            "/auth/register",
            json={"password": TEST_PASSWORD},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestAuthLoginAPI:
    @pytest.mark.asyncio
    async def test_login_with_email_success(self, client, mock_settings, mock_image_manager_init):
        await register_and_get_tokens(client, email=TEST_EMAIL)

        response = await client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client, mock_settings, mock_image_manager_init):
        await register_and_get_tokens(client, email=TEST_EMAIL)

        response = await client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": "wrong-password"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()


class TestAuthRefreshAPI:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client, mock_settings, mock_image_manager_init, mock_refresh_rotation_cache):
        tokens = await register_and_get_tokens(client, email=TEST_EMAIL)

        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client, mock_settings, mock_image_manager_init, mock_refresh_rotation_cache):
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthCurrentUserAPI:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, mock_settings, mock_image_manager_init):
        tokens = await register_and_get_tokens(client, email=TEST_EMAIL)

        response = await client.post(
            "/auth",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["email"] == TEST_EMAIL
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client, mock_settings, mock_image_manager_init):
        response = await client.post("/auth")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
