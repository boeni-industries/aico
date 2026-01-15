"""
Memory & AMS API Router

Comprehensive API for knowledge graph, semantic memory, working memory, and AMS.
Provides full introspection, analytics, and query capabilities.
"""

from typing import Annotated, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from aico.core.logging import get_logger
from backend.api.memory.dependencies import get_current_user

logger = get_logger("backend.api.memory")

router = APIRouter(prefix="/memory", tags=["memory"])


# ============================================================================
# Request/Response Models
# ============================================================================

class NodeResponse(BaseModel):
    """Knowledge graph node with full properties."""
    id: str
    user_id: str
    label: str
    properties: Dict[str, Any]
    confidence: float
    source_text: str
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    is_current: int
    canonical_id: Optional[str] = None
    aliases: Optional[List[str]] = None
    # Computed fields
    connection_count: Optional[int] = None
    pagerank_score: Optional[float] = None
    centrality_score: Optional[float] = None


class EdgeResponse(BaseModel):
    """Knowledge graph edge with full properties."""
    id: str
    user_id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any]
    confidence: float
    source_text: str
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    is_current: int


class GraphStatsResponse(BaseModel):
    """Overall graph statistics."""
    total_nodes: int
    total_edges: int
    total_node_properties: int
    total_edge_properties: int
    entity_type_distribution: Dict[str, int]
    relationship_type_distribution: Dict[str, int]
    avg_properties_per_node: float
    avg_connections_per_node: float
    graph_density: float
    largest_component_size: int
    num_communities: int


class GraphPathResponse(BaseModel):
    """Path through the graph."""
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    total_weight: float
    hop_count: int


class AnalyticsResponse(BaseModel):
    """Graph analytics results."""
    pagerank: Dict[str, float]
    centrality: Dict[str, float]
    communities: List[Dict[str, Any]]
    temporal_patterns: Dict[str, Any]
    knowledge_gaps: List[Dict[str, Any]]
    top_entities: List[Dict[str, Any]]


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
    retrieval_quality_percent: float = 0.0


class ActivityEntry(BaseModel):
    """Recent activity entry"""
    id: str = Field(..., description="Activity ID")
    timestamp: str = Field(..., description="Activity timestamp")
    action: str = Field(..., description="Action type (stored, evict)")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    role: Optional[str] = Field(None, description="Message role (user, assistant)")
    preview: Optional[str] = Field(None, description="Message preview")


class WorkingMemoryStatsResponse(BaseModel):
    """Working memory statistics."""
    active_items: int
    capacity: int
    utilization_percent: float
    ttl_utilization_percent: float
    eviction_rate_per_min: float
    recent_activity: List[ActivityEntry]


# ============================================================================
# NOTE: Knowledge Graph endpoints are in /backend/api/kg/router.py
# This router only handles semantic memory and working memory stats
# ============================================================================

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
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not initialized"
            )
        
        if not hasattr(memory_manager, '_semantic_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic memory not initialized"
            )
        
        semantic_store = memory_manager._semantic_store
        
        if not semantic_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic memory not initialized"
            )
        
        # Get stats from semantic store (synchronous method)
        stats = semantic_store.get_stats()
        
        # Convert collections to proper Pydantic models
        collections = [
            CollectionInfo(**col) for col in stats.get('collections', [])
        ]
        
        return SemanticMemoryStatsResponse(
            total_vectors=stats.get('total_vectors', 0),
            collections=collections,
            index_size_mb=stats.get('index_size_mb', 0.0),
            avg_retrieval_latency_ms=stats.get('avg_retrieval_latency_ms', 0.0),
            retrieval_quality_percent=stats.get('retrieval_quality_percent', 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"❌ SEMANTIC STATS ENDPOINT FAILURE: {e}"
        logger.error(error_msg)
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
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Get memory manager from AI registry
        from aico.ai import ai_registry
        memory_manager = ai_registry.get("memory")
        
        if not memory_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory manager not initialized"
            )
        
        if not hasattr(memory_manager, '_working_store'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Working memory not initialized"
            )
        
        working_store = memory_manager._working_store
        
        if not working_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Working memory not initialized"
            )
        
        # Get stats from working store
        stats = await working_store.get_stats()
        
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
        error_msg = f"❌ WORKING STATS ENDPOINT FAILURE: {e}"
        logger.error(error_msg)
        print(f"\n{'='*80}")
        print(f"❌ /api/v1/memory/working/stats ENDPOINT FAILED")
        print(f"{'='*80}")
        print(f"Error: {e}")
        print(f"User ID: {user.get('user_id')}")
        print(f"{'='*80}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve working memory statistics: {str(e)}"
        )


# END OF FILE - All KG endpoints removed, they are in /backend/api/kg/router.py
