"""
User Management API Router

REST API endpoints for user CRUD operations and authentication.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from aico.core.logging import get_logger
from aico.data.user import UserService
from .schemas import (
    CreateUserRequest, UpdateUserRequest, AuthenticateRequest, SetPinRequest,
    UserResponse, AuthenticationResponse, UserStatsResponse, UserListResponse
)

def _user_to_response(user) -> UserResponse:
    """Convert UserProfile to UserResponse (DRY helper)"""
    return UserResponse(
        uuid=user.uuid,
        full_name=user.full_name,
        nickname=user.nickname,
        user_type=user.user_type,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None
    )
from .dependencies import validate_uuid, validate_user_type, validate_pin, security
from backend.core.lifecycle_manager import get_user_service, get_auth_manager
from .exceptions import (
    UserNotFoundError, UserServiceError, InvalidCredentialsError,
    handle_user_service_exceptions
)

router = APIRouter()
logger = get_logger("backend", "api.users_router")

# Router now uses proper FastAPI dependency injection - no global state needed
# Dependencies are injected via get_user_service, get_auth_manager from dependencies.py


async def get_admin_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager = Depends(get_auth_manager)
):
    """Admin access dependency using service container"""
    try:
        token = credentials.credentials
        # Verify admin token using auth manager
        user = auth_manager.verify_admin_token(credentials)
        return {"user_uuid": user.get("user_uuid"), "username": user.get("username")}
    except Exception as e:
        logger.error(f"Admin authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_user_service_exceptions
async def create_user(
    request: CreateUserRequest,
    admin_user = Depends(get_admin_dependency)
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
        "created_by": admin_user.get("user_uuid") if admin_user else "unknown"
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
    admin_user = Depends(get_admin_dependency)
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
    admin_user = Depends(get_admin_dependency)
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
        "updated_by": admin_user.get("user_uuid") if admin_user else "unknown"
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
    admin_user = Depends(get_admin_dependency)
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
        "deleted_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })


@router.get("/", response_model=UserListResponse)
@handle_user_service_exceptions
async def list_users(
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    user_service: UserService = Depends(get_user_service)
) -> UserListResponse:
    """List users with optional filtering"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    # Cap maximum limit
    limit = 100
    
    # Validate user type filter if provided
    if user_type:
        validate_user_type(user_type)
    
    users = await user_service.list_users(user_type=user_type, is_active=is_active, limit=limit)
    
    user_responses = [_user_to_response(user) for user in users]
    
    return UserListResponse(
        users=user_responses,
        total=len(user_responses),
        limit=limit,
        user_type_filter=user_type
    )


@router.post("/authenticate", response_model=AuthenticationResponse)
async def authenticate_user(
    request: AuthenticateRequest,
    user_service: UserService = Depends(get_user_service),
    auth_manager = Depends(get_auth_manager)
) -> AuthenticationResponse:
    logger.info(f"AUTHENTICATE_USER: Starting authentication for user_uuid: {request.user_uuid}")
    logger.info(f"AUTHENTICATE_USER: PIN provided: {bool(request.pin)}")
    """Authenticate a user with PIN and return JWT token."""
    
    logger.info(f"Authentication endpoint called with user_uuid: {request.user_uuid}")
    
    # Validate UUID format
    validate_uuid(request.user_uuid)
    
    # Validate PIN format
    validate_pin(request.pin)
    
    try:
        logger.info(f"Starting authentication for user: {request.user_uuid}")
        result = await user_service.authenticate_user(request.user_uuid, request.pin)
        logger.info(f"User service authentication result: {result}")
        
        if not result["success"]:
            response = AuthenticationResponse(
                success=False,
                error=result["error"]
            )
            logger.info(f"Authentication failed response: {response.dict()}")
            return response
        
        user = result["user"]
        logger.info(f"Retrieved user from result: {user.uuid if user else 'None'}")
        
        # Get user roles from authorization service
        from aico.core.authorization import AuthorizationService
        authz_service = AuthorizationService(user_service.db)
        logger.info("Getting user roles from authorization service")
        user_roles = authz_service.get_user_roles(user.uuid)
        user_permissions = authz_service.get_user_permissions(user.uuid)
        logger.info(f"User roles: {user_roles}, permissions: {user_permissions}")
        
        # Generate JWT access token with proper roles and permissions
        jwt_token = auth_manager.generate_jwt_token(
            user_uuid=user.uuid,
            username=user.full_name,
            roles=user_roles,
            permissions=user_permissions,
            device_uuid="web-client"  # Default device for web authentication
        )
        
        # Generate refresh token for token renewal
        refresh_token = auth_manager.generate_refresh_token(
            user_uuid=user.uuid,
            username=user.full_name,
            roles=user_roles,
            permissions=user_permissions,
            device_uuid="web-client"
        )
        
        response = AuthenticationResponse(
            success=True,
            user=_user_to_response(user),
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            last_login=result.get("last_login")
        )
        logger.info(f"Authentication success response: {response.dict()}")
        return response
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        response = AuthenticationResponse(
            success=False,
            error="Authentication system error"
        )
        logger.info(f"Authentication failure response: {response.dict()}")
        return response


