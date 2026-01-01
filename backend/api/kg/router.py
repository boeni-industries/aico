"""
Knowledge Graph API Router.

Provides REST endpoints for querying and managing the knowledge graph.
"""

import json
from pathlib import Path
from typing import Annotated
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
    get_kg_storage,
    get_db_connection
)

# Initialize router and logger
router = APIRouter()
logger = get_logger("backend", "api.kg")

# Include temporal endpoints
from backend.api.kg.temporal_router import router as temporal_router
router.include_router(temporal_router, tags=["temporal"])


@router.post("/query", response_model=GQLQueryResponse)
async def execute_gql_query(
    request: GQLQueryRequest,
    user: Annotated[dict, Depends(get_current_user)],
    kg_storage: Annotated[object, Depends(get_kg_storage)],
    db_connection: Annotated[object, Depends(get_db_connection)]
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
        
        logger.info(f"Executing GQL query for user {user_id}: {request.query[:100]}...")
        
        # Create query executor
        max_results = request.limit or 1000
        executor = GQLQueryExecutor(
            kg_storage,
            db_connection,
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
        
        logger.info(f"Query executed successfully: {result['metadata'].get('row_count', 0)} rows")
        
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


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
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
        
        logger.info(f"Fetching comprehensive graph stats for user {user_id}")
        
        # Import analytics engine
        from backend.api.kg.analytics import KGAnalyticsEngine
        import json
        
        # Initialize analytics engine
        analytics = KGAnalyticsEngine(db_connection, user_id)
        
        # Basic counts with current/historical breakdown
        node_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_nodes WHERE user_id = ?",
            [user_id]
        ).fetchone()[0]
        
        current_node_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_nodes WHERE user_id = ? AND is_current = 1",
            [user_id]
        ).fetchone()[0]
        
        historical_node_count = node_count - current_node_count
        
        edge_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_edges WHERE user_id = ?",
            [user_id]
        ).fetchone()[0]
        
        current_edge_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_edges WHERE user_id = ? AND is_current = 1",
            [user_id]
        ).fetchone()[0]
        
        historical_edge_count = edge_count - current_edge_count
        
        # Node/edge type distributions
        node_types_raw = db_connection.execute(
            "SELECT label, COUNT(*) FROM kg_nodes WHERE user_id = ? GROUP BY label",
            [user_id]
        ).fetchall()
        node_types = {row[0]: row[1] for row in node_types_raw}
        
        edge_types_raw = db_connection.execute(
            "SELECT relation_type, COUNT(*) FROM kg_edges WHERE user_id = ? GROUP BY relation_type",
            [user_id]
        ).fetchall()
        edge_types = {row[0]: row[1] for row in edge_types_raw}
        
        # Total properties
        nodes_with_props = db_connection.execute(
            "SELECT properties FROM kg_nodes WHERE user_id = ?",
            [user_id]
        ).fetchall()
        total_node_properties = sum(
            len(json.loads(row[0])) if row[0] else 0 
            for row in nodes_with_props
        )
        
        # Storage size
        all_nodes = db_connection.execute(
            "SELECT * FROM kg_nodes WHERE user_id = ?",
            [user_id]
        ).fetchall()
        all_edges = db_connection.execute(
            "SELECT * FROM kg_edges WHERE user_id = ?",
            [user_id]
        ).fetchall()
        
        node_data_size = sum(
            sum(len(str(field)) if field else 0 for field in row)
            for row in all_nodes
        )
        edge_data_size = sum(
            sum(len(str(field)) if field else 0 for field in row)
            for row in all_edges
        )
        storage_size_mb = (node_data_size + edge_data_size) / (1024 * 1024) * 1.3
        
        # Calculate comprehensive metrics using analytics engine
        logger.info("Calculating health metrics...")
        health_metrics = analytics.calculate_health_metrics()
        
        logger.info("Calculating structure metrics...")
        structure_metrics = analytics.calculate_structure_metrics()
        
        logger.info("Calculating temporal metrics...")
        temporal_metrics = analytics.calculate_temporal_metrics()
        
        logger.info("Calculating centrality metrics...")
        centrality_metrics = analytics.calculate_centrality_metrics()
        logger.info(f"Centrality metrics calculated: {centrality_metrics}")
        logger.info(f"Top by degree count: {len(centrality_metrics.get('top_by_degree', []))}")
        logger.info(f"Top by pagerank count: {len(centrality_metrics.get('top_by_pagerank', []))}")
        logger.info(f"Top by betweenness count: {len(centrality_metrics.get('top_by_betweenness', []))}")
        
        logger.info("Calculating clustering metrics...")
        clustering_metrics = analytics.calculate_clustering_metrics()
        
        # Detect actual duplicate pairs
        logger.info("Detecting duplicate node pairs...")
        duplicate_pairs = analytics.detect_duplicate_pairs()
        logger.info(f"Found {len(duplicate_pairs)} duplicate pairs")
        
        # Convert to schema format
        from backend.api.kg.schemas import DuplicateNodePair
        duplicate_pair_objects = [
            DuplicateNodePair(
                id1=pair['id1'],
                name1=pair['name1'],
                label1=pair['label1'],
                id2=pair['id2'],
                name2=pair['name2'],
                label2=pair['label2'],
                similarity=pair['similarity']
            )
            for pair in duplicate_pairs
        ]
        
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
            duplicate_pairs=duplicate_pair_objects if duplicate_pair_objects else None,
            structure=structure_metrics,
            temporal=temporal_metrics,
            centrality=centrality_metrics,
            clustering=clustering_metrics
        )
        logger.info(f"Response centrality data: {response.centrality}")
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
    db_connection: Annotated[object, Depends(get_db_connection)],
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
        
        logger.info(f"Fetching nodes for user {user_id} (limit={limit}, offset={offset})")
        
        # Fetch nodes (all nodes, not just current versions)
        nodes_raw = db_connection.execute(
            """
            SELECT id, user_id, label, properties, confidence, source_text,
                   created_at, updated_at, valid_from, valid_until, is_current,
                   canonical_id, aliases_json
            FROM kg_nodes 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [user_id, limit, offset]
        ).fetchall()
        
        # Convert to dict format
        import json
        nodes = []
        for row in nodes_raw:
            nodes.append({
                "id": row[0],
                "user_id": row[1],
                "label": row[2],
                "properties": json.loads(row[3]) if row[3] else {},
                "confidence": row[4],
                "source_text": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "valid_from": row[8],
                "valid_until": row[9],
                "is_current": row[10],
                "canonical_id": row[11],
                "aliases": json.loads(row[12]) if row[12] else []
            })
        
        logger.info(f"Returning {len(nodes)} nodes")
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
    db_connection: Annotated[object, Depends(get_db_connection)],
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
        
        logger.info(f"Fetching edges for user {user_id} (limit={limit}, offset={offset})")
        
        # Fetch edges (all edges, not just current versions)
        edges_raw = db_connection.execute(
            """
            SELECT id, user_id, source_id, target_id, relation_type, properties,
                   confidence, source_text, created_at, updated_at,
                   valid_from, valid_until, is_current
            FROM kg_edges 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [user_id, limit, offset]
        ).fetchall()
        
        # Convert to dict format
        import json
        edges = []
        for row in edges_raw:
            edges.append({
                "id": row[0],
                "user_id": row[1],
                "source_id": row[2],
                "target_id": row[3],
                "relation_type": row[4],
                "properties": json.loads(row[5]) if row[5] else {},
                "confidence": row[6],
                "source_text": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "valid_from": row[10],
                "valid_until": row[11],
                "is_current": row[12]
            })
        
        logger.info(f"Returning {len(edges)} edges")
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
        
        # Get OS-specific data directory and ensure it exists
        data_dir = AICOPaths.get_data_directory() / AICOPaths.get_data_subdirectory_from_config()
        data_dir.mkdir(parents=True, exist_ok=True)
        
        templates_path = data_dir / "gql_query_templates.json"
        
        if not templates_path.exists():
            logger.warning(f"Query templates file not found at {templates_path}")
            return {"templates": []}
        
        with open(templates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data.get('templates', []))} query templates from {templates_path} for user {user.get('user_uuid')}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse query templates JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query templates file is malformed"
        )
    except Exception as e:
        logger.error(f"Failed to load query templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load query templates: {str(e)}"
        )
