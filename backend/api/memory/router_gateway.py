"""
Gateway memory stats endpoints - proxy to core via NATS.

Gateway is HTTP termination only. All memory business logic lives in core.
These endpoints validate auth and proxy requests to core via NATS request/reply.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.api.dependencies import get_current_user
from backend.api.errors import raise_api_error

router = APIRouter(prefix="/memory", tags=["memory"])


class SemanticMemoryStatsResponse(BaseModel):
    """Semantic memory statistics."""
    total_vectors: int
    collections: list
    index_size_mb: float
    avg_retrieval_latency_ms: float
    retrieval_quality_percent: float


class WorkingMemoryStatsResponse(BaseModel):
    """Working memory statistics."""
    active_items: int
    capacity: int
    utilization_percent: float
    ttl_utilization_percent: float


@router.get("/semantic/stats", response_model=SemanticMemoryStatsResponse)
async def get_semantic_stats(
    user: Annotated[dict, Depends(get_current_user)],
    request: Request
):
    """
    Get semantic memory statistics.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise_api_error(
            status_code=401,
            error_code="AUTH_MISSING_USER_ID",
            message="User ID not found in token",
        )
    
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        stats_data = await nats_client.request_semantic_memory_stats()
        
        return SemanticMemoryStatsResponse(**stats_data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="SEMANTIC_MEMORY_STATS_FAILED",
            message=f"Failed to retrieve semantic memory statistics: {str(e)}",
        )


@router.get("/working/stats", response_model=WorkingMemoryStatsResponse)
async def get_working_stats(
    user: Annotated[dict, Depends(get_current_user)],
    request: Request
):
    """
    Get working memory statistics.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise_api_error(
            status_code=401,
            error_code="AUTH_MISSING_USER_ID",
            message="User ID not found in token",
        )
    
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        stats_data = await nats_client.request_working_memory_stats()
        
        return WorkingMemoryStatsResponse(**stats_data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="WORKING_MEMORY_STATS_FAILED",
            message=f"Failed to retrieve working memory statistics: {str(e)}",
        )
