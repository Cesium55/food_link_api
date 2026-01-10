import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional
from fastapi import HTTPException, status

from app.auth.manager import AuthManager, INVALID_CREDENTIALS, INVALID_REFRESH_TOKEN, EMAIL_AUTH_DISABLED, PHONE_AUTH_DISABLED
from app.auth.service import AuthService
from app.auth.models import User, RefreshToken
from app.auth import schemas
from app.auth.password_utils import PasswordUtils
from app.auth.jwt_utils import JWTUtils


# Constants
TEST_EMAIL = "test@example.com"
TEST_PHONE = "79991234567"
TEST_PASSWORD = "password123"
TEST_USER_ID = 1


@pytest.fixture
def mock_session():
    """Create a mock async session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user"""
    user = Mock(spec=User)
    user.id = TEST_USER_ID
    user.email = TEST_EMAIL
    user.phone = TEST_PHONE
    user.phone_verified = False
    user.is_seller = False
    user.password_hash = "hashed_password"
    return user


@pytest.fixture
def mock_user_with_email_only():
    """Create a mock user with email only"""
    user = Mock(spec=User)
    user.id = TEST_USER_ID
    user.email = TEST_EMAIL
    user.phone = None
    user.phone_verified = False
    user.is_seller = False
    return user


@pytest.fixture
def mock_user_with_phone_only():
    """Create a mock user with phone only"""
    user = Mock(spec=User)
    user.id = TEST_USER_ID
    user.email = None
    user.phone = TEST_PHONE
    user.phone_verified = False
    user.is_seller = False
    return user


@pytest.fixture
def mock_refresh_token():
    """Create a mock refresh token"""
    token = Mock(spec=RefreshToken)
    token.token = uuid.uuid4()
    token.user_id = TEST_USER_ID
    token.expires_at = datetime.now() + timedelta(days=30)
    token.is_revoked = False
    return token


@pytest.fixture
def auth_service():
    """Create AuthService instance"""
    return AuthService()


@pytest.fixture
def auth_manager():
    """Create AuthManager instance"""
    return AuthManager()


@pytest.fixture
def password_utils():
    """Create PasswordUtils instance"""
    return PasswordUtils()


@pytest.fixture
def mock_settings_enabled():
    """Mock settings with email and phone auth enabled"""
    with patch('app.auth.manager.settings') as mock_settings:
        mock_settings.auth_enable_email = True
        mock_settings.auth_enable_phone = True
        yield mock_settings


@pytest.fixture
def mock_jwt_settings():
    """Mock JWT settings for HS256"""
    with patch('app.auth.jwt_utils.settings') as mock_settings:
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_secret_key = "test_secret_key"
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.jwt_refresh_token_expire_days = 30
        yield mock_settings


# Helper functions
def create_mock_execute_result(return_value, scalar_method="scalar_one"):
    """Create a mock result for session.execute"""
    mock_result = Mock()
    getattr(mock_result, scalar_method).return_value = return_value
    return mock_result


def setup_token_creation_mocks(manager, access_token="access_token"):
    """Setup mocks for token creation"""
    manager.jwt_utils.create_access_token = Mock(return_value=access_token)
    manager.service.create_refresh_token = AsyncMock()
    mock_refresh_token = Mock()
    mock_refresh_token.token = uuid.uuid4()
    manager.service.create_refresh_token.return_value = mock_refresh_token
    return mock_refresh_token


def setup_sms_manager_mocks():
    """Setup mocks for SMS manager"""
    mock_sms_manager = AsyncMock()
    mock_sms_manager.__aenter__ = AsyncMock(return_value=mock_sms_manager)
    mock_sms_manager.__aexit__ = AsyncMock(return_value=None)
    mock_sms_manager.send_verification_code = AsyncMock(return_value="1234")
    return mock_sms_manager


def create_user_registration(email: Optional[str] = None, phone: Optional[str] = None):
    """Create UserRegistration schema"""
    return schemas.UserRegistration(
        email=email,
        phone=phone,
        password=TEST_PASSWORD
    )


