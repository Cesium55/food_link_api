from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Базовые настройки приложения"""
    
    # Настройки приложения
    app_name: str = "Food Link API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Настройки сервера
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Настройки базы данных
    db_sync_driver: str = "postgresql"
    db_async_driver: str = "postgresql+asyncpg"
    db_user: str = "user"
    db_password: str = "password"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "food_link"
    
    # JWT настройки для аутентификации
    jwt_secret_key: str = "your-jwt-secret-key-here"  # Deprecated, kept for backward compatibility
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30
    jwt_algorithm: str = "RS256"
    jwt_private_key_path: str = "keys/jwt_private_key.pem"
    jwt_public_key_path: str = "keys/jwt_public_key.pem"
    
    # Настройки CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: list[str] = ["*"]
    
    # Настройки логирования
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Настройки Celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    # Настройки Redis
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Настройки истечения покупок
    purchase_expiration_seconds: int = 30  # Время истечения покупки в секундах
    
    yandex_map_api_key: str = "UNDEFINED_KEY"
    
    # Настройки YooKassa
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None
    
    # Настройки S3/MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "food-link-images"
    s3_region_name: str = "us-east-1"
    
    # Настройки Exolve SMS
    exolve_api_key: Optional[str] = None
    exolve_number: Optional[str] = None
    exolve_api_url: str = "https://api.exolve.ru/messaging/v1/SendSMS"
    
    # Настройки аутентификации
    auth_enable_email: bool = True
    auth_enable_phone: bool = True

    # tg
    tg_gateway_access_token: Optional[str] = None
    
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


# Создаем глобальный экземпляр настроек
settings = Settings()
