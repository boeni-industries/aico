"""
Knowledge Graph API dependencies.

Provides dependency injection for KG-related resources.
"""

from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from aico.core.logging import get_logger

logger = get_logger("backend", "api.kg.dependencies")
security = HTTPBearer()


def get_auth_manager(request: Request):
    """Get auth manager from service container via FastAPI app state."""
    if not hasattr(request.app.state, 'service_container'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service container not initialized"
        )
    container = request.app.state.service_container
    security_plugin = container.get_service("security_plugin")
    return security_plugin.auth_manager


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_manager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """
    Verify JWT token and return user information.
    
    Args:
        credentials: HTTP Bearer token
        auth_manager: Auth manager from service container
        
    Returns:
        User dict with user_id and other claims
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        # Decode and validate JWT token
        try:
            payload = jwt.decode(
                token,
                auth_manager._get_jwt_secret(),
                algorithms=["HS256"],
                options={"verify_aud": False}  # Skip audience validation for CLI compatibility
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            return {
                "user_id": user_id,
                "username": payload.get("username"),
                "role": payload.get("role", "user")
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_kg_storage(request: Request):
    """
    Get KG storage instance from service container.
    
    Args:
        request: FastAPI request object
        
    Returns:
        PropertyGraphStorage instance
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service container not initialized"
            )
        
        container = request.app.state.service_container
        
        # Get database connection
        db_connection = container.get_service("database")
        
        # Get ChromaDB client
        from aico.core.paths import AICOPaths
        import chromadb
        from chromadb.config import Settings
        
        chromadb_path = AICOPaths.get_semantic_memory_path()
        chromadb_client = chromadb.PersistentClient(
            path=str(chromadb_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=False)
        )
        
        # Create storage instance
        from aico.ai.knowledge_graph import PropertyGraphStorage
        storage = PropertyGraphStorage(db_connection, chromadb_client, None)
        
        return storage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KG storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge graph storage unavailable"
        )


def get_db_connection(request: Request):
    """
    Get database connection from service container.
    
    Args:
        request: FastAPI request object
        
    Returns:
        EncryptedLibSQLConnection instance
    """
    try:
        if not hasattr(request.app.state, 'service_container'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service container not initialized"
            )
        
        container = request.app.state.service_container
        return container.get_service("database")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection unavailable"
        )
