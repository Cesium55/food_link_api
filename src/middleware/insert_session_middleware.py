from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from database import get_async_session


class InsertSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware для вставки сессии базы данных в контекст запроса.
    Создает сессию для каждого запроса и сохраняет её в request.state.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        async with get_async_session() as session:
            request.state.session = session
            
            response = await call_next(request)
            
            return response

