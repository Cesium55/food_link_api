from typing import Any, Dict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically wrap API responses in {'data': ...} format.
    
    This middleware:
    1. Intercepts all responses from route handlers
    2. Wraps non-error responses in {'data': response_data} format
    3. Preserves error responses as-is
    4. Only affects JSON responses
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        if request.url.path in ["/docs", "/redoc", "/openapi.json"] or request.url.path.startswith("/static"):
            return response

        # Only process successful JSON responses (2xx status codes)
        if (200 <= response.status_code < 300 and 
            response.headers.get("content-type", "").startswith("application/json")):
            
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                response_data = json.loads(body.decode())
                
                # Check if response contains pagination data
                if isinstance(response_data, dict) and "pagination" in response_data and "items" in response_data:
                    # Extract pagination and items separately
                    pagination = response_data["pagination"]
                    items = response_data["items"]
                    
                    wrapped_data = {
                        "data": items,
                        "pagination": pagination
                    }
                else:
                    # Standard response wrapping
                    wrapped_data = {"data": response_data}
                
                new_headers = dict(response.headers)
                new_headers.pop("content-length", None)
                
                return JSONResponse(
                    content=wrapped_data,
                    status_code=response.status_code,
                    headers=new_headers
                )
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                return response
        
        return response
