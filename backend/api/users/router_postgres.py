"""
User Management API Router - PostgreSQL Version

Example of migrated endpoint using Repository pattern.
This demonstrates the architecture spike for the Big Bang migration.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow
from .schemas import UserResponse
from .dependencies import validate_uuid
from .exceptions import UserNotFoundError, handle_user_service_exceptions

router = APIRouter()
logger = get_logger("backend.api.users_router_postgres")


@router.get("/{user_uuid}", response_model=UserResponse)
@handle_user_service_exceptions
async def get_user_postgres(
    user_uuid: str,
    uow: UnitOfWork = Depends(get_uow)
):
    """
    Get user by UUID - PostgreSQL Repository Pattern
    
    This is the NEW way using:
    - Repository pattern (clean abstraction)
    - Unit of Work (transaction management)
    - SQLAlchemy Core (type-safe queries)
    - asyncpg (high-performance driver)
    
    OLD WAY (what we're replacing):
        db.execute("SELECT * FROM user_profiles WHERE uuid = ?", (user_uuid,))
        row = db.fetchone()
        user = UserProfile(uuid=row[0], full_name=row[1], ...)
    
    NEW WAY:
        user = await uow.users.get_by_id(user_uuid)
    """
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Get user via repository
    user = await uow.users.get_by_id(user_uuid)
    
    if not user:
        raise UserNotFoundError(user_uuid)
    
    logger.info(f"Retrieved user via PostgreSQL repository: {user_uuid}")
    
    return UserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        primary_language=user.primary_language,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.get("/", response_model=list[UserResponse])
@handle_user_service_exceptions
async def list_users_postgres(
    user_type: str = None,
    limit: int = 100,
    uow: UnitOfWork = Depends(get_uow)
):
    """
    List users with optional filtering - PostgreSQL Repository Pattern
    
    Demonstrates:
    - Clean filter syntax
    - Type-safe queries
    - Automatic pagination
    """
    # Build filters
    filters = {}
    if user_type:
        filters['user_type'] = user_type
    
    # Get users via repository
    users = await uow.users.list(filters=filters, limit=limit)
    
    logger.info(f"Listed {len(users)} users via PostgreSQL repository")
    
    return [
        UserResponse(
            uuid=user.uuid,
            full_name=user.full_name,
            nickname=user.nickname,
            user_type=user.user_type,
            is_active=user.is_active,
            primary_language=user.primary_language,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        for user in users
    ]
