"""
Base Repository Interfaces

Protocol-based repository interfaces for type-safe data access.
All concrete repository implementations must implement these protocols.
"""

from typing import Protocol, TypeVar, Generic, Optional, List, Dict, Any
from abc import abstractmethod

T = TypeVar('T')


class Repository(Protocol, Generic[T]):
    """
    Base repository interface for CRUD operations.
    
    Generic type T represents the domain model (e.g., Goal, User, Plan).
    All repositories should implement this protocol for consistency.
    """
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Domain model instance to persist
            
        Returns:
            Created entity with any database-generated fields populated
            
        Raises:
            ValueError: If entity validation fails
            IntegrityError: If unique constraints are violated
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Retrieve entity by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Entity if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Update existing entity.
        
        Args:
            entity: Domain model with updated values
            
        Returns:
            Updated entity
            
        Raises:
            ValueError: If entity doesn't exist
        """
        ...
    
    @abstractmethod
    async def delete(self, id: str) -> None:
        """
        Delete entity by primary key.
        
        Args:
            id: Primary key value
            
        Raises:
            ValueError: If entity doesn't exist
        """
        ...
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[T]:
        """
        List entities with optional filtering.
        
        Args:
            filters: Optional dictionary of field filters (e.g., {'user_id': 'user-123', 'status': 'active'})
            limit: Optional maximum number of results
            
        Returns:
            List of entities matching filters
        """
        ...
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching filters.
        
        Args:
            filters: Optional dictionary of field filters
            
        Returns:
            Number of entities matching filters
        """
        ...
