from functools import wraps
from typing import Callable, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import Response
import json
import time
from logger import get_logger


logger = get_logger("response_logger")


def log_response(
    log_level: str = "info",
    include_request_body: bool = False,
    include_response_body: bool = True,
    max_body_length: int = 10000,
    exclude_paths: Optional[list] = None
):
    """
    Декоратор для логирования ответов от эндпоинтов FastAPI.
    
    Логирует информацию о запросе (метод, путь, параметры, тело), ответе (статус, данные)
    и времени выполнения. Также логирует ошибки (HTTPException и другие исключения).
    
    Args:
        log_level: Уровень логирования ('debug', 'info', 'warning', 'error', 'critical')
        include_request_body: Логировать ли тело запроса (по умолчанию False, т.к. в FastAPI
                             тело может быть уже прочитано для Pydantic моделей)
        include_response_body: Логировать ли тело ответа
        max_body_length: Максимальная длина тела запроса/ответа для логирования (в символах)
        exclude_paths: Список путей, которые нужно исключить из логирования (например, ['/health', '/metrics'])
    
    Usage:
        from utils import log_response
        
        @router.post("/purchases")
        @log_response()
        async def create_purchase(
            request: Request,
            purchase_data: schemas.PurchaseCreate,
            current_user: User = Depends(get_current_user)
        ) -> schemas.PurchaseWithOffers:
            return await purchases_manager.create_purchase(...)
        
        # С кастомными параметрами
        @router.get("/users")
        @log_response(log_level="debug", include_response_body=False)
        async def get_users(request: Request) -> List[schemas.User]:
            return users
        
        # Исключить определенные пути
        @router.get("/health")
        @log_response(exclude_paths=["/health"])
        async def health_check():
            return {"status": "ok"}
    
    Note:
        - Декоратор должен быть применен ПОСЛЕ декоратора @router.* (ближе к функции)
        - Если include_request_body=True, тело запроса может быть недоступно,
          если оно уже было прочитано FastAPI для Pydantic моделей
        - Все логи записываются в файл через AsyncLogger (logs/app.log)
        - Логируются успешные ответы и ошибки (HTTPException и другие исключения)
    """
    exclude_paths = exclude_paths or []
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Ищем Request в аргументах
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            # Если Request не найден, просто выполняем функцию без логирования
            if not request:
                return await func(*args, **kwargs)
            
            # Проверяем, нужно ли исключить этот путь
            if any(request.url.path.startswith(path) for path in exclude_paths):
                return await func(*args, **kwargs)
            
            start_time = time.time()
            endpoint_name = f"{func.__module__}.{func.__name__}"
            
            # Собираем информацию о запросе
            request_info = {
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": f"{request.client.host}:{request.client.port}" if request.client else None,
            }
            
            # Логируем тело запроса, если нужно
            # Внимание: в FastAPI тело запроса может быть уже прочитано для Pydantic моделей,
            # поэтому чтение тела здесь может не сработать. Рекомендуется оставить include_request_body=False
            if include_request_body:
                try:
                    # Пытаемся прочитать тело запроса
                    # Используем безопасный подход - проверяем, не было ли оно уже прочитано
                    body = None
                    if hasattr(request, '_body') and request._body:
                        # Тело уже было прочитано FastAPI
                        body = request._body
                    elif hasattr(request, 'state') and hasattr(request.state, '_body'):
                        body = getattr(request.state, '_body', None)
                    else:
                        # Пытаемся прочитать тело напрямую
                        # Это может не сработать, если FastAPI уже прочитал его для Pydantic
                        try:
                            body = await request.body()
                        except RuntimeError:
                            # Тело уже было прочитано
                            body = None
                    
                    if body:
                        try:
                            body_str = body.decode('utf-8') if isinstance(body, bytes) else str(body)
                            if len(body_str) > max_body_length:
                                body_str = body_str[:max_body_length] + "... (truncated)"
                            # Пытаемся распарсить как JSON
                            if body_str.strip():
                                try:
                                    request_info["body"] = json.loads(body_str)
                                except json.JSONDecodeError:
                                    request_info["body"] = body_str
                            else:
                                request_info["body"] = None
                        except (UnicodeDecodeError, AttributeError):
                            request_info["body"] = f"<binary or non-json data, length: {len(body) if isinstance(body, bytes) else 'unknown'}>"
                    else:
                        request_info["body"] = "<body already read by FastAPI or empty>"
                except Exception as e:
                    # Если не удалось прочитать тело (например, уже было прочитано),
                    # просто пропускаем это поле
                    request_info["body_error"] = str(e)
            
            # Выполняем функцию
            response_data = None
            status_code = 200
            error_occurred = False
            error_message = None
            
            try:
                response_data = await func(*args, **kwargs)
                
                # Если это Response объект, пытаемся извлечь данные
                if isinstance(response_data, Response):
                    status_code = response_data.status_code
                    # Для Response объектов тело ответа обычно уже сериализовано
                    response_data = None
                else:
                    status_code = 200  # Успешный ответ по умолчанию
                    
            except HTTPException as e:
                error_occurred = True
                status_code = e.status_code
                error_message = str(e.detail)
                response_data = {"detail": e.detail}
                
                # Логируем ошибку перед raise
                execution_time = time.time() - start_time
                log_data = {
                    "endpoint": endpoint_name,
                    "request": request_info,
                    "status_code": status_code,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "error": error_message,
                }
                
                if include_response_body and response_data:
                    log_data["response"] = response_data
                
                log_message = (
                    f"{request.method} {request.url.path} - "
                    f"Status: {status_code} - "
                    f"Time: {execution_time * 1000:.2f}ms - "
                    f"Error: {error_message}"
                )
                
                log_method = getattr(logger, log_level.lower(), logger.info)
                await log_method(log_message, log_data)
                
                raise
                
            except Exception as e:
                error_occurred = True
                status_code = 500
                error_message = str(e)
                response_data = {"error": str(e)}
                
                # Логируем ошибку перед raise
                execution_time = time.time() - start_time
                log_data = {
                    "endpoint": endpoint_name,
                    "request": request_info,
                    "status_code": status_code,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "error": error_message,
                    "exception_type": type(e).__name__,
                }
                
                if include_response_body and response_data:
                    log_data["response"] = response_data
                
                log_message = (
                    f"{request.method} {request.url.path} - "
                    f"Status: {status_code} - "
                    f"Time: {execution_time * 1000:.2f}ms - "
                    f"Error: {error_message}"
                )
                
                log_method = getattr(logger, "error", logger.error)
                await log_method(log_message, log_data)
                
                raise
            
            # Логируем успешный ответ
            execution_time = time.time() - start_time
            
            log_data = {
                "endpoint": endpoint_name,
                "request": request_info,
                "status_code": status_code,
                "execution_time_ms": round(execution_time * 1000, 2),
            }
            
            # Логируем тело ответа, если нужно
            if include_response_body and response_data is not None:
                try:
                    # Сериализуем ответ в JSON для логирования
                    if hasattr(response_data, 'model_dump'):
                        # Pydantic модель (v2)
                        response_json = response_data.model_dump()
                    elif hasattr(response_data, 'dict'):
                        # Старая версия Pydantic (v1)
                        response_json = response_data.dict()
                    elif isinstance(response_data, (dict, list, str, int, float, bool, type(None))):
                        response_json = response_data
                    else:
                        # Для других типов пытаемся преобразовать в строку
                        response_json = str(response_data)
                    
                    # Ограничиваем длину
                    response_str = json.dumps(response_json, ensure_ascii=False, default=str)
                    if len(response_str) > max_body_length:
                        response_str = response_str[:max_body_length] + "... (truncated)"
                        log_data["response_truncated"] = True
                    
                    log_data["response"] = json.loads(response_str) if response_str else None
                except Exception as e:
                    log_data["response_error"] = str(e)
                    log_data["response_type"] = type(response_data).__name__
            
            log_message = (
                f"{request.method} {request.url.path} - "
                f"Status: {status_code} - "
                f"Time: {execution_time * 1000:.2f}ms"
            )
            
            log_method = getattr(logger, log_level.lower(), logger.info)
            await log_method(log_message, log_data)
            
            return response_data
        
        return wrapper
    
    return decorator

