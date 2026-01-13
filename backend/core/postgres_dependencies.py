"""
PostgreSQL Dependency Injection for FastAPI

Provides dependency injection for Unit of Work and repositories.
Integrates with FastAPI's dependency injection system.
"""

from typing import AsyncGenerator
from fastapi import Depends

from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


# Global session factory (initialized on startup)
_session_factory = None


async def initialize_postgres_dependencies():
    """
    Initialize PostgreSQL dependencies on application startup.
    
    Should be called in FastAPI lifespan event.
    """
    global _session_factory
    _session_factory = await get_session_factory()


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    FastAPI dependency for Unit of Work.
    
    Provides a UnitOfWork instance with automatic transaction management.
    Commits on success, rolls back on exception.
    
    Usage:
        @router.get("/users/{uuid}")
        async def get_user(uuid: str, uow: UnitOfWork = Depends(get_uow)):
            user = await uow.users.get_by_id(uuid)
            return user
    """
    if _session_factory is None:
        raise RuntimeError("PostgreSQL session factory not initialized. Call initialize_postgres_dependencies() first.")
    
    uow = UnitOfWork(_session_factory)
    async with uow:
        yield uow
        # Auto-commit on success, auto-rollback on exception
