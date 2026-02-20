"""
API integration tests for authentication endpoints
"""
import pytest
from fastapi import status
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch
from app.auth.models import User, RefreshToken
from app.auth.password_utils import PasswordUtils
from app.auth.jwt_utils import JWTUtils


# Constants
TEST_EMAIL = "test@example.com"
TEST_PHONE = "79991234567"
TEST_PASSWORD = "password123"


def get_response_data(response_data: dict) -> dict:
    """Helper function to extract data from wrapped response"""
    # ResponseWrapperMiddleware wraps responses in {"data": ...}
    return response_data.get("data", response_data)


class TestRegisterAPI:
    """Tests for /auth/register endpoint"""
    
    @pytest.mark.asyncio
    async def test_register_with_email_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful registration with email"""
        response = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user was created in database
        result = await test_session.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == TEST_EMAIL
        assert user.phone is None
        assert user.phone_verified is False
    
    @pytest.mark.asyncio
    async def test_register_with_phone_success(self, client, test_session, mock_settings, mock_sms_manager, mock_redis_verification_code, mock_image_manager_init):
        """Test successful registration with phone"""
        response = await client.post(
            "/auth/register",
            json={
                "phone": TEST_PHONE,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify user was created
        result = await test_session.execute(select(User).where(User.phone == TEST_PHONE))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.phone == TEST_PHONE
        assert user.email is None
    
    @pytest.mark.asyncio
    async def test_register_email_already_exists(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test registration with existing email"""
        # Create existing user
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        # Try to register with same email
        response = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_without_email_or_phone(self, client, mock_settings, mock_image_manager_init):
        """Test registration without email or phone"""
        response = await client.post(
            "/auth/register",
            json={
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_register_with_both_email_and_phone(self, client, mock_settings, mock_image_manager_init):
        """Test registration with both email and phone (should fail)"""
        response = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "phone": TEST_PHONE,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, client, mock_settings, mock_image_manager_init):
        """Test registration with password too short"""
        response = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": "short"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginAPI:
    """Tests for /auth/login endpoint"""
    
    @pytest.mark.asyncio
    async def test_login_with_email_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful login with email"""
        # Create user first
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        # Login
        response = await client.post(
            "/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_login_with_phone_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful login with phone"""
        # Create user first
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(phone=TEST_PHONE, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        # Login
        response = await client.post(
            "/auth/login",
            json={
                "phone": TEST_PHONE,
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials_user_not_found(self, client, mock_settings, mock_image_manager_init):
        """Test login with non-existent user"""
        response = await client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": TEST_PASSWORD
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials_wrong_password(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test login with wrong password"""
        # Create user first
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        # Try to login with wrong password
        response = await client.post(
            "/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": "wrong_password"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()


class TestRefreshTokenAPI:
    """Tests for /auth/refresh endpoint"""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test successful token refresh"""
        # Create user and refresh token
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.flush()
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=uuid.uuid4(),
            expires_at=datetime.now() + timedelta(days=30),
            created_at=datetime.now()
        )
        test_session.add(refresh_token)
        await test_session.commit()
        refresh_token_str = refresh_token.token
        
        # Refresh token
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": str(refresh_token_str)
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different
        assert data["refresh_token"] != str(refresh_token_str)
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client, mock_settings, mock_image_manager_init):
        """Test refresh with invalid token"""
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid-token-uuid"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test refresh with expired token"""
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.flush()
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=uuid.uuid4(),
            expires_at=datetime.now() - timedelta(days=1),  # Expired
            created_at=datetime.now() - timedelta(days=2)
        )
        test_session.add(refresh_token)
        await test_session.commit()
        
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": str(refresh_token.token)
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUserAPI:
    """Tests for /auth endpoint (get current user)"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test getting current user with valid token"""
        # Create user and get token
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        jwt_utils = JWTUtils()
        token = jwt_utils.create_access_token(user)
        
        # Get current user
        response = await client.post(
            "/auth",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert data["email"] == TEST_EMAIL
        assert data["id"] is not None
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client, mock_settings, mock_image_manager_init):
        """Test getting current user with invalid token"""
        response = await client.post(
            "/auth",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client, mock_settings, mock_image_manager_init):
        """Test getting current user without token"""
        response = await client.post("/auth")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestVerifyPhoneAPI:
    """Tests for /auth/verify-phone endpoint"""
    
    @pytest.mark.asyncio
    async def test_verify_phone_success(self, client, test_session, mock_settings, mock_redis_verification_code, mock_image_manager_init):
        """Test successful phone verification"""
        # Create user with phone
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, phone=TEST_PHONE, password_hash=password_hash, phone_verified=False)
        test_session.add(user)
        await test_session.commit()
        
        jwt_utils = JWTUtils()
        token = jwt_utils.create_access_token(user)
        
        # Override verify_code to return True
        with patch('app.auth.manager.verify_code', return_value=True):
            response = await client.post(
                "/auth/verify-phone",
                headers={"Authorization": f"Bearer {token}"},
                json={"code": "1234"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify phone_verified was updated
        await test_session.refresh(user)
        assert user.phone_verified is True
    
    @pytest.mark.asyncio
    async def test_verify_phone_invalid_code(self, client, test_session, mock_settings, mock_image_manager_init):
        """Test phone verification with invalid code"""
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, phone=TEST_PHONE, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        jwt_utils = JWTUtils()
        token = jwt_utils.create_access_token(user)
        
        with patch('app.auth.manager.verify_code', return_value=False):
            response = await client.post(
                "/auth/verify-phone",
                headers={"Authorization": f"Bearer {token}"},
                json={"code": "wrong_code"}
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()


class TestResendVerificationCodeAPI:
    """Tests for /auth/resend-verification-code endpoint"""
    
    @pytest.mark.asyncio
    async def test_resend_verification_code_success(self, client, test_session, mock_settings, mock_sms_manager, mock_redis_verification_code, mock_image_manager_init):
        """Test successful resend of verification code"""
        password_utils = PasswordUtils()
        password_hash = password_utils.hash_password(TEST_PASSWORD)
        user = User(email=TEST_EMAIL, phone=TEST_PHONE, password_hash=password_hash)
        test_session.add(user)
        await test_session.commit()
        
        jwt_utils = JWTUtils()
        token = jwt_utils.create_access_token(user)
        
        response = await client.post(
            "/auth/resend-verification-code",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = get_response_data(response.json())
        assert "message" in data
        assert "phone" in data
        mock_sms_manager.send_verification_code.assert_called_once()

