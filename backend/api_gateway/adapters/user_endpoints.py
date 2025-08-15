"""
User Management Endpoints for AICO API Gateway

Provides REST API endpoints for user CRUD operations and authentication.
Integrates with UserService and follows AICO's security patterns.
"""

from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from aico.core.logging import get_logger
from aico.data.libsql.connection import LibSQLConnection
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.data.user import UserService, UserProfile
from backend.api_gateway.core.auth import AuthenticationManager

security = HTTPBearer()


# Pydantic models for request/response
class CreateUserRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=50)
    user_type: str = Field(default='parent', regex='^(parent|child|admin)$')
    pin: Optional[str] = Field(None, min_length=4, max_length=8)


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=50)
    user_type: Optional[str] = Field(None, regex='^(parent|child|admin)$')


class AuthenticateRequest(BaseModel):
    user_uuid: str = Field(..., regex='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    pin: str = Field(..., min_length=4, max_length=8)


class SetPinRequest(BaseModel):
    new_pin: str = Field(..., min_length=4, max_length=8)


class UserResponse(BaseModel):
    uuid: str
    full_name: str
    nickname: Optional[str]
    user_type: str
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class AuthenticationResponse(BaseModel):
    success: bool
    user: Optional[UserResponse] = None
    jwt_token: Optional[str] = None
    error: Optional[str] = None
    last_login: Optional[str] = None


def create_user_endpoints(user_service: UserService, auth_manager: AuthenticationManager) -> FastAPI:
    """Create user management FastAPI application"""
    
    logger = get_logger("api_gateway", "user_endpoints")
    
    app = FastAPI(
        title="AICO User Management API",
        description="User CRUD operations and authentication endpoints",
        version="1.0.0"
    )
    
    async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify admin authentication for user management operations"""
        try:
            token = credentials.credentials
            
            # Use auth_manager to validate JWT token
            import jwt
            payload = jwt.decode(
                token,
                auth_manager._get_jwt_secret(),
                algorithms=[auth_manager.jwt_algorithm]
            )
            
            # Check if user has admin permissions
            roles = payload.get("roles", [])
            permissions = set(payload.get("permissions", []))
            
            if "admin" not in roles and "*" not in permissions and "user.*" not in permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    # User CRUD Endpoints
    
    @app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def create_user(
        request: CreateUserRequest,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Create a new user"""
        try:
            user = await user_service.create_user(
                full_name=request.full_name,
                nickname=request.nickname,
                user_type=request.user_type,
                pin=request.pin
            )
            
            logger.info("User created via API", extra={
                "user_uuid": user.uuid,
                "full_name": user.full_name,
                "created_by": admin_user.get("sub")
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
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    @app.get("/users/{user_uuid}", response_model=UserResponse)
    async def get_user(
        user_uuid: str,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Get user by UUID"""
        try:
            # Validate UUID format
            uuid.UUID(user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format"
            )
        
        try:
            user = await user_service.get_user(user_uuid)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse(
                uuid=user.uuid,
                full_name=user.full_name,
                nickname=user.nickname,
                user_type=user.user_type,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else None,
                updated_at=user.updated_at.isoformat() if user.updated_at else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user"
            )
    
    @app.put("/users/{user_uuid}", response_model=UserResponse)
    async def update_user(
        user_uuid: str,
        request: UpdateUserRequest,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Update user profile"""
        try:
            uuid.UUID(user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format"
            )
        
        try:
            # Convert request to dict, excluding None values
            updates = {k: v for k, v in request.dict().items() if v is not None}
            
            if not updates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No updates provided"
                )
            
            user = await user_service.update_user(user_uuid, updates)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            logger.info("User updated via API", extra={
                "user_uuid": user_uuid,
                "updated_fields": list(updates.keys()),
                "updated_by": admin_user.get("sub")
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
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
    
    @app.delete("/users/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_user(
        user_uuid: str,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Delete user (soft delete)"""
        try:
            uuid.UUID(user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format"
            )
        
        try:
            success = await user_service.delete_user(user_uuid)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            logger.info("User deleted via API", extra={
                "user_uuid": user_uuid,
                "deleted_by": admin_user.get("sub")
            })
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
    
    @app.get("/users", response_model=List[UserResponse])
    async def list_users(
        user_type: Optional[str] = None,
        limit: int = 100,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """List users with optional filtering"""
        if limit > 1000:
            limit = 1000  # Cap maximum limit
        
        try:
            users = await user_service.list_users(user_type=user_type, limit=limit)
            
            return [
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
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list users"
            )
    
    # Authentication Endpoints
    
    @app.post("/auth/authenticate", response_model=AuthenticationResponse)
    async def authenticate_user(request: AuthenticateRequest):
        """Authenticate user with PIN and return JWT token"""
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
    
    @app.post("/users/{user_uuid}/pin", status_code=status.HTTP_204_NO_CONTENT)
    async def set_user_pin(
        user_uuid: str,
        request: SetPinRequest,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Set or update user's PIN"""
        try:
            uuid.UUID(user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format"
            )
        
        try:
            success = await user_service.set_user_pin(user_uuid, request.new_pin)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            logger.info("User PIN updated via API", extra={
                "user_uuid": user_uuid,
                "updated_by": admin_user.get("sub")
            })
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to set user PIN: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set user PIN"
            )
    
    @app.post("/users/{user_uuid}/unlock", status_code=status.HTTP_204_NO_CONTENT)
    async def unlock_user(
        user_uuid: str,
        admin_user: dict = Depends(verify_admin_token)
    ):
        """Unlock user account"""
        try:
            uuid.UUID(user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format"
            )
        
        try:
            success = await user_service.unlock_user(user_uuid)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found or no authentication configured"
                )
            
            logger.info("User unlocked via API", extra={
                "user_uuid": user_uuid,
                "unlocked_by": admin_user.get("sub")
            })
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unlock user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unlock user"
            )
    
    @app.get("/users/stats")
    async def get_user_stats(admin_user: dict = Depends(verify_admin_token)):
        """Get user statistics"""
        try:
            stats = await user_service.get_user_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user statistics"
            )
    
    return app
