"""
User Management API Router

REST API endpoints for user CRUD operations and authentication.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from aico.core.logging import get_logger
from aico.data.user import UserService
from .schemas import (
    CreateUserRequest, UpdateUserRequest, AuthenticateRequest, SetPinRequest,
    UserResponse, AuthenticationResponse, UserStatsResponse, UserListResponse
)
from .dependencies import validate_uuid, validate_user_type, validate_pin
from .exceptions import (
    UserNotFoundError, UserServiceError, InvalidCredentialsError,
    handle_user_service_exceptions
)

router = APIRouter()
logger = get_logger("api", "users_router")

# These will be injected during app initialization
user_service: Optional[UserService] = None
auth_manager = None
verify_admin_access = None


def initialize_router(user_svc: UserService, auth_mgr, admin_dependency):
    """Initialize router with dependencies from main.py"""
    global user_service, auth_manager, verify_admin_access
    user_service = user_svc
    auth_manager = auth_mgr
    verify_admin_access = admin_dependency


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_user_service_exceptions
async def create_user(
    request: CreateUserRequest,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Create a new user"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate user type
    validate_user_type(request.user_type)
    
    # Validate PIN if provided
    if request.pin:
        validate_pin(request.pin)
    
    user = await user_service.create_user(
        full_name=request.full_name,
        nickname=request.nickname,
        user_type=request.user_type,
        pin=request.pin
    )
    
    logger.info("User created via API", extra={
        "user_uuid": user.uuid,
        "full_name": user.full_name,
        "created_by": admin_user.get("user_id")
    })
    
    return UserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.get("/{user_uuid}", response_model=UserResponse)
@handle_user_service_exceptions
async def get_user(
    user_uuid: str,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Get user by UUID"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    user = await user_service.get_user(user_uuid)
    if not user:
        raise UserNotFoundError(user_uuid)
    
    return UserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.put("/{user_uuid}", response_model=UserResponse)
@handle_user_service_exceptions
async def update_user(
    user_uuid: str,
    request: UpdateUserRequest,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Update user profile"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    # Validate user type if provided
    if "user_type" in updates:
        validate_user_type(updates["user_type"])
    
    user = await user_service.update_user(user_uuid, updates)
    if not user:
        raise UserNotFoundError(user_uuid)
    
    logger.info("User updated via API", extra={
        "user_uuid": user_uuid,
        "updated_fields": list(updates.keys()),
        "updated_by": admin_user.get("user_id")
    })
    
    return UserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )


@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def delete_user(
    user_uuid: str,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Delete user (soft delete)"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    success = await user_service.delete_user(user_uuid)
    if not success:
        raise UserNotFoundError(user_uuid)
    
    logger.info("User deleted via API", extra={
        "user_uuid": user_uuid,
        "deleted_by": admin_user.get("user_id")
    })


@router.get("/", response_model=UserListResponse)
@handle_user_service_exceptions
async def list_users(
    user_type: Optional[str] = None,
    limit: int = 100,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """List users with optional filtering"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Cap maximum limit
    if limit > 1000:
        limit = 1000
    
    # Validate user type filter if provided
    if user_type:
        validate_user_type(user_type)
    
    users = await user_service.list_users(user_type=user_type, limit=limit)
    
    user_responses = [
        UserResponse(
            uuid=user.uuid,
            full_name=user.full_name,
            nickname=user.nickname,
            user_type=user.user_type,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        for user in users
    ]
    
    return UserListResponse(
        users=user_responses,
        total=len(user_responses),
        limit=limit,
        user_type_filter=user_type
    )


@router.post("/authenticate", response_model=AuthenticationResponse)
async def authenticate_user(request: AuthenticateRequest):
    """Authenticate user with PIN and return JWT token"""
    if not user_service or not auth_manager:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    # Validate UUID format
    validate_uuid(request.user_uuid)
    
    # Validate PIN format
    validate_pin(request.pin)
    
    try:
        result = await user_service.authenticate_user(request.user_uuid, request.pin)
        
        if not result["success"]:
            return AuthenticationResponse(
                success=False,
                error=result["error"]
            )
        
        user = result["user"]
        
        # Generate JWT token using auth_manager
        jwt_token = auth_manager.generate_jwt_token(
            user_id=user.uuid,
            username=user.full_name,
            roles=[user.user_type],
            permissions={"conversation.*", "memory.read", "personality.read"}
        )
        
        logger.info("User authenticated via API", extra={
            "user_uuid": user.uuid,
            "full_name": user.full_name
        })
        
        return AuthenticationResponse(
            success=True,
            user=UserResponse(
                uuid=user.uuid,
                full_name=user.full_name,
                nickname=user.nickname,
                user_type=user.user_type,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else None,
                updated_at=user.updated_at.isoformat() if user.updated_at else None
            ),
            jwt_token=jwt_token,
            last_login=result.get("last_login")
        )
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return AuthenticationResponse(
            success=False,
            error="Authentication system error"
        )


@router.post("/{user_uuid}/pin", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def set_user_pin(
    user_uuid: str,
    request: SetPinRequest,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Set or update user's PIN"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Validate PIN format
    validate_pin(request.new_pin)
    
    success = await user_service.set_user_pin(user_uuid, request.new_pin)
    if not success:
        raise UserNotFoundError(user_uuid)
    
    logger.info("User PIN updated via API", extra={
        "user_uuid": user_uuid,
        "updated_by": admin_user.get("user_id")
    })


@router.post("/{user_uuid}/unlock", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def unlock_user(
    user_uuid: str,
    admin_user: dict = Depends(lambda: verify_admin_access)
):
    """Unlock user account"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    success = await user_service.unlock_user(user_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or no authentication configured"
        )
    
    logger.info("User unlocked via API", extra={
        "user_uuid": user_uuid,
        "unlocked_by": admin_user.get("user_id")
    })


@router.get("/stats", response_model=UserStatsResponse)
@handle_user_service_exceptions
async def get_user_stats(admin_user: dict = Depends(lambda: verify_admin_access)):
    """Get user statistics"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    stats = await user_service.get_user_stats()
    return UserStatsResponse(**stats)
