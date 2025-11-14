#!/usr/bin/env python3
"""
Скрипт запуска Celery worker
Настраивает пути и запускает Celery
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

os.chdir(project_root)

if __name__ == "__main__":
    import subprocess
    
    # Устанавливаем PYTHONPATH для правильной работы импортов
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_path)
    
    # Запускаем celery worker через uv run
    # Используем celery_app из src директории
    cmd = [
        "uv", "run", "celery",
        "-A", "celery_app",
        "worker",
        "--loglevel=info"
    ]
    
    # Запускаем celery с правильными путями
    subprocess.run(cmd, env=env)

