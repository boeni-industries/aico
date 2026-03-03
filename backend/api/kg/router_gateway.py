"""
Gateway KG endpoints - proxy to core via NATS.

Gateway is HTTP termination only. All KG business logic lives in core.
These endpoints validate auth and proxy requests to core via NATS request/reply.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.system.dependencies import get_current_user
from backend.api.errors import raise_api_error

router = APIRouter(prefix="/kg", tags=["kg"])


class KGStatsResponse(BaseModel):
    """Knowledge graph statistics."""
    total_nodes: int
    total_edges: int
    entity_types: list
    relation_types: list


class KGNodesResponse(BaseModel):
    """Knowledge graph nodes list."""
    nodes: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class KGEdgesResponse(BaseModel):
    """Knowledge graph edges list."""
    edges: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


@router.get("/stats", response_model=KGStatsResponse)
async def get_kg_stats(
    _auth: dict = Depends(get_current_user)
):
    """
    Get knowledge graph statistics.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        stats_data = await nats_client.request_kg_stats()
        
        return KGStatsResponse(**stats_data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_STATS_FAILED",
            message=f"Failed to retrieve KG statistics: {str(e)}",
        )


@router.get("/nodes", response_model=KGNodesResponse)
async def get_kg_nodes(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    _auth: dict = Depends(get_current_user)
):
    """
    Get knowledge graph nodes.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_nodes(limit=limit, offset=offset)
        
        return KGNodesResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_NODES_FAILED",
            message=f"Failed to retrieve KG nodes: {str(e)}",
        )


@router.get("/edges", response_model=KGEdgesResponse)
async def get_kg_edges(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    _auth: dict = Depends(get_current_user)
):
    """
    Get knowledge graph edges.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_edges(limit=limit, offset=offset)
        
        return KGEdgesResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_EDGES_FAILED",
            message=f"Failed to retrieve KG edges: {str(e)}",
        )