def create_user_login(email: Optional[str] = None, phone: Optional[str] = None, password: str = TEST_PASSWORD):
    """Create UserLogin schema"""
    return schemas.UserLogin(
        email=email,
        phone=phone,
        password=password
    )


class TestPasswordUtils:
    """Tests for PasswordUtils class"""
    
    def test_hash_password(self, password_utils):
        """Test password hashing"""
        password = "test_password_123"
        hashed = password_utils.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert isinstance(hashed, str)
    
    def test_verify_password_correct(self, password_utils):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = password_utils.hash_password(password)
        result = password_utils.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_incorrect(self, password_utils):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = password_utils.hash_password(password)
        result = password_utils.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_hash_password_different_salts(self, password_utils):
        """Test that same password produces different hashes (different salts)"""
        password = "test_password_123"
        hashed1 = password_utils.hash_password(password)
        hashed2 = password_utils.hash_password(password)
        
        assert hashed1 != hashed2
        assert password_utils.verify_password(password, hashed1) is True
        assert password_utils.verify_password(password, hashed2) is True


class TestAuthService:
    """Tests for AuthService class"""
    
    @pytest.mark.asyncio
    async def test_create_user_with_email(self, auth_service, mock_session, mock_user_with_email_only):
        """Test creating user with email"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user_with_email_only)
        
        user = await auth_service.create_user(
            mock_session,
            email=TEST_EMAIL,
            password_hash="hashed_password"
        )
        
        assert user is not None
        assert user.email == TEST_EMAIL
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_with_phone(self, auth_service, mock_session, mock_user_with_phone_only):
        """Test creating user with phone"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user_with_phone_only)
        
        user = await auth_service.create_user(
            mock_session,
            phone=TEST_PHONE,
            password_hash="hashed_password"
        )
        
        assert user is not None
        assert user.phone == TEST_PHONE
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user(self, auth_service, mock_session, mock_user):
        """Test getting user by ID"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user, "scalar_one_or_none")
        
        user = await auth_service.get_user(mock_session, user_id=TEST_USER_ID)
        
        assert user is not None
        assert user.id == TEST_USER_ID
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, auth_service, mock_session):
        """Test getting non-existent user"""
        mock_session.execute.return_value = create_mock_execute_result(None, "scalar_one_or_none")
        
        user = await auth_service.get_user(mock_session, user_id=999)
        
        assert user is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, auth_service, mock_session, mock_user):
        """Test getting user by email"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user, "scalar_one_or_none")
        
        user = await auth_service.get_user_by_email(mock_session, TEST_EMAIL)
        
        assert user is not None
        assert user.email == TEST_EMAIL
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_phone(self, auth_service, mock_session, mock_user):
        """Test getting user by phone"""
        mock_session.execute.return_value = create_mock_execute_result(mock_user, "scalar_one_or_none")
        
        user = await auth_service.get_user_by_phone(mock_session, TEST_PHONE)
        
        assert user is not None
        assert user.phone == TEST_PHONE
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_user_password_correct(self, auth_service):
        """Test password verification with correct password"""
        password = "test_password_123"
        password_hash = auth_service.password_utils.hash_password(password)
        result = await auth_service.verify_user_password(password, password_hash)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_user_password_incorrect(self, auth_service):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        password_hash = auth_service.password_utils.hash_password(password)
        result = await auth_service.verify_user_password(wrong_password, password_hash)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_refresh_token(self, auth_service, mock_session, mock_refresh_token):
        """Test creating refresh token"""
        mock_session.execute.return_value = create_mock_execute_result(mock_refresh_token)
        expires_at = datetime.now() + timedelta(days=30)
        
        token = await auth_service.create_refresh_token(mock_session, user_id=TEST_USER_ID, expires_at=expires_at)
        
        assert token is not None
        assert token.user_id == TEST_USER_ID
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_refresh_token(self, auth_service, mock_session, mock_refresh_token):
        """Test getting refresh token"""
        mock_session.execute.return_value = create_mock_execute_result(mock_refresh_token, "scalar_one_or_none")
        
        token = await auth_service.get_refresh_token(mock_session, str(mock_refresh_token.token))
        
        assert token is not None
        assert token.user_id == TEST_USER_ID
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, auth_service, mock_session):
        """Test revoking refresh token"""
        mock_session.execute.return_value = Mock()
        
        await auth_service.revoke_refresh_token(mock_session, "token_string")
        
        mock_session.execute.assert_called_once()


