"""
Knowledge Graph API request/response schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GQLQueryRequest(BaseModel):
    """Request schema for GQL/Cypher query execution."""
    
    query: str = Field(..., description="GQL/Cypher query string", min_length=1)
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query parameters (future use)"
    )
    format: str = Field(
        default="dict",
        description="Output format: dict, json, csv, table",
        pattern="^(dict|json|csv|table)$"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of results (overrides query LIMIT)",
        ge=1,
        le=10000
    )


class GQLQueryResponse(BaseModel):
    """Response schema for GQL/Cypher query execution."""
    
    success: bool = Field(..., description="Whether query executed successfully")
    data: Any = Field(None, description="Query results (format depends on request)")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Query metadata (row count, columns, etc.)"
    )


class GraphStatsResponse(BaseModel):
    """Response schema for graph statistics."""
    
    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")
    node_types: Dict[str, int] = Field(..., description="Node count by type")
    edge_types: Dict[str, int] = Field(..., description="Edge count by type")
    user_id: str = Field(..., description="User ID")
