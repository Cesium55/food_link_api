from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.auth.manager import AuthManager
from app.auth.models import User

auth_manager = AuthManager()
security = HTTPBearer(auto_error=False)


class CurrentUserData(BaseModel):
    id: int
    email: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    is_seller: bool = False
    seller_id: int | None = None


async def get_current_user_data(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUserData:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_manager.jwt_utils.verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUserData(
        id=payload["user_id"],
        email=payload.get("email"),
        phone=payload.get("phone"),
        phone_verified=payload.get("phone_verified", False),
        is_seller=payload.get("is_seller", False),
        seller_id=payload.get("seller_id"),
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    session = request.state.session
    return await auth_manager.get_current_user_by_token(session, token)
