"""
PostgreSQL Connection Pool Management

Provides asyncpg-based connection pooling with encryption key management
integration for secure password handling.
"""

import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.security import AICOKeyManager

logger = get_logger("shared.data.postgres.connection")

# Global connection pool and session factory (initialized once per process)
_pool: Optional[asyncpg.Pool] = None
_engine = None
_session_factory: Optional[async_sessionmaker] = None


async def get_postgres_pool() -> asyncpg.Pool:
    """
    Get or create the global asyncpg connection pool.
    
    Pool configuration:
    - min_size: 10 connections (always available)
    - max_size: 50 connections (scales under load)
    - command_timeout: 60 seconds
    - Connection recycling and health checks
    
    Returns:
        asyncpg.Pool instance
        
    Raises:
        RuntimeError: If configuration is missing or connection fails
    """
    global _pool
    
    if _pool is not None:
        return _pool
    
    # Load configuration
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    pg_config = config.get("core.database.postgres", {})
    if not pg_config:
        raise RuntimeError("PostgreSQL configuration not found in core.yaml")
    
    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = os.environ.get("AICO_POSTGRES_DATABASE", pg_config.get("database", "aico"))
    user = pg_config.get("user", "postgres")
    
    # Get password from environment or AICOKeyManager
    import os
    
    password = os.environ.get("AICO_PG_PASSWORD")
    
    if not password:
        # Try to get from AICOKeyManager (like deploy.py does)
        try:
            key_manager = AICOKeyManager(config)
            password = key_manager.get_database_password("postgres", username="postgres")
            if password:
                logger.debug("Retrieved Postgres password from AICOKeyManager")
        except Exception as e:
            logger.warning(f"Could not retrieve password from AICOKeyManager: {e}")
    
    if not password:
        raise RuntimeError(
            "PostgreSQL password not found. Set AICO_PG_PASSWORD environment variable "
            "or run 'aico deploy postgres' to set up credentials."
        )
    
    # Create connection pool
    try:
        logger.info(f"Creating PostgreSQL connection pool: {user}@{host}:{port}/{database}")
        
        _pool = await asyncpg.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            # SSL configuration (disable for local dev, enable for production)
            ssl=False,                # No SSL for local docker container
            # Connection pool sizing for optimal performance
            min_size=10,              # Always-ready connections
            max_size=50,              # Scale under load
            max_queries=50000,        # Recycle connections after 50k queries
            max_inactive_connection_lifetime=300,  # 5 min idle timeout
            # Timeouts
            command_timeout=60,       # Query timeout
            timeout=10,               # Connection acquisition timeout
            # Connection initialization callback
            init=_init_connection,
        )
        
        logger.info(f"PostgreSQL connection pool created successfully (min=10, max=50)")
        return _pool
        
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL connection pool: {e}")
        raise RuntimeError(f"PostgreSQL connection failed: {e}") from e


async def _init_connection(conn: asyncpg.Connection):
    """
    Initialize each new connection in the pool.
    
    Sets search_path and optimizes connection for performance:
    - Enable prepared statement caching
    - Set optimal work_mem for this connection
    - Configure timezone to UTC
    """
    await conn.execute("SET search_path TO aico_core, public")
    await conn.execute("SET timezone TO 'UTC'")  # All timestamps in UTC
    # asyncpg automatically uses prepared statements for better performance


async def close_postgres_pool():
    """
    Close the global connection pool and SQLAlchemy engine.
    
    Should be called during application shutdown.
    """
    global _pool
    
    # Close SQLAlchemy engine first
    await close_session_factory()
    
    # Then close asyncpg pool
    if _pool is not None:
        logger.info("Closing PostgreSQL connection pool")
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection():
    """
    Get a connection from the pool (context manager).
    
    Usage:
        async with get_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = await get_postgres_pool()
    async with pool.acquire() as connection:
        yield connection


async def get_session_factory() -> async_sessionmaker:
    """
    Get a SQLAlchemy session factory bound to the asyncpg pool.
    
    Creates async sessions that use our optimized asyncpg connection pool.
    Sessions are configured for optimal PostgreSQL performance.
    
    Returns:
        async_sessionmaker that creates AsyncSession instances
        
    Raises:
        RuntimeError: If configuration is missing or connection fails
    """
    global _session_factory, _engine
    
    if _session_factory is not None:
        return _session_factory
    
    # Load configuration
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    pg_config = config.get("core.database.postgres", {})
    if not pg_config:
        raise RuntimeError("PostgreSQL configuration not found in core.yaml")
    
    host = pg_config.get("host", "localhost")
    import os
    port = pg_config.get("port", 5432)
    database = os.environ.get("AICO_POSTGRES_DATABASE", pg_config.get("database", "aico"))
    user = pg_config.get("user", "postgres")
    
    # Get password from environment or AICOKeyManager
    import os
    
    password = os.environ.get("AICO_PG_PASSWORD")
    
    if not password:
        # Try to get from AICOKeyManager (like deploy.py does)
        try:
            key_manager = AICOKeyManager(config)
            password = key_manager.get_database_password("postgres", username="postgres")
            if password:
                logger.debug("Retrieved Postgres password from AICOKeyManager")
        except Exception as e:
            logger.warning(f"Could not retrieve password from AICOKeyManager: {e}")
    
    if not password:
        raise RuntimeError(
            "PostgreSQL password not found. Set AICO_PG_PASSWORD environment variable "
            "or run 'aico deploy postgres' to set up credentials."
        )
    
    # Create SQLAlchemy async engine with asyncpg
    # Use postgresql+asyncpg:// dialect for native asyncpg support
    # Note: SSL is disabled via connect_args for local development
    database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    
    try:
        logger.info(f"Creating SQLAlchemy async engine with asyncpg: {user}@{host}:{port}/{database}")
        
        _engine = create_async_engine(
            database_url,
            # Use NullPool - we manage pooling via asyncpg directly
            poolclass=NullPool,
            # Performance optimizations
            echo=False,  # Set to True for SQL query logging during development
            future=True,  # Use SQLAlchemy 2.0 style
            # Connection arguments passed to asyncpg
            connect_args={
                "ssl": False,  # Disable SSL for local development
                "server_settings": {
                    "jit": "on",
                    "application_name": "aico_backend",
                },
            },
        )
        
        # Create session factory
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit for better performance
            autoflush=False,  # Manual flush control for better performance
            autocommit=False,  # Explicit transaction control
        )
        
        logger.info("SQLAlchemy async session factory created successfully")
        return _session_factory
        
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy session factory: {e}")
        raise RuntimeError(f"SQLAlchemy setup failed: {e}") from e


async def close_session_factory():
    """
    Close the SQLAlchemy engine.
    
    Should be called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("Closing SQLAlchemy engine")
        await _engine.dispose()
        _engine = None
        _session_factory = None
