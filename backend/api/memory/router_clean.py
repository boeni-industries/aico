"""
Memory Stats API Router

Provides statistics endpoints for semantic memory (ChromaDB) and working memory (LMDB).
Knowledge Graph endpoints are in /backend/api/kg/router.py
"""

from typing import Annotated, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from aico.core.logging import get_logger
from backend.api.memory.dependencies import get_current_user

logger = get_logger("backend", "api.memory")

print("\n=== CREATING MEMORY ROUTER ===")
router = APIRouter(prefix="/memory", tags=["memory"])
print(f"Router created with prefix: /memory")


# ============================================================================
# Response Models
# ============================================================================

class CollectionInfo(BaseModel):
    """Collection metadata."""
    name: str
    count: int
    dimension: int

class SemanticMemoryStatsResponse(BaseModel):
    """Semantic memory statistics."""
    total_vectors: int
    collections: List[CollectionInfo]
    index_size_mb: float
    avg_retrieval_latency_ms: float


class ActivityEntry(BaseModel):
    """Recent activity entry."""
    id: str
    timestamp: str
    action: str
    key: str

class WorkingMemoryStatsResponse(BaseModel):
    """Working memory statistics."""
    active_items: int
    capacity: int
    utilization_percent: float
    ttl_utilization_percent: float
    eviction_rate_per_min: float
    recent_activity: List[ActivityEntry]


# ============================================================================
# Semantic Memory Endpoints
# ============================================================================

@router.get("/semantic/stats", response_model=SemanticMemoryStatsResponse)
async def get_semantic_stats(
    user: Annotated[dict, Depends(get_current_user)],
    request: Request
):
    """
    Get semantic memory (ChromaDB) statistics.
    
    Returns:
        - total_vectors: Total vector count across collections
        - collections: List of collections with counts and dimensions
        - index_size_mb: Total index size in megabytes
        - avg_retrieval_latency_ms: Average query latency
    """
    print("\n=== SEMANTIC STATS ENDPOINT CALLED ===")
    try:
        user_id = user.get("user_id")
        print(f"User ID: {user_id}")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Get memory manager from AI registry
        print("Getting memory manager from ai_registry...")
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        print(f"Memory manager: {memory_manager}")
        
        if not memory_manager:
            print("ERROR: Memory manager is None!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not initialized"
            )
        
        print(f"Has _semantic_store: {hasattr(memory_manager, '_semantic_store')}")
        if not hasattr(memory_manager, '_semantic_store'):
            print("ERROR: No _semantic_store attribute!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic memory not initialized"
            )
        
        semantic_store = memory_manager._semantic_store
        print(f"Semantic store: {semantic_store}")
        
        if not semantic_store:
            print("ERROR: Semantic store is None!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic memory not initialized"
            )
        
        # Get stats from semantic store
        print("Calling get_stats()...")
        stats = semantic_store.get_stats()
        print(f"Stats returned: {stats}")
        
        # Convert collections to proper Pydantic models
        collections = [
            CollectionInfo(**col) for col in stats.get('collections', [])
        ]
        
        return SemanticMemoryStatsResponse(
            total_vectors=stats.get('total_vectors', 0),
            collections=collections,
            index_size_mb=stats.get('index_size_mb', 0.0),
            avg_retrieval_latency_ms=stats.get('avg_retrieval_latency_ms', 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get semantic memory stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve semantic memory statistics: {str(e)}"
        )


# ============================================================================
# Working Memory Endpoints
# ============================================================================

@router.get("/working/stats", response_model=WorkingMemoryStatsResponse)
async def get_working_stats(
    user: Annotated[dict, Depends(get_current_user)],
    request: Request
):
    """
    Get working memory (LMDB) statistics.
    
    Returns:
        - active_items: Current number of items in memory
        - capacity: Maximum capacity
        - utilization_percent: Memory utilization percentage
        - ttl_utilization_percent: TTL-based utilization
        - eviction_rate_per_min: Items evicted per minute
        - recent_activity: Recent read/write/evict operations
    """
    print("\n=== WORKING STATS ENDPOINT CALLED ===")
    try:
        user_id = user.get("user_id")
        print(f"User ID: {user_id}")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Get memory manager from AI registry
        print("Getting memory manager from ai_registry...")
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        print(f"Memory manager: {memory_manager}")
        
        if not memory_manager:
            print("ERROR: Memory manager is None!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not initialized"
            )
        
        print(f"Has _working_store: {hasattr(memory_manager, '_working_store')}")
        if not hasattr(memory_manager, '_working_store'):
            print("ERROR: No _working_store attribute!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Working memory not initialized"
            )
        
        working_store = memory_manager._working_store
        print(f"Working store: {working_store}")
        
        if not working_store:
            print("ERROR: Working store is None!")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Working memory not initialized"
            )
        
        # Get stats from working store
        print("Calling get_stats()...")
        stats = await working_store.get_stats()
        print(f"Stats returned: {stats}")
        
        # Convert recent_activity to proper Pydantic models
        recent_activity = [
            ActivityEntry(**activity) for activity in stats.get('recent_activity', [])
        ]
        
        return WorkingMemoryStatsResponse(
            active_items=stats.get('active_items', 0),
            capacity=stats.get('capacity', 10000),
            utilization_percent=stats.get('utilization_percent', 0.0),
            ttl_utilization_percent=stats.get('ttl_utilization_percent', 0.0),
            eviction_rate_per_min=stats.get('eviction_rate_per_min', 0.0),
            recent_activity=recent_activity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get working memory stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve working memory statistics: {str(e)}"
        )
