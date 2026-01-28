"""
Knowledge Graph API Router.

Provides REST endpoints for querying and managing the knowledge graph.
"""

import json
from pathlib import Path
from typing import Annotated, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from aico.core.logging import get_logger
from aico.ai.knowledge_graph.query import GQLQueryExecutor
from backend.api.kg.schemas import (
    GQLQueryRequest,
    GQLQueryResponse,
    GraphStatsResponse
)
from backend.api.kg.dependencies import (
    get_current_user,
    get_kg_storage
)
from backend.core.postgres_dependencies import get_uow
from aico.data.uow import UnitOfWork

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend.api.kg")

# Cache for stats endpoint (30 second TTL)
_stats_cache: dict[str, tuple[GraphStatsResponse, datetime]] = {}

# Include temporal endpoints
from backend.api.kg.temporal_router import router as temporal_router
router.include_router(temporal_router, tags=["temporal"])


@router.post("/query", response_model=GQLQueryResponse)
async def execute_gql_query(
    request: GQLQueryRequest,
    user: Annotated[dict, Depends(get_current_user)],
    kg_storage: Annotated[object, Depends(get_kg_storage)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> GQLQueryResponse:
    """
    Execute a GQL/Cypher query against the user's knowledge graph.
    
    **Authentication required:** Bearer token
    
    **Query Examples:**
    ```cypher
    # Find all people
    MATCH (p:PERSON) RETURN p.name
    
    # Find work relationships
    MATCH (p:PERSON)-[:WORKS_FOR]->(c:ORGANIZATION)
    RETURN p.name, c.name
    
    # Multi-hop traversal
    MATCH (a)-[]->(b)-[]->(c)
    WHERE a.type = 'PERSON'
    RETURN a, b, c
    ```
    
    **Security:**
    - All queries automatically scoped to authenticated user
    - Query validation prevents injection attacks
    - Execution timeouts prevent DoS
    - Result size limits prevent memory exhaustion
    
    Args:
        request: GQL query request
        user: Authenticated user (injected)
        kg_storage: KG storage instance (injected)
        db_connection: Database connection (injected)
        
    Returns:
        Query results with metadata
        
    Raises:
        HTTPException: If query execution fails
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Removed excessive logging
        
        # Create query executor
        max_results = request.limit or 1000
        executor = GQLQueryExecutor(
            kg_storage,
            max_results=max_results,
            timeout_seconds=30
        )
        
        # Execute query
        result = await executor.execute(
            request.query,
            user_id,
            format=request.format
        )
        
        if not result["success"]:
            logger.warning(f"Query failed for user {user_id}: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Query executed successfully
        
        return GQLQueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        # Log full error details at ERROR level for 500 responses
        # Use exception() method for AICOLogger to include traceback
        logger.exception(
            f"CRITICAL: Query execution failed with 500 error for user {user_id}",
            extra={
                'user_id': user_id,
                'query': request.query[:200],
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.get("/schema")
async def get_kg_schema(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> dict:
    """
    Get knowledge graph schema for autocomplete.
    
    **Authentication required:** Bearer token
    
    Returns:
        Schema with node labels, relationship types, and properties
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Get all current nodes and edges for this user
        nodes = await uow.kg_nodes.list(filters={"user_id": user_id, "is_current": True}, limit=10000)
        edges = await uow.kg_edges.list(filters={"user_id": user_id, "is_current": True}, limit=10000)
        
        # Extract unique labels and relation types
        node_labels = sorted(list(set(node.label for node in nodes if node.label)))
        relationship_types = sorted(list(set(edge.relation_type for edge in edges if edge.relation_type)))
        
        # Define standard node properties (available on all nodes)
        node_properties = [
            'id', 'label', 'confidence', 'source_text', 
            'created_at', 'updated_at', 'valid_from', 'valid_until',
            'is_current', 'canonical_id', 'language', 'reason'
        ]
        
        # Define standard relationship properties (available on all edges)
        relationship_properties = [
            'id', 'relation_type', 'confidence', 'source_text',
            'created_at', 'updated_at', 'valid_from', 'valid_until',
            'is_current', 'reason'
        ]
        
        return {
            "nodeLabels": node_labels,
            "relationshipTypes": relationship_types,
            "nodeProperties": node_properties,
            "relationshipProperties": relationship_properties
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch KG schema for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schema: {str(e)}"
        )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> GraphStatsResponse:
    """
    Get statistics about the user's knowledge graph.
    
    **Authentication required:** Bearer token
    
    Returns:
        Graph statistics including node/edge counts and type distributions
        
    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Check cache first (30 second TTL)
        now = datetime.utcnow()
        if user_id in _stats_cache:
            cached_response, cached_at = _stats_cache[user_id]
            if now - cached_at < timedelta(seconds=30):
                return cached_response
        
        # Fetching graph stats using repositories
        import json
        
        # Get all nodes and edges for this user
        all_nodes = await uow.kg_nodes.list(filters={"user_id": user_id}, limit=100000)
        all_edges = await uow.kg_edges.list(filters={"user_id": user_id}, limit=100000)
        
        # Basic counts with current/historical breakdown
        node_count = len(all_nodes)
        current_nodes = [n for n in all_nodes if n.is_current]
        current_node_count = len(current_nodes)
        historical_node_count = node_count - current_node_count
        
        edge_count = len(all_edges)
        current_edges = [e for e in all_edges if e.is_current]
        current_edge_count = len(current_edges)
        historical_edge_count = edge_count - current_edge_count
        
        # Node/edge type distributions
        node_types = {}
        for node in all_nodes:
            label = node.label or "unknown"
            node_types[label] = node_types.get(label, 0) + 1
        
        edge_types = {}
        for edge in all_edges:
            rel_type = edge.relation_type or "unknown"
            edge_types[rel_type] = edge_types.get(rel_type, 0) + 1
        
        # Total properties
        total_node_properties = 0
        for node in all_nodes:
            if node.properties:
                if isinstance(node.properties, str):
                    try:
                        props = json.loads(node.properties)
                        total_node_properties += len(props)
                    except:
                        pass
                elif isinstance(node.properties, dict):
                    total_node_properties += len(node.properties)
        
        # Storage size estimation
        node_data_size = sum(
            len(str(node.id or "")) + len(str(node.label or "")) + 
            len(str(node.properties or "")) + len(str(node.source_text or ""))
            for node in all_nodes
        )
        edge_data_size = sum(
            len(str(edge.id or "")) + len(str(edge.relation_type or "")) + 
            len(str(edge.properties or "")) + len(str(edge.source_text or ""))
            for edge in all_edges
        )
        storage_size_mb = (node_data_size + edge_data_size) / (1024 * 1024) * 1.3
        
        # Import metric schemas
        from backend.api.kg.schemas import (
            HealthMetrics, StructureMetrics, TemporalMetrics, 
            CentralityMetrics, ClusteringMetrics, DuplicateNodePair
        )
        
        # Calculate health metrics
        avg_degree = current_edge_count / max(current_node_count, 1)
        isolated_nodes = sum(1 for node in current_nodes if not any(
            e.source_id == node.id or e.target_id == node.id for e in current_edges
        ))
        
        health_metrics = HealthMetrics(
            orphaned_edges=0,  # Would need edge validation
            duplicate_nodes=0,  # Would need similarity analysis
            stale_nodes_count=0,  # Would need timestamp analysis
            stale_nodes_percent=0.0,
            property_completeness=total_node_properties / max(current_node_count, 1),
            nodes_added_24h=0,  # Would need timestamp filtering
            edges_added_24h=0
        )
        
        structure_metrics = StructureMetrics(
            graph_density=current_edge_count / max((current_node_count * (current_node_count - 1)) / 2, 1) if current_node_count > 1 else 0.0,
            average_degree=avg_degree,
            max_degree=0,  # Would need degree calculation
            min_degree=0,
            isolated_nodes=isolated_nodes,
            connected_components=1,  # Would need graph traversal
            largest_component_size=current_node_count
        )
        
        temporal_metrics = TemporalMetrics(
            growth_rate_7d=0.0,  # Would need timestamp analysis
            growth_rate_30d=0.0,
            most_active_day=None,
            activity_by_day={}
        )
        
        centrality_metrics = CentralityMetrics(
            top_by_degree=[],
            top_by_pagerank=[],
            top_by_betweenness=[]
        )
        
        clustering_metrics = ClusteringMetrics(
            global_clustering_coefficient=0.0,
            average_clustering_coefficient=0.0,
            communities_detected=0,
            modularity_score=0.0
        )
        
        response = GraphStatsResponse(
            total_nodes=node_count,
            current_nodes=current_node_count,
            historical_nodes=historical_node_count,
            total_edges=edge_count,
            current_edges=current_edge_count,
            historical_edges=historical_edge_count,
            total_node_properties=total_node_properties,
            node_types=node_types,
            edge_types=edge_types,
            storage_size_mb=round(storage_size_mb, 2),
            user_id=user_id,
            health=health_metrics,
            duplicate_pairs=None,
            structure=structure_metrics,
            temporal=temporal_metrics,
            centrality=centrality_metrics,
            clustering=clustering_metrics
        )
        
        # Cache the response
        _stats_cache[user_id] = (response, now)
        
        # Response prepared
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Failed to get graph stats: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph statistics: {str(e)}"
        )


@router.get("/nodes")
async def list_nodes(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = 100,
    offset: int = 0
):
    """
    List knowledge graph nodes for the authenticated user.
    
    **Authentication required:** Bearer token
    
    Query Parameters:
        - limit: Number of results (default: 100, max: 1000)
        - offset: Pagination offset (default: 0)
    
    Returns:
        List of nodes with all properties
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Clamp limit
        limit = min(limit, 1000)
        
        # Fetch nodes using repository (all nodes, not just current versions)
        nodes_list = await uow.kg_nodes.list(filters={"user_id": user_id}, limit=limit, offset=offset)
        
        # Convert to dict format
        import json
        nodes = []
        for node in nodes_list:
            nodes.append({
                "id": node.id,
                "user_id": node.user_id,
                "label": node.label,
                "properties": json.loads(node.properties) if isinstance(node.properties, str) else (node.properties or {}),
                "confidence": node.confidence,
                "source_text": node.source_text,
                "created_at": node.created_at.isoformat() if hasattr(node.created_at, 'isoformat') else node.created_at,
                "updated_at": node.updated_at.isoformat() if hasattr(node.updated_at, 'isoformat') else node.updated_at,
                "valid_from": node.valid_from.isoformat() if hasattr(node.valid_from, 'isoformat') else node.valid_from,
                "valid_until": node.valid_until.isoformat() if hasattr(node.valid_until, 'isoformat') else node.valid_until,
                "is_current": node.is_current,
                "canonical_id": node.canonical_id,
                "aliases": json.loads(node.aliases_json) if isinstance(node.aliases_json, str) else (node.aliases_json or [])
            })
        
        # Nodes fetched
        return {"nodes": nodes, "total": len(nodes), "limit": limit, "offset": offset}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch nodes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch nodes: {str(e)}"
        )


@router.get("/edges")
async def list_edges(
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = 100,
    offset: int = 0
):
    """
    List knowledge graph edges for the authenticated user.
    
    **Authentication required:** Bearer token
    
    Query Parameters:
        - limit: Number of results (default: 100, max: 1000)
        - offset: Pagination offset (default: 0)
    
    Returns:
        List of edges with all properties
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Clamp limit
        limit = min(limit, 1000)
        
        # Fetch edges using repository (all edges, not just current versions)
        edges_list = await uow.kg_edges.list(filters={"user_id": user_id}, limit=limit, offset=offset)
        
        # Convert to dict format
        import json
        edges = []
        for edge in edges_list:
            edges.append({
                "id": edge.id,
                "user_id": edge.user_id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "properties": json.loads(edge.properties) if isinstance(edge.properties, str) else (edge.properties or {}),
                "confidence": edge.confidence,
                "source_text": edge.source_text,
                "created_at": edge.created_at.isoformat() if hasattr(edge.created_at, 'isoformat') else edge.created_at,
                "updated_at": edge.updated_at.isoformat() if hasattr(edge.updated_at, 'isoformat') else edge.updated_at,
                "valid_from": edge.valid_from.isoformat() if hasattr(edge.valid_from, 'isoformat') else edge.valid_from,
                "valid_until": edge.valid_until.isoformat() if hasattr(edge.valid_until, 'isoformat') else edge.valid_until,
                "is_current": edge.is_current
            })
        
        # Edges fetched
        return {"edges": edges, "total": len(edges), "limit": limit, "offset": offset}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch edges: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch edges: {str(e)}"
        )


@router.get("/query-templates")
async def get_query_templates(
    user: Annotated[dict, Depends(get_current_user)]
):
    """
    Get available GQL query templates.
    
    Templates are loaded from the OS-specific AICO data directory:
    - macOS: ~/Library/Application Support/aico/data/gql_query_templates.json
    - Linux: ~/.local/share/aico/data/gql_query_templates.json
    - Windows: %APPDATA%/aico/data/gql_query_templates.json
    
    **Authentication required:** Bearer token
    """
    try:
        from aico.core.paths import AICOPaths
        
        # Get OS-specific data directory
        data_dir = AICOPaths.get_data_directory() / AICOPaths.get_data_subdirectory_from_config()
        templates_path = data_dir / "gql_query_templates.json"
        
        # Templates should be initialized via CLI: aico config init
        if not templates_path.exists():
            logger.warning(
                f"Query templates not found at {templates_path}. "
                f"Run 'aico config init' to initialize templates from repository defaults."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Query templates not initialized. Run 'aico config init' to set up templates."
            )
        
        with open(templates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Templates loaded
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse query templates JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query templates file is malformed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load query templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load query templates: {str(e)}"
        )


@router.put("/query-templates", tags=["Knowledge Graph"])
async def update_query_templates(
    templates_data: dict,
    user: dict = Depends(get_current_user)
):
    """
    Update GQL query templates (Studio template editor).
    
    Allows users to customize query templates through the Studio UI.
    Templates are persisted to the OS-specific data directory.
    
    **Request Body:**
    ```json
    {
      "templates": [
        {
          "id": "custom-query",
          "title": "My Custom Query",
          "description": "Description",
          "category": "exploration",
          "query": "MATCH (n) RETURN n LIMIT 10",
          "tags": ["custom"]
        }
      ]
    }
    ```
    
    **Authentication required:** Bearer token
    """
    try:
        from aico.core.paths import AICOPaths
        
        # Validate templates structure
        if 'templates' not in templates_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request must contain 'templates' array"
            )
        
        templates = templates_data['templates']
        if not isinstance(templates, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'templates' must be an array"
            )
        
        # Validate each template has required fields
        required_fields = {'id', 'title', 'description', 'category', 'query', 'tags'}
        for idx, template in enumerate(templates):
            if not isinstance(template, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Template at index {idx} must be an object"
                )
            missing_fields = required_fields - set(template.keys())
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Template '{template.get('id', idx)}' missing fields: {missing_fields}"
                )
        
        # Get target path
        data_dir = AICOPaths.get_data_directory() / AICOPaths.get_data_subdirectory_from_config()
        data_dir.mkdir(parents=True, exist_ok=True)
        templates_path = data_dir / "gql_query_templates.json"
        
        # Write templates
        with open(templates_path, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, indent=2, ensure_ascii=False)
        
        # Templates updated
        
        return {
            "success": True,
            "message": f"Updated {len(templates)} query templates",
            "templates_count": len(templates),
            "path": str(templates_path)
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to encode templates JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON structure in templates"
        )
    except Exception as e:
        logger.error(f"Failed to update query templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update query templates: {str(e)}"
        )
