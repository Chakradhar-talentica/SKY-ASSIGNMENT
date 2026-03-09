"""
FastAPI dependencies for the application.
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, Request
import redis.asyncio as redis

from src.config.database import get_db_session, AsyncSession
from src.config.settings import get_settings, Settings


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides database session."""
    yield session


async def get_redis_client(request: Request) -> redis.Redis:
    """Dependency that provides Redis client from app state."""
    return request.app.state.redis


async def get_current_settings() -> Settings:
    """Dependency that provides application settings."""
    return get_settings()