@router.post("/refresh", response_model=AuthenticationResponse)
async def refresh_token(
    request: Request,
    auth_manager = Depends(get_auth_manager)
) -> AuthenticationResponse:
    """Refresh access token using refresh token"""
    try:
        # Extract refresh token from request body or Authorization header
        body = await request.json()
        refresh_token = body.get('refresh_token')
        
        # Fallback to Authorization header if not in body
        if not refresh_token:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                refresh_token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not refresh_token:
            return AuthenticationResponse(
                success=False,
                error="No refresh token provided"
            )
        
        # Decode refresh token to verify it's valid and get user info
        try:
            payload = jwt.decode(
                refresh_token,
                auth_manager.jwt_secret,
                algorithms=[auth_manager.jwt_algorithm],
                options={"verify_aud": False}
            )
            
            # Verify this is actually a refresh token
            if payload.get("type") != "refresh":
                return AuthenticationResponse(
                    success=False,
                    error="Invalid token type - refresh token required"
                )
            
            # Generate new access token
            new_access_token = auth_manager.generate_jwt_token(
                user_uuid=payload["user_uuid"],
                username=payload.get("username"),
                roles=payload.get("roles", ["user"]),
                permissions=set(payload.get("permissions", [])),
                device_uuid="web-client"
            )
            
            # Return new access token (keep same refresh token)
            return AuthenticationResponse(
                success=True,
                jwt_token=new_access_token,
                refresh_token=refresh_token  # Return same refresh token
            )
            
        except jwt.ExpiredSignatureError:
            return AuthenticationResponse(
                success=False,
                error="Refresh token expired - please login again"
            )
        except jwt.InvalidTokenError as e:
            return AuthenticationResponse(
                success=False,
                error=f"Invalid refresh token: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return AuthenticationResponse(
            success=False,
            error="Token refresh system error"
        )


@router.post("/{user_uuid}/pin", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def set_user_pin(
    user_uuid: str,
    request: SetPinRequest,
    admin_user = Depends(get_admin_dependency)
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
        "updated_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })


@router.post("/{user_uuid}/unlock", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def unlock_user(
    user_uuid: str,
    admin_user = Depends(get_admin_dependency)
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
        "unlocked_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(request: Request):
    """Logout user by revoking current JWT token"""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid token provided")
    
    token = auth_header.split(" ")[1]
    
    if not auth_manager:
        raise HTTPException(status_code=500, detail="Authentication manager not initialized")
    
    # Delete the session completely on logout
    if auth_manager.session_service:
        success = auth_manager.session_service.delete_token(token)
    else:
        # Fallback to in-memory revocation
        auth_manager.revoke_token(token)
        success = True
    
    logger.info("User logged out", extra={
        "token_prefix": token[:8] + "..." if len(token) > 8 else token,
        "revocation_success": success
    })


@router.post("/refresh", response_model=AuthenticationResponse)
async def refresh_token(
    request: Request,
    auth_manager = Depends(get_auth_manager),
    user_service: UserService = Depends(get_user_service)
):
    """Refresh JWT token for authenticated user with session rotation"""
    # Extract current token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid token provided")
    
    token = auth_header.split(" ")[1]
    
    if not auth_manager:
        raise HTTPException(status_code=500, detail="Authentication manager not initialized")
    
    # Use the new refresh_token method from auth_manager
    new_token = auth_manager.refresh_token(token, device_uuid="web-client")
    
    if not new_token:
        raise HTTPException(status_code=401, detail="Token refresh failed - token may be expired or revoked")
    
    # Extract user information from new token to get user data
    try:
        import jwt
        payload = jwt.decode(
            new_token, 
            auth_manager.jwt_secret, 
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_uuid = payload.get("user_uuid", payload.get("sub"))
        username = payload.get("username")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode new token")
    
    # Get user data for response
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    user = await user_service.get_user(user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info("Token refreshed with session rotation", extra={
        "user_uuid": user_uuid,
        "username": username
    })
    
    return AuthenticationResponse(
        success=True,
        user=_user_to_response(user),
        jwt_token=new_token,
        last_login=None
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_service: UserService = Depends(get_user_service)
) -> UserStatsResponse:
    """Get user statistics"""
    if not user_service:
        raise HTTPException(status_code=500, detail="User service not initialized")
    
    stats = await user_service.get_user_stats()
    return UserStatsResponse(**stats)
