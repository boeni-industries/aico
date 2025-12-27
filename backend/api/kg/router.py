"""
Knowledge Graph API Router.

Provides REST endpoints for querying and managing the knowledge graph.
"""

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
        logger.error(f"Unexpected error executing query: {e}", exc_info=True)
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
        
        logger.info(f"Fetching graph stats for user {user_id}")
        
        # Get node count
        node_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_nodes WHERE user_id = ? AND is_current = 1",
            [user_id]
        ).fetchone()[0]
        
        # Get edge count
        edge_count = db_connection.execute(
            "SELECT COUNT(*) FROM kg_edges WHERE user_id = ? AND is_current = 1",
            [user_id]
        ).fetchone()[0]
        
        # Get node type distribution
        node_types_raw = db_connection.execute(
            "SELECT label, COUNT(*) FROM kg_nodes WHERE user_id = ? AND is_current = 1 GROUP BY label",
            [user_id]
        ).fetchall()
        node_types = {row[0]: row[1] for row in node_types_raw}
        
        # Get edge type distribution
        edge_types_raw = db_connection.execute(
            "SELECT relation_type, COUNT(*) FROM kg_edges WHERE user_id = ? AND is_current = 1 GROUP BY relation_type",
            [user_id]
        ).fetchall()
        edge_types = {row[0]: row[1] for row in edge_types_raw}
        
        return GraphStatsResponse(
            total_nodes=node_count,
            total_edges=edge_count,
            node_types=node_types,
            edge_types=edge_types,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}", exc_info=True)
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
        
        # Fetch nodes
        nodes_raw = db_connection.execute(
            """
            SELECT id, user_id, label, properties, confidence, source_text,
                   created_at, updated_at, valid_from, valid_until, is_current,
                   canonical_id, aliases_json
            FROM kg_nodes 
            WHERE user_id = ? AND is_current = 1
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
        
        # Fetch edges
        edges_raw = db_connection.execute(
            """
            SELECT id, user_id, source_id, target_id, relation_type, properties,
                   confidence, source_text, created_at, updated_at,
                   valid_from, valid_until, is_current
            FROM kg_edges 
            WHERE user_id = ? AND is_current = 1
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
