from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.manager import AuthManager
from app.auth.models import User
from database import get_async_session_generator
from sqlalchemy.ext.asyncio import AsyncSession

auth_manager = AuthManager()
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    session = request.state.session
    return await auth_manager.get_current_user_by_token(session, token)
