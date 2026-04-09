#!/usr/bin/env python3
"""
Скрипт запуска Food Link API
Настраивает пути и запускает FastAPI приложение
"""

import sys
import os
import logging
from pathlib import Path

project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

os.chdir(project_root)

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class UvicornNameFilter(logging.Filter):
    """Normalize uvicorn child logger names to a single 'uvicorn' name."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("uvicorn"):
            record.name = "uvicorn"
        return True


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": LOG_FORMAT,
            "datefmt": LOG_DATE_FORMAT,
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
            "filters": ["normalize_uvicorn_name"],
        },
    },
    "filters": {
        "normalize_uvicorn_name": {
            "()": UvicornNameFilter,
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "fastapi": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}

if __name__ == "__main__":
    import uvicorn
    from src.main import app
    
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = 8000
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    
    # Запускаем сервер
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_config=LOG_CONFIG,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
