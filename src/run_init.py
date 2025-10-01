#!/usr/bin/env python3
"""
Скрипт для запуска инициализации тестовых данных
"""

import asyncio
import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.debug.init import main

if __name__ == "__main__":
    print("🚀 Запуск инициализации тестовых данных...")
    print("Убедитесь, что API сервер запущен на http://localhost:8000")
    print("Нажмите Ctrl+C для отмены\n")
    
    try:
        asyncio.run(main())
        print("\n🎉 Инициализация завершена успешно!")
    except KeyboardInterrupt:
        print("\n❌ Инициализация отменена пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка инициализации: {e}")
        sys.exit(1)
