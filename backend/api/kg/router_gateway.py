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
from backend.api.kg.schemas import ChangesResponse, GraphStatsResponse

router = APIRouter(prefix="/kg", tags=["kg"])


class KGNodesResponse(BaseModel):
    """Knowledge graph nodes list."""
    nodes: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class KGSchemaResponse(BaseModel):
    nodeLabels: List[str]
    relationshipTypes: List[str]
    nodeProperties: List[str]
    relationshipProperties: List[str]


class KGQueryTemplatesResponse(BaseModel):
    templates: List[Dict[str, Any]]


class KGEdgesResponse(BaseModel):
    """Knowledge graph edges list."""
    edges: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


@router.get("/stats", response_model=GraphStatsResponse)
async def get_kg_stats(
    user: dict = Depends(get_current_user)
):
    """
    Get knowledge graph statistics.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        stats_data = await nats_client.request_kg_stats(user_id=user_id)
        
        return GraphStatsResponse(**stats_data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_STATS_FAILED",
            message=f"Failed to retrieve KG statistics: {str(e)}",
        )


@router.get("/schema", response_model=KGSchemaResponse)
async def get_kg_schema(
    user: dict = Depends(get_current_user)
):
    """Get KG schema for autocomplete. Proxied to core via NATS."""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_schema(user_id=user_id)

        return KGSchemaResponse(**data)

    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_SCHEMA_FAILED",
            message=f"Failed to retrieve KG schema: {str(e)}",
        )


@router.get("/changes", response_model=ChangesResponse)
async def get_kg_changes(
    from_timestamp: str = Query(..., description="Start timestamp (ISO 8601)"),
    to_timestamp: str = Query(..., description="End timestamp (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=1000),
    user: dict = Depends(get_current_user),
):
    """Get KG changes in a time range. Proxied to core via NATS."""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_changes(
            user_id=user_id,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=limit,
        )

        return ChangesResponse(**data)

    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_CHANGES_FAILED",
            message=f"Failed to retrieve KG changes: {str(e)}",
        )


@router.get("/query-templates", response_model=KGQueryTemplatesResponse)
async def get_kg_query_templates(
    user: dict = Depends(get_current_user),
):
    """Get KG query templates. Proxied to core via NATS."""
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client

        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_query_templates(user_id=user_id)

        return KGQueryTemplatesResponse(**data)

    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_QUERY_TEMPLATES_FAILED",
            message=f"Failed to retrieve KG query templates: {str(e)}",
        )


@router.get("/nodes", response_model=KGNodesResponse)
async def get_kg_nodes(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    """
    Get knowledge graph nodes.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_nodes(user_id=user_id, limit=limit, offset=offset)
        
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
    user: dict = Depends(get_current_user)
):
    """
    Get knowledge graph edges.
    
    Gateway proxies this request to core via NATS request/reply.
    """
    try:
        from backend.api_gateway.core.nats_client import get_gateway_nats_client
        
        user_id = user.get("user_id")
        nats_client = get_gateway_nats_client()
        data = await nats_client.request_kg_edges(user_id=user_id, limit=limit, offset=offset)
        
        return KGEdgesResponse(**data)
        
    except Exception as e:
        raise_api_error(
            status_code=500,
            error_code="KG_EDGES_FAILED",
            message=f"Failed to retrieve KG edges: {str(e)}",
        )
