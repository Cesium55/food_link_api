from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import schemas
from app.auth.manager import AuthManager
from app.auth.models import User
from utils.auth_dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize manager and security
auth_manager = AuthManager()
security = HTTPBearer()


@router.post("/register", response_model=schemas.TokenResponse)
async def register_user(
    request: Request, user_data: schemas.UserRegistration
) -> schemas.TokenResponse:
    """Register a new user"""
    return await auth_manager.register_user(request.state.session, user_data)


@router.post("/login", response_model=schemas.TokenResponse)
async def login_user(
    request: Request, login_data: schemas.UserLogin
) -> schemas.TokenResponse:
    """Login user"""
    return await auth_manager.login_user(request.state.session, login_data)


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_tokens(
    request: Request, refresh_data: schemas.RefreshTokenRequest
) -> schemas.TokenResponse:
    """Refresh access token"""
    return await auth_manager.refresh_tokens(request.state.session, refresh_data)


@router.post("/resend-verification-code")
async def resend_phone_verification_code(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Resend verification code to phone number (for authenticated users)"""
    token = credentials.credentials
    user = await auth_manager.get_current_user_by_token(request.state.session, token)
    
    return await auth_manager.resend_phone_verification_code(
        request.state.session,
        user.id
    )


@router.post("/verify-phone")
async def verify_phone(
    request: Request,
    verify_data: schemas.VerifyPhoneRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> schemas.TokenResponse:
    """Verify phone number with code and get new token with phone_verified=True"""
    token = credentials.credentials
    user = await auth_manager.get_current_user_by_token(request.state.session, token)
    
    return await auth_manager.verify_phone_code(
        request.state.session,
        verify_data.code,
        user.id
    )


@router.post("", response_model=schemas.UserResponse, summary="Get current user", description="Get current user information by Bearer token")
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user by token
    
    Requires Bearer token in Authorization header.
    Use the 'Authorize' button in Swagger UI to set the token.
    """
    token = credentials.credentials
    user = await auth_manager.get_current_user_by_token(request.state.session, token)
    
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "phone_verified": user.phone_verified,
        "is_seller": user.is_seller
    }


@router.post("/firebase-token", summary="Register/Update Firebase token", description="Register or update Firebase Cloud Messaging token for push notifications")
async def register_firebase_token(
    request: Request,
    token_data: schemas.FirebaseTokenRequest,
    user: User = Depends(get_current_user)
) -> dict:
    """Register or update Firebase token for the current user
    
    This endpoint allows authenticated users to register their device's FCM token
    for receiving push notifications. If a token already exists, it will be updated.
    
    Requires Bearer token in Authorization header.
    """

    return await auth_manager.register_firebase_token(
        request.state.session,
        user.get("id"),
        token_data.token
    )


@router.put("/last-location", summary="Update last known location", description="Update current user's last known location coordinates")
async def update_user_last_location(
    request: Request,
    location: schemas.UserLastLocationUpdate,
    user: User = Depends(get_current_user)
) -> dict:
    """Update current user's last known location
    
    This endpoint allows authenticated users to update their last known location
    (latitude and longitude coordinates). This location can be used for various
    features like finding nearby shops, calculating delivery distances, etc.
    
    Requires Bearer token in Authorization header.
    """
    return await auth_manager.update_user_last_location(
        request.state.session,
        user.get("id"),
        location.latitude,
        location.longitude
    )