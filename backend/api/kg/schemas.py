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


class DuplicateNodePair(BaseModel):
    """Schema for a pair of duplicate nodes."""
    
    id1: str = Field(..., description="ID of first node")
    name1: str = Field(..., description="Name/label of first node")
    label1: str = Field(..., description="Entity type of first node")
    id2: str = Field(..., description="ID of second node")
    name2: str = Field(..., description="Name/label of second node")
    label2: str = Field(..., description="Entity type of second node")
    similarity: float = Field(..., description="Similarity score (0-1)")


class DuplicatesResponse(BaseModel):
    """Response schema for duplicate nodes detection."""
    
    total_duplicates: int = Field(..., description="Total number of duplicate pairs")
    pairs: List[DuplicateNodePair] = Field(..., description="List of duplicate node pairs")


class HealthMetrics(BaseModel):
    """Health and quality metrics."""
    orphaned_edges: int = Field(..., description="Edges pointing to non-existent nodes")
    duplicate_nodes: int = Field(..., description="Potential duplicate nodes")
    stale_nodes_count: int = Field(..., description="Nodes not updated in 30+ days")
    stale_nodes_percent: float = Field(..., description="Percentage of stale nodes")
    property_completeness: float = Field(..., description="Average properties per node")
    nodes_added_24h: int = Field(..., description="Nodes added in last 24 hours")
    edges_added_24h: int = Field(..., description="Edges added in last 24 hours")


class StructureMetrics(BaseModel):
    """Graph structure and topology metrics."""
    graph_density: float = Field(..., description="Ratio of actual to possible edges")
    average_degree: float = Field(..., description="Average connections per node")
    max_degree: int = Field(..., description="Maximum connections for any node")
    min_degree: int = Field(..., description="Minimum connections for any node")
    isolated_nodes: int = Field(..., description="Nodes with zero connections")
    connected_components: int = Field(..., description="Number of disconnected subgraphs")
    largest_component_size: int = Field(..., description="Size of largest connected component")


class CentralityMetrics(BaseModel):
    """Node centrality and importance metrics."""
    top_by_degree: List[Dict[str, Any]] = Field(..., description="Most connected nodes")
    top_by_pagerank: List[Dict[str, Any]] = Field(..., description="Most important nodes by PageRank")
    top_by_betweenness: List[Dict[str, Any]] = Field(..., description="Bridge nodes connecting clusters")


class TemporalMetrics(BaseModel):
    """Temporal activity metrics."""
    growth_rate_7d: float = Field(..., description="Node growth rate over 7 days")
    growth_rate_30d: float = Field(..., description="Node growth rate over 30 days")
    most_active_day: Optional[str] = Field(None, description="Day with most node creation")
    activity_by_day: Dict[str, int] = Field(..., description="Node creation by day (last 7 days)")


class ClusteringMetrics(BaseModel):
    """Clustering and community metrics."""
    global_clustering_coefficient: float = Field(..., description="Overall graph cohesion")
    average_clustering_coefficient: float = Field(..., description="Average local clustering")
    communities_detected: int = Field(..., description="Number of communities found")
    modularity_score: float = Field(..., description="Quality of community structure")


class GraphStatsResponse(BaseModel):
    """Response schema for comprehensive graph statistics."""
    
    # Basic counts
    total_nodes: int = Field(..., description="Total number of nodes")
    current_nodes: int = Field(..., description="Number of current nodes")
    historical_nodes: int = Field(..., description="Number of historical nodes")
    total_edges: int = Field(..., description="Total number of edges")
    current_edges: int = Field(..., description="Number of current edges")
    historical_edges: int = Field(..., description="Number of historical edges")
    total_node_properties: int = Field(..., description="Total number of node properties across all nodes")
    node_types: Dict[str, int] = Field(..., description="Node count by type")
    edge_types: Dict[str, int] = Field(..., description="Edge count by type")
    storage_size_mb: float = Field(..., description="Approximate storage size in MB")
    user_id: str = Field(..., description="User ID")
    
    # Priority 1: Health & Quality
    health: HealthMetrics = Field(..., description="Health and quality metrics")
    duplicate_pairs: Optional[List[DuplicateNodePair]] = Field(None, description="Actual duplicate node pairs (if requested)")
    
    # Priority 2: Graph Structure
    structure: StructureMetrics = Field(..., description="Graph structure metrics")
    
    # Priority 3: Knowledge Insights
    temporal: TemporalMetrics = Field(..., description="Temporal activity metrics")
    
    # Priority 4: Advanced Analytics
    centrality: CentralityMetrics = Field(..., description="Centrality and importance metrics")
    clustering: ClusteringMetrics = Field(..., description="Clustering and community metrics")
