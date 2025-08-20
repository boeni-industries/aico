"""
Global API Dependencies

Shared dependencies used across multiple API domains.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
import jwt
from aico.core.logging import get_logger

security = HTTPBearer()
logger = get_logger("api", "dependencies")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    Used for endpoints requiring any authenticated user.
    """
    try:
        token = credentials.credentials
        # Note: auth_manager will be injected via dependency injection in actual usage
        # This is a placeholder that will be updated when integrating with main.py
        
        # For now, return a basic structure
        # TODO: Integrate with AuthenticationManager from main.py
        return {
            "user_uuid": "placeholder",
            "username": "placeholder", 
            "roles": [],
            "permissions": set(),
            "token": token
        }
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def create_auth_dependency(auth_manager):
    """
    Factory function to create auth dependency with injected auth_manager.
    This will be called from main.py during app initialization.
    """
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        try:
            token = credentials.credentials
            
            # Decode and validate JWT token
            try:
                payload = jwt.decode(
                    token,
                    auth_manager._get_jwt_secret(),
                    algorithms=[auth_manager.jwt_algorithm],
                    options={"verify_aud": False}
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if token is revoked
            if token in auth_manager.revoked_tokens:
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            return {
                "user_uuid": payload["user_uuid"],
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": set(payload.get("permissions", [])),
                "token": token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    return verify_token


def create_admin_dependency(auth_manager):
    """
    Factory function to create admin auth dependency.
    Requires admin role or appropriate permissions.
    """
    verify_token = create_auth_dependency(auth_manager)
    
    async def verify_admin(user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        roles = user.get("roles", [])
        permissions = user.get("permissions", set())
        
        if "admin" not in roles and "*" not in permissions and "admin.*" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user
    
    return verify_admin
