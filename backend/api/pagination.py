"""
Standardized Pagination Schemas for AICO Backend API

Provides consistent pagination contract across all list endpoints:
- Query parameters: limit, offset
- Response format: {items: T[], total: int, limit: int, offset: int}
"""

from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated response for all list endpoints.
    
    Contract:
    - items: Array of results for current page
    - total: Total count of items matching query (for pagination UI)
    - limit: Page size used (echoed from request)
    - offset: Offset used (echoed from request)
    
    Example:
        {
            "items": [...],
            "total": 150,
            "limit": 50,
            "offset": 0
        }
    """
    items: List[T] = Field(..., description="Array of items for current page")
    total: int = Field(..., description="Total count of items matching query")
    limit: int = Field(..., description="Page size limit used")
    offset: int = Field(..., description="Pagination offset used")
    
    class Config:
        # Allow arbitrary types for generic T
        arbitrary_types_allowed = True


class PaginationParams(BaseModel):
    """
    Standardized pagination query parameters.
    
    Usage in FastAPI endpoints:
        @router.get("/items")
        async def list_items(
            limit: int = Query(50, ge=1, le=100),
            offset: int = Query(0, ge=0),
        ):
            ...
    """
    limit: int = Field(50, ge=1, le=100, description="Number of items to return (max 100)")
    offset: int = Field(0, ge=0, description="Number of items to skip")
