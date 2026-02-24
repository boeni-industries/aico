"""
User Management API Router

REST API endpoints for user CRUD operations and authentication.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork
from aico.data.user.models import UserProfile
from aico.data.system.models import SystemEvent
from .schemas import (
    CreateUserRequest, UpdateUserRequest, AuthenticateRequest, SetPinRequest,
    UserResponse, AuthenticationResponse, UserStatsResponse, UserListResponse
)

from backend.api.errors import error_responses, raise_api_error

def _user_to_response(user) -> UserResponse:
    """Convert UserProfile to UserResponse (DRY helper)"""
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
from .dependencies import validate_uuid, validate_user_type, validate_pin, security
from backend.core.postgres_dependencies import get_uow
from backend.core.lifecycle_manager import get_auth_manager
from .exceptions import (
    UserNotFoundError, UserServiceError, InvalidCredentialsError,
    handle_user_service_exceptions
)

router = APIRouter()
logger = get_logger("backend.api.users_router")

# Router now uses proper FastAPI dependency injection - no global state needed


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
        raise_api_error(status_code=401, error_code="ADMIN_AUTH_FAILED", message="Invalid admin credentials")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_user_service_exceptions
async def create_user(
    request: CreateUserRequest,
    admin_user = Depends(get_admin_dependency),
    uow: UnitOfWork = Depends(get_uow)
):
    """Create a new user - PostgreSQL Repository Pattern"""
    from datetime import datetime, UTC
    import uuid as uuid_lib
    
    # Validate user type
    validate_user_type(request.user_type)
    
    # Validate PIN if provided
    if request.pin:
        validate_pin(request.pin)
    
    # Create user via repository
    user = UserProfile(
        uuid=str(uuid_lib.uuid4()),
        full_name=request.full_name,
        nickname=request.nickname,
        user_type=request.user_type,
        is_active=True,
        primary_language=request.primary_language or "en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    await uow.users.create(user)
    
    # Handle PIN if provided
    if request.pin:
        from aico.data.auth.models import UserCredentials
        import hashlib
        
        credentials = UserCredentials(
            uuid=str(uuid_lib.uuid4()),
            user_uuid=user.uuid,
            pin_hash=hashlib.sha256(request.pin.encode()).hexdigest(),
            failed_attempts=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        await uow.credentials.create(credentials)
    
    await uow.commit()
    
    logger.info("User created via API", extra={
        "user_uuid": user.uuid,
        "full_name": user.full_name,
        "created_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })
    
    return _user_to_response(user)


@router.get("/{user_uuid}", response_model=UserResponse)
@handle_user_service_exceptions
async def get_user(
    user_uuid: str,
    admin_user = Depends(get_admin_dependency),
    uow: UnitOfWork = Depends(get_uow)
):
    """Get user by UUID - PostgreSQL Repository Pattern"""
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Get user via repository
    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise UserNotFoundError(user_uuid)
    
    return _user_to_response(user)


@router.put("/{user_uuid}", response_model=UserResponse)
@handle_user_service_exceptions
async def update_user(
    user_uuid: str,
    request: UpdateUserRequest,
    admin_user = Depends(get_admin_dependency),
    uow: UnitOfWork = Depends(get_uow)
):
    """Update user profile - PostgreSQL Repository Pattern"""
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Get existing user
    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise UserNotFoundError(user_uuid)
    
    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    if not updates:
        raise_api_error(status_code=400, error_code="USER_UPDATE_EMPTY", message="No updates provided")
    
    # Validate user type if provided
    if "user_type" in updates:
        validate_user_type(updates["user_type"])
    
    # Apply updates to user object
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    # Update via repository
    user = await uow.users.update(user)
    await uow.commit()
    
    logger.info("User updated via API", extra={
        "user_uuid": user_uuid,
        "updated_fields": list(updates.keys()),
        "updated_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })
    
    return _user_to_response(user)


@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
@handle_user_service_exceptions
async def delete_user(
    user_uuid: str,
    admin_user = Depends(get_admin_dependency),
    uow: UnitOfWork = Depends(get_uow)
):
    """Delete user - PostgreSQL Repository Pattern"""
    # Validate UUID format
    validate_uuid(user_uuid)
    
    # Delete via repository
    success = await uow.users.delete(user_uuid)
    if not success:
        raise UserNotFoundError(user_uuid)
    
    await uow.commit()
    
    logger.info("User deleted via API", extra={
        "user_uuid": user_uuid,
        "deleted_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })


@router.get("/", response_model=UserListResponse)
@handle_user_service_exceptions
async def list_users(
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    uow: UnitOfWork = Depends(get_uow)
) -> UserListResponse:
    """List users with optional filtering - PostgreSQL Repository Pattern"""
    # Cap maximum limit
    limit = 100
    
    # Validate user type filter if provided
    if user_type:
        validate_user_type(user_type)
    
    # Build filters
    filters = {}
    if user_type:
        filters['user_type'] = user_type
    if is_active is not None:
        filters['is_active'] = is_active
    
    # Get users via repository
    users = await uow.users.list(filters=filters, limit=limit)
    
    user_responses = [_user_to_response(user) for user in users]
    
    return UserListResponse(
        users=user_responses,
        total=len(user_responses),
        limit=limit,
        user_type_filter=user_type
    )


@router.post(
    "/authenticate",
    response_model=AuthenticationResponse,
    responses=error_responses(401, 423, 500),
)
async def authenticate_user(
    request: AuthenticateRequest,
    request_obj: Request,
    uow: UnitOfWork = Depends(get_uow),
    auth_manager = Depends(get_auth_manager)
) -> AuthenticationResponse:
    """Authenticate a user with PIN and return JWT token - PostgreSQL Repository Pattern"""
    logger.info(f"AUTHENTICATE_USER: Starting authentication for user_uuid: {request.user_uuid}")
    logger.info(f"AUTHENTICATE_USER: PIN provided: {bool(request.pin)}")
    
    # Validate UUID format
    validate_uuid(request.user_uuid)
    
    # Validate PIN format
    validate_pin(request.pin)
    
    try:
        from datetime import datetime, UTC
        from passlib.context import CryptContext
        import uuid
        
        # Initialize bcrypt context (must match CLI UserService)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async def _emit_auth_event(*, topic: str, user_uuid: str, user_name: str | None, reason: str | None) -> None:
            now = datetime.now(UTC)
            ip_address = getattr(request_obj.client, "host", None)
            device_type = request_obj.headers.get("user-agent", None)
            await uow.system_events.create(
                SystemEvent(
                    timestamp=now.isoformat().replace("+00:00", "Z"),
                    topic=topic,
                    source="backend.api.users",
                    message_type="auth",
                    message_id=str(uuid.uuid4()),
                    priority=1,
                    correlation_id=None,
                    payload=None,
                    metadata={
                        "user_uuid": user_uuid,
                        "user_name": user_name,
                        "ip_address": ip_address,
                        "device_type": device_type,
                        "reason": reason,
                    },
                    created_at=now,
                )
            )
        
        logger.info(f"Starting authentication for user: {request.user_uuid}")
        
        # Get user via repository
        user = await uow.users.get_by_id(request.user_uuid)
        if not user:
            await _emit_auth_event(
                topic="auth.login.failed",
                user_uuid=request.user_uuid,
                user_name=None,
                reason="user_not_found",
            )
            await uow.commit()
            raise_api_error(
                status_code=401,
                error_code="AUTH_INVALID_CREDENTIALS",
                message="Invalid credentials",
            )
        
        # Get credentials via repository
        credentials = await uow.credentials.get_by_user_uuid(request.user_uuid)
        if not credentials:
            await _emit_auth_event(
                topic="auth.login.failed",
                user_uuid=request.user_uuid,
                user_name=user.full_name,
                reason="no_credentials",
            )
            await uow.commit()
            raise_api_error(
                status_code=401,
                error_code="AUTH_INVALID_CREDENTIALS",
                message="Invalid credentials",
            )
        
        # Check if account is locked
        if credentials.locked_until and credentials.locked_until > datetime.now(UTC):
            await _emit_auth_event(
                topic="auth.login.failed",
                user_uuid=request.user_uuid,
                user_name=user.full_name,
                reason="account_locked",
            )
            await uow.commit()
            raise_api_error(
                status_code=423,
                error_code="AUTH_ACCOUNT_LOCKED",
                message="Account locked",
                details={"locked_until": credentials.locked_until.isoformat()},
            )
        
        # Verify PIN using bcrypt (must match CLI UserService hashing)
        if not pwd_context.verify(request.pin, credentials.pin_hash):
            # Increment failed attempts
            await uow.credentials.increment_failed_attempts(request.user_uuid)

            await _emit_auth_event(
                topic="auth.login.failed",
                user_uuid=request.user_uuid,
                user_name=user.full_name,
                reason="invalid_pin",
            )
            await uow.commit()

            raise_api_error(
                status_code=401,
                error_code="AUTH_INVALID_CREDENTIALS",
                message="Invalid credentials",
            )
        
        # Reset failed attempts on successful login
        await uow.credentials.reset_failed_attempts(request.user_uuid)
        await uow.credentials.update_last_login(request.user_uuid)

        await _emit_auth_event(
            topic="auth.login.success",
            user_uuid=request.user_uuid,
            user_name=user.full_name,
            reason=None,
        )
        await uow.commit()
        
        logger.info(f"Authentication successful for user: {user.uuid}")
        
        # Get user roles from auth_access_policies table
        access_policies = await uow.auth_access_policies.get_user_policies(user.uuid, resource_type="role")
        user_roles = [policy.permission for policy in access_policies] if access_policies else ["user"]
        
        # If no roles found, default to "user" role
        if not user_roles:
            user_roles = ["user"]
        
        logger.info(f"User roles loaded: {user_roles}", extra={"user_uuid": user.uuid, "roles": user_roles})
        
        user_permissions = []
        
        # Extract User-Agent from request headers for device detection
        user_agent = request_obj.headers.get("user-agent", "")
        device_uuid = "web-client"  # TODO: Generate proper device UUID from client
        
        # Generate JWT access token with proper roles and permissions
        jwt_token = auth_manager.generate_jwt_token(
            user_uuid=user.uuid,
            username=user.full_name,
            roles=user_roles,
            permissions=user_permissions,
            device_uuid=device_uuid
        )
        
        # Generate refresh token for token renewal
        refresh_token = auth_manager.generate_refresh_token(
            user_uuid=user.uuid,
            username=user.full_name,
            roles=user_roles,
            permissions=user_permissions,
            device_uuid=device_uuid
        )
        
        # Create session record in database using AsyncSessionService + UoW
        try:
            from aico.security.async_session_service import AsyncSessionService
            session_service = AsyncSessionService()
            
            # Create session for access token
            await session_service.create_session(
                uow=uow,
                user_uuid=user.uuid,
                device_uuid=device_uuid,
                jwt_token=jwt_token,
                expires_in_minutes=15,  # Access token expiry
                session_type="rest"
            )
            
            # Create session for refresh token
            await session_service.create_session(
                uow=uow,
                user_uuid=user.uuid,
                device_uuid=device_uuid,
                jwt_token=refresh_token,
                expires_in_minutes=7*24*60,  # 7 days for refresh token
                session_type="refresh"
            )
            
            # Commit session records
            await uow.commit()
            
            logger.info("Sessions created successfully", extra={
                "user_uuid": user.uuid,
                "device_uuid": device_uuid
            })
            
        except Exception as e:
            logger.error(f"Failed to create session records: {e}", extra={
                "user_uuid": user.uuid,
                "error_type": type(e).__name__
            })
            # Don't fail authentication if session creation fails
            # Sessions are for tracking/revocation, not required for auth to work
        
        response = AuthenticationResponse(
            success=True,
            user=_user_to_response(user),
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            last_login=credentials.last_login.isoformat() if credentials.last_login else None
        )
        logger.info(f"Authentication success response: {response.dict()}")
        return response
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            from datetime import datetime, UTC
            import uuid

            now = datetime.now(UTC)
            ip_address = getattr(request_obj.client, "host", None)
            device_type = request_obj.headers.get("user-agent", None)
            await uow.system_events.create(
                SystemEvent(
                    timestamp=now.isoformat().replace("+00:00", "Z"),
                    topic="auth.login.failed",
                    source="backend.api.users",
                    message_type="auth",
                    message_id=str(uuid.uuid4()),
                    priority=1,
                    correlation_id=None,
                    payload=None,
                    metadata={
                        "user_uuid": request.user_uuid,
                        "user_name": None,
                        "ip_address": ip_address,
                        "device_type": device_type,
                        "reason": "system_error",
                    },
                    created_at=now,
                )
            )
            await uow.commit()
        except Exception:
            # Avoid masking the original auth failure.
            pass
        raise_api_error(
            status_code=500,
            error_code="AUTH_SYSTEM_ERROR",
            message="Authentication system error",
        )


@router.post(
    "/refresh",
    response_model=AuthenticationResponse,
    responses=error_responses(400, 401, 500),
)
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
            raise_api_error(
                status_code=400,
                error_code="AUTH_REFRESH_TOKEN_REQUIRED",
                message="No refresh token provided",
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
                raise_api_error(
                    status_code=401,
                    error_code="AUTH_REFRESH_TOKEN_INVALID",
                    message="Invalid token type - refresh token required",
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
            raise_api_error(
                status_code=401,
                error_code="AUTH_REFRESH_TOKEN_EXPIRED",
                message="Refresh token expired - please login again",
            )
        except jwt.InvalidTokenError:
            raise_api_error(
                status_code=401,
                error_code="AUTH_REFRESH_TOKEN_INVALID",
                message="Invalid refresh token",
            )
            
    except HTTPException:
        # Preserve intended API error status codes produced by raise_api_error().
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise_api_error(
            status_code=500,
            error_code="AUTH_REFRESH_SYSTEM_ERROR",
            message="Token refresh system error",
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
        raise_api_error(status_code=500, error_code="USER_SERVICE_NOT_INITIALIZED", message="User service not initialized")
    
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
        raise_api_error(status_code=500, error_code="USER_SERVICE_NOT_INITIALIZED", message="User service not initialized")
    
    # Validate UUID format
    validate_uuid(user_uuid)
    
    success = await user_service.unlock_user(user_uuid)
    if not success:
        raise_api_error(
            status_code=404,
            error_code="USER_UNLOCK_NOT_FOUND",
            message="User not found or no authentication configured",
        )
    
    logger.info("User unlocked via API", extra={
        "user_uuid": user_uuid,
        "unlocked_by": admin_user.get("user_uuid") if admin_user else "unknown"
    })


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 500),
)
async def logout_user(request: Request):
    """Logout user by revoking current JWT token"""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REQUIRED", message="No valid token provided")
    
    token = auth_header.split(" ")[1]
    
    if not auth_manager:
        raise_api_error(status_code=500, error_code="AUTH_MANAGER_NOT_INITIALIZED", message="Authentication manager not initialized")
    
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


@router.post(
    "/refresh/legacy",
    response_model=AuthenticationResponse,
    deprecated=True,
    responses=error_responses(401, 404, 500),
)
async def refresh_token_legacy(
    request: Request,
    auth_manager = Depends(get_auth_manager),
    uow: UnitOfWork = Depends(get_uow),
):
    """Refresh JWT token for authenticated user with session rotation"""
    # Extract current token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise_api_error(status_code=401, error_code="AUTH_TOKEN_REQUIRED", message="No valid token provided")
    
    token = auth_header.split(" ")[1]
    
    if not auth_manager:
        raise_api_error(status_code=500, error_code="AUTH_MANAGER_NOT_INITIALIZED", message="Authentication manager not initialized")
    
    # Use the new refresh_token method from auth_manager
    new_token = auth_manager.refresh_token(token, device_uuid="web-client")
    
    if not new_token:
        raise_api_error(
            status_code=401,
            error_code="AUTH_TOKEN_REFRESH_FAILED",
            message="Token refresh failed - token may be expired or revoked",
        )
    
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
        raise_api_error(status_code=500, error_code="AUTH_TOKEN_DECODE_FAILED", message="Failed to decode new token")
    
    # Get user data for response
    user = await uow.users.get_by_id(user_uuid)
    if not user:
        raise_api_error(status_code=404, error_code="USER_NOT_FOUND", message="User not found")
    
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
    uow: UnitOfWork = Depends(get_uow),
) -> UserStatsResponse:
    """Get user statistics"""
    try:
        users = await uow.users.list(filters={}, limit=100000)
        total_users = len(users)
        active_users = sum(1 for u in users if bool(getattr(u, "is_active", False)))
        users_by_type: dict[str, int] = {}
        for u in users:
            user_type = getattr(u, "user_type", None) or "unknown"
            users_by_type[user_type] = users_by_type.get(user_type, 0) + 1

        # Placeholder until we have a proper "last_login" field in a repository.
        # Keep schema contract stable.
        recent_logins = 0

        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            users_by_type=users_by_type,
            recent_logins=recent_logins,
        )
    except Exception as e:
        logger.error(f"Failed to compute user stats: {e}")
        raise_api_error(status_code=500, error_code="USER_STATS_FAILED", message="Failed to compute user stats")
