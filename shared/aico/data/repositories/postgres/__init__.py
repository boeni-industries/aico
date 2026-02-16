"""
PostgreSQL Repository Implementations

Concrete repository implementations using SQLAlchemy Core and asyncpg.
"""

from .user_repository import PostgresUserRepository

__all__ = ["PostgresUserRepository"]
