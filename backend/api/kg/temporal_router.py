"""
Temporal Knowledge Graph API endpoints.

Provides endpoints for querying historical graph states, version history,
changes over time, and graph comparisons.
"""

from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
import json

from aico.core.logging import get_logger
from backend.api.kg.schemas import (
    NodeVersion,
    NodeHistoryResponse,
    ChangeRecord,
    ChangesResponse,
    TemporalGraphRequest,
    TemporalGraphResponse,
    GraphComparisonRequest,
    GraphComparisonResponse,
    GraphDiff
)
from backend.api.kg.dependencies import (
    get_current_user,
    get_db_connection
)

router = APIRouter()
logger = get_logger("backend.api.kg.temporal")


@router.get("/nodes/{node_id}/history", response_model=NodeHistoryResponse)
async def get_node_history(
    node_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> NodeHistoryResponse:
    """
    Get complete version history for a node.
    
    **Authentication required:** Bearer token
    
    Returns all versions of a node (by canonical_id), ordered newest to oldest.
    Shows how the node evolved over time with property changes.
    
    Args:
        node_id: The ID of the node to fetch history for
        user: Current authenticated user (injected)
        db_connection: Database connection (injected)
    
    Returns:
        NodeHistoryResponse with all versions of the node
        
    Raises:
        HTTPException: 404 if node not found, 401 if unauthorized, 500 on error
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        logger.info(f"[TEMPORAL] Fetching version history for node {node_id}, user {user_id}")
        
        # First, get the canonical_id for this node
        logger.debug(f"[TEMPORAL] Querying canonical_id for node {node_id}")
        node_row = db_connection.execute(
            """
            SELECT canonical_id FROM kg_nodes 
            WHERE id = ? AND user_id = ?
            """,
            [node_id, user_id]
        ).fetchone()
        
        if not node_row:
            logger.warning(f"[TEMPORAL] Node {node_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node {node_id} not found"
            )
        
        canonical_id = node_row[0] or node_id
        logger.info(f"[TEMPORAL] Found canonical_id: {canonical_id} for node {node_id}")
        
        # Fetch all versions with this canonical_id
        logger.debug(f"[TEMPORAL] Fetching all versions for canonical_id {canonical_id}")
        versions_raw = db_connection.execute(
            """
            SELECT id, user_id, label, properties, confidence, source_text,
                   created_at, updated_at, valid_from, valid_until, is_current,
                   canonical_id, aliases_json, reason
            FROM kg_nodes 
            WHERE (canonical_id = ? OR id = ?) AND user_id = ?
            ORDER BY created_at DESC
            """,
            [canonical_id, canonical_id, user_id]
        ).fetchall()
        logger.debug(f"[TEMPORAL] Query returned {len(versions_raw)} raw rows")
        
        versions = []
        for idx, row in enumerate(versions_raw):
            try:
                version = NodeVersion(
                    id=row[0],
                    user_id=row[1],
                    label=row[2],
                    properties=json.loads(row[3]) if row[3] else {},
                    confidence=row[4],
                    source_text=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    valid_from=row[8],
                    valid_until=row[9],
                    is_current=row[10],
                    canonical_id=row[11],
                    aliases=json.loads(row[12]) if row[12] else [],
                    reason=row[13]
                )
                versions.append(version)
                logger.debug(f"[TEMPORAL] Version {idx+1}: id={row[0]}, is_current={row[10]}, valid_from={row[8]}, reason={row[13]}")
            except Exception as e:
                logger.error(f"[TEMPORAL] Failed to parse version {idx+1}: {e}")
                logger.error(f"[TEMPORAL] Row data: {row}")
                raise
        
        logger.info(f"[TEMPORAL] ✅ Successfully built {len(versions)} versions for canonical_id {canonical_id}")
        
        return NodeHistoryResponse(
            canonical_id=canonical_id,
            total_versions=len(versions),
            versions=versions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEMPORAL] ❌ Failed to fetch node history: {e}")
        logger.error(f"[TEMPORAL] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"[TEMPORAL] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch node history: {str(e)}"
        )


@router.get("/changes", response_model=ChangesResponse)
async def get_changes(
    from_timestamp: str = Query(..., description="Start timestamp (ISO 8601)"),
    to_timestamp: str = Query(..., description="End timestamp (ISO 8601)"),
    user: Annotated[dict, Depends(get_current_user)] = None,
    db_connection: Annotated[object, Depends(get_db_connection)] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> ChangesResponse:
    """
    Get all changes (creates, updates, deletes) in a time range.
    
    **Authentication required:** Bearer token
    
    Returns a feed of all changes to nodes and edges between two timestamps.
    Useful for building activity feeds and change logs.
    
    Args:
        from_timestamp: Start of time range (ISO 8601)
        to_timestamp: End of time range (ISO 8601)
        limit: Maximum number of changes to return
        user: Current authenticated user (injected)
        db_connection: Database connection (injected)
    
    Returns:
        ChangesResponse with list of changes in time range
        
    Raises:
        HTTPException: 401 if unauthorized, 500 on error
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        logger.info(f"Fetching changes from {from_timestamp} to {to_timestamp} for user {user_id}")
        
        changes = []
        
        # Get node changes (created or updated in time range)
        nodes_changed = db_connection.execute(
            """
            SELECT id, label, properties, created_at, updated_at, 
                   valid_from, valid_until, is_current, source_text
            FROM kg_nodes
            WHERE user_id = ? 
              AND (created_at BETWEEN ? AND ? OR updated_at BETWEEN ? AND ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            [user_id, from_timestamp, to_timestamp, from_timestamp, to_timestamp, limit]
        ).fetchall()
        
        for row in nodes_changed:
            node_id, label, props_json, created_at, updated_at, valid_from, valid_until, is_current, source_text = row
            properties = json.loads(props_json) if props_json else {}
            
            # Determine change type
            if created_at >= from_timestamp and created_at <= to_timestamp:
                change_type = "node_created"
            elif valid_until and valid_until >= from_timestamp and valid_until <= to_timestamp:
                change_type = "node_deleted"
            else:
                change_type = "node_updated"
            
            changes.append(ChangeRecord(
                change_type=change_type,
                entity_type="node",
                entity_id=node_id,
                entity_label=label,
                timestamp=updated_at,
                properties_changed=list(properties.keys()) if change_type == "node_updated" else None,
                old_values=None,  # Would need to query previous version
                new_values=properties if change_type != "node_deleted" else None,
                source_text=source_text,
                reason=None  # Would need to be stored in database
            ))
        
        # Get edge changes
        edges_changed = db_connection.execute(
            """
            SELECT id, source_id, target_id, relation_type, properties, 
                   created_at, updated_at, valid_from, valid_until, is_current, source_text
            FROM kg_edges
            WHERE user_id = ? 
              AND (created_at BETWEEN ? AND ? OR updated_at BETWEEN ? AND ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            [user_id, from_timestamp, to_timestamp, from_timestamp, to_timestamp, limit]
        ).fetchall()
        
        for row in edges_changed:
            edge_id, source_id, target_id, relation_type, props_json, created_at, updated_at, valid_from, valid_until, is_current, source_text = row
            properties = json.loads(props_json) if props_json else {}
            
            if created_at >= from_timestamp and created_at <= to_timestamp:
                change_type = "edge_created"
            elif valid_until and valid_until >= from_timestamp and valid_until <= to_timestamp:
                change_type = "edge_deleted"
            else:
                change_type = "edge_updated"
            
            changes.append(ChangeRecord(
                change_type=change_type,
                entity_type="edge",
                entity_id=edge_id,
                entity_label=relation_type,
                timestamp=updated_at,
                properties_changed=list(properties.keys()) if change_type == "edge_updated" else None,
                old_values=None,
                new_values=properties if change_type != "edge_deleted" else None,
                source_text=source_text,
                reason=None
            ))
        
        # Sort all changes by timestamp
        changes.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"Found {len(changes)} changes in time range")
        
        return ChangesResponse(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            total_changes=len(changes),
            changes=changes[:limit]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch changes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch changes: {str(e)}"
        )


@router.post("/temporal", response_model=TemporalGraphResponse)
async def get_temporal_graph_state(
    request: TemporalGraphRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> TemporalGraphResponse:
    """
    Get the state of the knowledge graph at a specific point in time.
    
    **Authentication required:** Bearer token
    
    Returns all nodes and edges that were current at the given timestamp,
    based on their valid_from and valid_until periods. Enables "time travel"
    queries to see what the graph looked like at any point in history.
    
    Args:
        request: TemporalGraphRequest with as_of timestamp and options
        user: Current authenticated user (injected)
        db_connection: Database connection (injected)
    
    Returns:
        TemporalGraphResponse with nodes and edges at specified time
        
    Raises:
        HTTPException: 401 if unauthorized, 500 on error
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        as_of = request.as_of
        logger.info(f"Fetching graph state as of {as_of} for user {user_id}")
        
        # Get nodes that were current at the specified time
        # A node is current at time T if:
        # - (valid_from IS NULL OR valid_from <= T) - node existed at time T
        # - AND (valid_until IS NULL OR valid_until > T) - node wasn't deleted yet
        # Nodes without valid_from are treated as "always existed" (legacy nodes)
        nodes_raw = db_connection.execute(
            """
            SELECT id, user_id, label, properties, confidence, source_text,
                   created_at, updated_at, valid_from, valid_until, is_current,
                   canonical_id, aliases_json, reason
            FROM kg_nodes 
            WHERE user_id = ? 
              AND (valid_from IS NULL OR valid_from <= ?)
              AND (valid_until IS NULL OR valid_until > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [user_id, as_of, as_of, request.node_limit or 10000]
        ).fetchall()
        
        nodes = []
        for row in nodes_raw:
            nodes.append(NodeVersion(
                id=row[0],
                user_id=row[1],
                label=row[2],
                properties=json.loads(row[3]) if row[3] else {},
                confidence=row[4],
                source_text=row[5],
                created_at=row[6],
                updated_at=row[7],
                valid_from=row[8],
                valid_until=row[9],
                is_current=row[10],
                canonical_id=row[11],
                aliases=json.loads(row[12]) if row[12] else [],
                reason=row[13]
            ))
        
        edges = []
        if request.include_edges:
            # Same logic for edges - include edges without valid_from (legacy edges)
            edges_raw = db_connection.execute(
                """
                SELECT id, source_id, target_id, relation_type, properties,
                       confidence, source_text, created_at, updated_at,
                       valid_from, valid_until, is_current
                FROM kg_edges 
                WHERE user_id = ? 
                  AND (valid_from IS NULL OR valid_from <= ?)
                  AND (valid_until IS NULL OR valid_until > ?)
                ORDER BY created_at DESC
                """,
                [user_id, as_of, as_of]
            ).fetchall()
            
            logger.info(f"[TEMPORAL_DEBUG] Queried edges at {as_of}: found {len(edges_raw)} raw edges")
            
            for row in edges_raw:
                edge_data = {
                    "id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "relation_type": row[3],
                    "properties": json.loads(row[4]) if row[4] else {},
                    "confidence": row[5],
                    "source_text": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "valid_from": row[9],
                    "valid_until": row[10],
                    "is_current": row[11]
                }
                edges.append(edge_data)
            
            if len(edges_raw) > 0:
                logger.info(f"[TEMPORAL_DEBUG] Sample edge: {edges[0]['id']}, valid_from={edges[0]['valid_from']}, valid_until={edges[0]['valid_until']}")
        
        logger.info(f"Found {len(nodes)} nodes and {len(edges)} edges at {as_of}")
        
        return TemporalGraphResponse(
            as_of=as_of,
            total_nodes=len(nodes),
            total_edges=len(edges),
            nodes=nodes,
            edges=edges
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch temporal graph state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch temporal graph state: {str(e)}"
        )


@router.post("/compare", response_model=GraphComparisonResponse)
async def compare_graph_states(
    request: GraphComparisonRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db_connection: Annotated[object, Depends(get_db_connection)]
) -> GraphComparisonResponse:
    """
    Compare the knowledge graph state between two timestamps.
    
    **Authentication required:** Bearer token
    
    Returns a diff showing what changed between two points in time,
    including added, removed, and modified nodes and edges. Useful for
    understanding graph evolution and tracking significant changes.
    
    Args:
        request: GraphComparisonRequest with from/to timestamps
        user: Current authenticated user (injected)
        db_connection: Database connection (injected)
    
    Returns:
        GraphComparisonResponse with detailed diff and statistics
        
    Raises:
        HTTPException: 401 if unauthorized, 500 on error
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        from_ts = request.from_timestamp
        to_ts = request.to_timestamp
        logger.info(f"Comparing graph states from {from_ts} to {to_ts} for user {user_id}")
        
        # Get nodes at from_timestamp
        nodes_from = set()
        nodes_from_raw = db_connection.execute(
            """
            SELECT id FROM kg_nodes 
            WHERE user_id = ? 
              AND valid_from <= ?
              AND (valid_until IS NULL OR valid_until > ?)
            """,
            [user_id, from_ts, from_ts]
        ).fetchall()
        nodes_from = {row[0] for row in nodes_from_raw}
        
        # Get nodes at to_timestamp
        nodes_to = set()
        nodes_to_raw = db_connection.execute(
            """
            SELECT id FROM kg_nodes 
            WHERE user_id = ? 
              AND valid_from <= ?
              AND (valid_until IS NULL OR valid_until > ?)
            """,
            [user_id, to_ts, to_ts]
        ).fetchall()
        nodes_to = {row[0] for row in nodes_to_raw}
        
        # Calculate differences
        added_nodes = nodes_to - nodes_from
        removed_nodes = nodes_from - nodes_to
        
        # Get modified nodes (nodes that exist in both but have different updated_at)
        common_nodes = nodes_from & nodes_to
        modified_nodes = []
        for node_id in common_nodes:
            # Check if node was updated between timestamps
            update_check = db_connection.execute(
                """
                SELECT COUNT(*) FROM kg_nodes
                WHERE id = ? AND user_id = ?
                  AND updated_at > ? AND updated_at <= ?
                """,
                [node_id, user_id, from_ts, to_ts]
            ).fetchone()
            if update_check[0] > 0:
                modified_nodes.append(node_id)
        
        # Same for edges
        edges_from = set()
        edges_from_raw = db_connection.execute(
            """
            SELECT id FROM kg_edges 
            WHERE user_id = ? 
              AND valid_from <= ?
              AND (valid_until IS NULL OR valid_until > ?)
            """,
            [user_id, from_ts, from_ts]
        ).fetchall()
        edges_from = {row[0] for row in edges_from_raw}
        
        edges_to = set()
        edges_to_raw = db_connection.execute(
            """
            SELECT id FROM kg_edges 
            WHERE user_id = ? 
              AND valid_from <= ?
              AND (valid_until IS NULL OR valid_until > ?)
            """,
            [user_id, to_ts, to_ts]
        ).fetchall()
        edges_to = {row[0] for row in edges_to_raw}
        
        added_edges = edges_to - edges_from
        removed_edges = edges_from - edges_to
        
        common_edges = edges_from & edges_to
        modified_edges = []
        for edge_id in common_edges:
            update_check = db_connection.execute(
                """
                SELECT COUNT(*) FROM kg_edges
                WHERE id = ? AND user_id = ?
                  AND updated_at > ? AND updated_at <= ?
                """,
                [edge_id, user_id, from_ts, to_ts]
            ).fetchone()
            if update_check[0] > 0:
                modified_edges.append(edge_id)
        
        diff = GraphDiff(
            nodes_added=len(added_nodes),
            nodes_removed=len(removed_nodes),
            nodes_modified=len(modified_nodes),
            edges_added=len(added_edges),
            edges_removed=len(removed_edges),
            edges_modified=len(modified_edges),
            added_node_ids=list(added_nodes),
            removed_node_ids=list(removed_nodes),
            modified_node_ids=modified_nodes
        )
        
        from_state = {
            "total_nodes": len(nodes_from),
            "total_edges": len(edges_from)
        }
        
        to_state = {
            "total_nodes": len(nodes_to),
            "total_edges": len(edges_to)
        }
        
        logger.info(f"Comparison complete: +{diff.nodes_added} nodes, -{diff.nodes_removed} nodes, ~{diff.nodes_modified} modified")
        
        return GraphComparisonResponse(
            from_timestamp=from_ts,
            to_timestamp=to_ts,
            diff=diff,
            from_state=from_state,
            to_state=to_state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare graph states: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare graph states: {str(e)}"
        )
