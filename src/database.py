"""
Конфигурация базы данных для приложения.
Поддерживает как синхронные, так и асинхронные сессии.

Примеры использования:

1. Синхронная сессия:
    with get_sync_session() as session:
        networks = session.query(Network).all()

2. Асинхронная сессия:
    async with get_async_session() as session:
        result = await session.execute(select(Network))
        networks = result.scalars().all()

3. В FastAPI с зависимостями:
    @app.get("/networks/")
    async def get_networks(session: AsyncSession = Depends(get_async_session_generator)):
        result = await session.execute(select(Network))
        return result.scalars().all()
"""

import os
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from config import settings

# URL для синхронной базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"{settings.db_sync_driver}://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

# URL для асинхронной базы данных
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL", 
    f"{settings.db_async_driver}://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

# Синхронный движок и фабрика сессий
sync_engine = create_engine(DATABASE_URL)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Асинхронный движок и фабрика сессий
# pool_pre_ping=True проверяет соединения перед использованием
# pool_recycle=3600 пересоздает соединения каждый час
# max_overflow=10 позволяет создавать дополнительные соединения при нагрузке
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    max_overflow=10,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для синхронной сессии базы данных.
    
    Использование:
        with get_sync_session() as session:
            result = session.query(Network).all()
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для сессии базы данных.
    
    Использование:
        async with get_async_session() as session:
            result = await session.execute(select(Network))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_async_session_generator() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор для получения сессии базы данных.
    Используется как зависимость в FastAPI.
    
    Использование в FastAPI:
        @app.get("/networks/")
        async def get_networks(session: AsyncSession = Depends(get_async_session_generator)):
            result = await session.execute(select(Network))
            return result.scalars().all()
    """
    async with get_async_session() as session:
        yield session