class TestAuthManager:
    """Tests for AuthManager class"""
    
    @pytest.mark.asyncio
    async def test_register_user_with_email_success(self, auth_manager, mock_session, mock_user_with_email_only, mock_settings_enabled):
        """Test successful user registration with email"""
        auth_manager.service.get_user_by_email = AsyncMock(return_value=None)
        auth_manager.service.create_user = AsyncMock(return_value=mock_user_with_email_only)
        mock_refresh_token = setup_token_creation_mocks(auth_manager)
        
        user_data = create_user_registration(email=TEST_EMAIL)
        result = await auth_manager.register_user(mock_session, user_data)
        
        assert result is not None
        assert result.access_token == "access_token"
        assert result.refresh_token == str(mock_refresh_token.token)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_with_phone_success(self, auth_manager, mock_session, mock_user_with_phone_only, mock_settings_enabled):
        """Test successful user registration with phone"""
        auth_manager.service.get_user_by_phone = AsyncMock(return_value=None)
        auth_manager.service.create_user = AsyncMock(return_value=mock_user_with_phone_only)
        mock_refresh_token = setup_token_creation_mocks(auth_manager)
        
        with patch('app.auth.manager.create_exolve_sms_manager') as mock_sms:
            mock_sms_manager = setup_sms_manager_mocks()
            mock_sms.return_value = mock_sms_manager
            
            with patch('app.auth.manager.store_verification_code'):
                user_data = create_user_registration(phone=TEST_PHONE)
                result = await auth_manager.register_user(mock_session, user_data)
                
                assert result is not None
                assert result.access_token == "access_token"
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(self, auth_manager, mock_session, mock_user, mock_settings_enabled):
        """Test registration with existing email"""
        auth_manager.service.get_user_by_email = AsyncMock(return_value=mock_user)
        user_data = create_user_registration(email=TEST_EMAIL)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.register_user(mock_session, user_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_register_user_email_auth_disabled(self, auth_manager, mock_session):
        """Test registration when email auth is disabled"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_email = False
            user_data = create_user_registration(email=TEST_EMAIL)
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.register_user(mock_session, user_data)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_login_user_with_email_success(self, auth_manager, mock_session, mock_user, mock_settings_enabled):
        """Test successful login with email"""
        auth_manager.service.get_user_by_email = AsyncMock(return_value=mock_user)
        auth_manager.service.verify_user_password = AsyncMock(return_value=True)
        setup_token_creation_mocks(auth_manager)
        
        login_data = create_user_login(email=TEST_EMAIL)
        result = await auth_manager.login_user(mock_session, login_data)
        
        assert result is not None
        assert result.access_token == "access_token"
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_user_with_phone_success(self, auth_manager, mock_session, mock_user, mock_settings_enabled):
        """Test successful login with phone"""
        auth_manager.service.get_user_by_phone = AsyncMock(return_value=mock_user)
        auth_manager.service.verify_user_password = AsyncMock(return_value=True)
        setup_token_creation_mocks(auth_manager)
        
        login_data = create_user_login(phone=TEST_PHONE)
        result = await auth_manager.login_user(mock_session, login_data)
        
        assert result is not None
        assert result.access_token == "access_token"
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials_user_not_found(self, auth_manager, mock_session, mock_settings_enabled):
        """Test login with non-existent user"""
        auth_manager.service.get_user_by_email = AsyncMock(return_value=None)
        login_data = create_user_login(email="nonexistent@example.com")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.login_user(mock_session, login_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials_wrong_password(self, auth_manager, mock_session, mock_user, mock_settings_enabled):
        """Test login with wrong password"""
        auth_manager.service.get_user_by_email = AsyncMock(return_value=mock_user)
        auth_manager.service.verify_user_password = AsyncMock(return_value=False)
        login_data = create_user_login(email=TEST_EMAIL, password="wrong_password")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.login_user(mock_session, login_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_user_email_auth_disabled(self, auth_manager, mock_session):
        """Test login when email auth is disabled"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_email = False
            login_data = create_user_login(email=TEST_EMAIL)
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.login_user(mock_session, login_data)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, auth_manager, mock_session, mock_user, mock_refresh_token):
        """Test successful token refresh"""
        mock_refresh_token.expires_at = datetime.now() + timedelta(days=1)
        auth_manager.service.get_refresh_token = AsyncMock(return_value=mock_refresh_token)
        auth_manager.service.get_user = AsyncMock(return_value=mock_user)
        auth_manager.service.revoke_refresh_token = AsyncMock()
        new_refresh_token = setup_token_creation_mocks(auth_manager, "new_access_token")
        
        refresh_data = schemas.RefreshTokenRequest(refresh_token=str(mock_refresh_token.token))
        result = await auth_manager.refresh_tokens(mock_session, refresh_data)
        
        assert result is not None
        assert result.access_token == "new_access_token"
        assert result.refresh_token == str(new_refresh_token.token)
        auth_manager.service.revoke_refresh_token.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(self, auth_manager, mock_session):
        """Test refresh with invalid token"""
        auth_manager.service.get_refresh_token = AsyncMock(return_value=None)
        refresh_data = schemas.RefreshTokenRequest(refresh_token="invalid_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.refresh_tokens(mock_session, refresh_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_expired_token(self, auth_manager, mock_session, mock_refresh_token):
        """Test refresh with expired token"""
        mock_refresh_token.expires_at = datetime.now() - timedelta(days=1)
        auth_manager.service.get_refresh_token = AsyncMock(return_value=mock_refresh_token)
        refresh_data = schemas.RefreshTokenRequest(refresh_token=str(mock_refresh_token.token))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.refresh_tokens(mock_session, refresh_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_revoked_token(self, auth_manager, mock_session, mock_refresh_token):
        """Test refresh with revoked token"""
        mock_refresh_token.expires_at = datetime.now() + timedelta(days=1)
        mock_refresh_token.is_revoked = True
        auth_manager.service.get_refresh_token = AsyncMock(return_value=mock_refresh_token)
        refresh_data = schemas.RefreshTokenRequest(refresh_token=str(mock_refresh_token.token))
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.refresh_tokens(mock_session, refresh_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_by_token_success(self, auth_manager, mock_session, mock_user):
        """Test getting current user by valid token"""
        payload = {"user_id": TEST_USER_ID, "email": TEST_EMAIL, "type": "access"}
        auth_manager.jwt_utils.verify_access_token = Mock(return_value=payload)
        auth_manager.service.get_user = AsyncMock(return_value=mock_user)
        
        user = await auth_manager.get_current_user_by_token(mock_session, "valid_token")
        
        assert user is not None
        assert user.id == TEST_USER_ID
        assert user.email == TEST_EMAIL
    
    @pytest.mark.asyncio
    async def test_get_current_user_by_token_invalid_token(self, auth_manager, mock_session):
        """Test getting user with invalid token"""
        auth_manager.jwt_utils.verify_access_token = Mock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.get_current_user_by_token(mock_session, "invalid_token")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_by_token_user_not_found(self, auth_manager, mock_session):
        """Test getting user when user doesn't exist"""
        payload = {"user_id": 999, "email": TEST_EMAIL, "type": "access"}
        auth_manager.jwt_utils.verify_access_token = Mock(return_value=payload)
        auth_manager.service.get_user = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.get_current_user_by_token(mock_session, "valid_token")
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_verify_phone_code_success(self, auth_manager, mock_session, mock_user_with_phone_only):
        """Test successful phone verification"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            auth_manager.service.get_user = AsyncMock(return_value=mock_user_with_phone_only)
            auth_manager._format_phone_number = Mock(return_value=TEST_PHONE)
            
            with patch('app.auth.manager.verify_code', return_value=True):
                verified_user = mock_user_with_phone_only
                verified_user.phone_verified = True
                auth_manager.service.update_user_phone_verified = AsyncMock(return_value=verified_user)
                setup_token_creation_mocks(auth_manager, "new_access_token")
                
                result = await auth_manager.verify_phone_code(mock_session, "1234", TEST_USER_ID)
                
                assert result is not None
                assert result.access_token == "new_access_token"
                auth_manager.service.update_user_phone_verified.assert_called_once_with(mock_session, TEST_USER_ID, True)
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_phone_code_invalid_code(self, auth_manager, mock_session, mock_user):
        """Test phone verification with invalid code"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            auth_manager.service.get_user = AsyncMock(return_value=mock_user)
            auth_manager._format_phone_number = Mock(return_value=TEST_PHONE)
            
            with patch('app.auth.manager.verify_code', return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await auth_manager.verify_phone_code(mock_session, "wrong_code", TEST_USER_ID)
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
                assert "invalid" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_verify_phone_code_no_phone(self, auth_manager, mock_session, mock_user):
        """Test phone verification when user has no phone"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            mock_user.phone = None
            auth_manager.service.get_user = AsyncMock(return_value=mock_user)
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.verify_phone_code(mock_session, "1234", TEST_USER_ID)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_resend_phone_verification_code_success(self, auth_manager, mock_session, mock_user):
        """Test successful resend of phone verification code"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            auth_manager.service.get_user = AsyncMock(return_value=mock_user)
            auth_manager._format_phone_number = Mock(return_value=TEST_PHONE)
            
            with patch('app.auth.manager.create_exolve_sms_manager') as mock_sms:
                mock_sms_manager = setup_sms_manager_mocks()
                mock_sms.return_value = mock_sms_manager
                
                with patch('app.auth.manager.store_verification_code'):
                    result = await auth_manager.resend_phone_verification_code(mock_session, TEST_USER_ID)
                    
                    assert result is not None
                    assert "message" in result
                    assert result["phone"] == TEST_PHONE
                    mock_sms_manager.send_verification_code.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resend_phone_verification_code_user_not_found(self, auth_manager, mock_session):
        """Test resend verification code when user doesn't exist"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            auth_manager.service.get_user = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.resend_phone_verification_code(mock_session, 999)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_resend_phone_verification_code_no_phone(self, auth_manager, mock_session, mock_user):
        """Test resend verification code when user has no phone"""
        with patch('app.auth.manager.settings') as mock_settings:
            mock_settings.auth_enable_phone = True
            mock_user.phone = None
            auth_manager.service.get_user = AsyncMock(return_value=mock_user)
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_manager.resend_phone_verification_code(mock_session, TEST_USER_ID)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_format_phone_number(self, auth_manager):
        """Test phone number formatting"""
        test_cases = [
            ("89123456789", "79123456789"),
            ("79123456789", "79123456789"),
            ("9123456789", "79123456789"),
            ("8 (912) 345-67-89", "79123456789")
        ]
        
        for input_phone, expected in test_cases:
            formatted = auth_manager._format_phone_number(input_phone)
            assert formatted == expected, f"Failed for input: {input_phone}"


class TestJWTUtils:
    """Tests for JWTUtils class - basic tests without requiring actual keys"""
    
    def test_create_access_token_structure_hs256(self, mock_jwt_settings):
        """Test that JWTUtils can be initialized with HS256 algorithm (no files needed)"""
        jwt_utils = JWTUtils()
        
        assert hasattr(jwt_utils, 'create_access_token')
        assert hasattr(jwt_utils, 'verify_access_token')
        assert jwt_utils.algorithm == "HS256"
        assert jwt_utils.secret_key == "test_secret_key"
    
    def test_get_user_id_from_token_none(self, mock_jwt_settings):
        """Test getting user ID from invalid token"""
        jwt_utils = JWTUtils()
        jwt_utils.verify_access_token = Mock(return_value=None)
        user_id = jwt_utils.get_user_id_from_token("invalid_token")
        
        assert user_id is None
    
    def test_get_user_id_from_token_valid(self, mock_jwt_settings):
        """Test getting user ID from valid token payload"""
        jwt_utils = JWTUtils()
        payload = {"user_id": TEST_USER_ID, "type": "access"}
        jwt_utils.verify_access_token = Mock(return_value=payload)
        user_id = jwt_utils.get_user_id_from_token("valid_token")
        
        assert user_id == TEST_USER_ID

