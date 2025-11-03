"""
Knowledge Graph API dependencies.

Provides dependency injection for KG-related resources.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from aico.core.logging import get_logger
from aico.data.user import UserService
from backend.core.service_container import ServiceContainer

logger = get_logger("backend", "api.kg.dependencies")
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    container: Annotated[ServiceContainer, Depends(lambda: None)]  # Injected by router
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token
        container: Service container (injected)
        
    Returns:
        User dict with user_id and other claims
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get user service from container
        user_service: UserService = container.get_service("user_service")
        
        # Verify JWT token
        token = credentials.credentials
        user_data = user_service.verify_token(token)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_data
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_kg_storage(
    container: Annotated[ServiceContainer, Depends(lambda: None)]
):
    """
    Get KG storage instance from service container.
    
    Args:
        container: Service container (injected)
        
    Returns:
        PropertyGraphStorage instance
    """
    try:
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
        
    except Exception as e:
        logger.error(f"Failed to get KG storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge graph storage unavailable"
        )


async def get_db_connection(
    container: Annotated[ServiceContainer, Depends(lambda: None)]
):
    """
    Get database connection from service container.
    
    Args:
        container: Service container (injected)
        
    Returns:
        EncryptedLibSQLConnection instance
    """
    try:
        return container.get_service("database")
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection unavailable"
        )
