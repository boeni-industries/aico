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
from backend.api.kg.dependencies import get_current_user
from backend.core.postgres_dependencies import get_uow

router = APIRouter()
logger = get_logger("backend.api.kg.temporal")


@router.get("/nodes/{node_id}/history", response_model=NodeHistoryResponse)
async def get_node_history(
    node_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    uow: Annotated[object, Depends(get_uow)]
) -> NodeHistoryResponse:
    """
    Get complete version history for a node.
    
    **Authentication required:** Bearer token
    
    Returns all versions of a node (by canonical_id), ordered newest to oldest.
    Shows how the node evolved over time with property changes.
    
    Args:
        node_id: The ID of the node to fetch history for
        user: Current authenticated user (injected)
        uow: Unit of Work (injected)
    
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
        node = await uow.kg_nodes.get_by_id(node_id)
        
        if not node or node.user_id != user_id:
            logger.warning(f"[TEMPORAL] Node {node_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node {node_id} not found"
            )
        
        canonical_id = node.canonical_id or node_id
        logger.info(f"[TEMPORAL] Found canonical_id: {canonical_id} for node {node_id}")
        
        # Fetch all versions with this canonical_id
        logger.debug(f"[TEMPORAL] Fetching all versions for canonical_id {canonical_id}")
        all_versions = await uow.kg_nodes.list(
            filters={'user_id': user_id},
            limit=10000
        )
        
        # Filter for matching canonical_id or id
        versions_filtered = [
            n for n in all_versions 
            if n.canonical_id == canonical_id or n.id == canonical_id
        ]
        
        # Sort by created_at descending
        versions_filtered.sort(key=lambda n: n.created_at or '', reverse=True)
        
        logger.debug(f"[TEMPORAL] Query returned {len(versions_filtered)} versions")
        
        versions = []
        for idx, node_ver in enumerate(versions_filtered):
            try:
                version = NodeVersion(
                    id=node_ver.id,
                    user_id=node_ver.user_id,
                    label=node_ver.label,
                    properties=json.loads(node_ver.properties) if isinstance(node_ver.properties, str) else (node_ver.properties or {}),
                    confidence=node_ver.confidence,
                    source_text=node_ver.source_text,
                    created_at=node_ver.created_at,
                    updated_at=node_ver.updated_at,
                    valid_from=node_ver.valid_from,
                    valid_until=node_ver.valid_until,
                    is_current=bool(node_ver.is_current),
                    canonical_id=node_ver.canonical_id,
                    aliases=json.loads(node_ver.aliases_json) if node_ver.aliases_json else [],
                    reason=node_ver.reason
                )
                versions.append(version)
                logger.debug(f"[TEMPORAL] Version {idx+1}: id={node_ver.id}, is_current={node_ver.is_current}, valid_from={node_ver.valid_from}, reason={node_ver.reason}")
            except Exception as e:
                logger.error(f"[TEMPORAL] Failed to parse version {idx+1}: {e}")
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
    uow: Annotated[object, Depends(get_uow)] = None,
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
        
        # Get all nodes for user and filter in memory
        all_nodes = await uow.kg_nodes.list(
            filters={'user_id': user_id},
            limit=100000
        )
        
        nodes_changed = [
            n for n in all_nodes
            if (n.created_at and from_timestamp <= n.created_at <= to_timestamp) or
               (n.updated_at and from_timestamp <= n.updated_at <= to_timestamp)
        ]
        
        # Sort by updated_at descending and limit
        nodes_changed.sort(key=lambda n: n.updated_at or n.created_at or '', reverse=True)
        nodes_changed = nodes_changed[:limit]
        
        for node in nodes_changed:
            # Convert JSONB to plain dict
            properties = node.properties
            if properties is None:
                properties = {}
            elif isinstance(properties, dict):
                # Already a dict, use as-is
                properties = dict(properties)
            else:
                # Fallback: try to parse as JSON string
                try:
                    properties = json.loads(str(properties))
                    if not isinstance(properties, dict):
                        properties = {}
                except (json.JSONDecodeError, TypeError, ValueError):
                    properties = {}
            
            # Determine change type
            if node.created_at and from_timestamp <= node.created_at <= to_timestamp:
                change_type = "node_created"
            elif node.valid_until and from_timestamp <= node.valid_until <= to_timestamp:
                change_type = "node_deleted"
            else:
                change_type = "node_updated"
            
            changes.append(ChangeRecord(
                change_type=change_type,
                entity_type="node",
                entity_id=node.id,
                entity_label=node.label,
                timestamp=node.updated_at,
                properties_changed=list(properties.keys()) if change_type == "node_updated" else None,
                old_values=None,
                new_values=properties if change_type != "node_deleted" else None,
                source_text=node.source_text,
                reason=None
            ))
        
        # Get edge changes
        all_edges = await uow.kg_edges.list(
            filters={'user_id': user_id},
            limit=100000
        )
        
        edges_changed = [
            e for e in all_edges
            if (e.created_at and from_timestamp <= e.created_at <= to_timestamp) or
               (e.updated_at and from_timestamp <= e.updated_at <= to_timestamp)
        ]
        
        edges_changed.sort(key=lambda e: e.updated_at or e.created_at or '', reverse=True)
        edges_changed = edges_changed[:limit]
        
        for edge in edges_changed:
            # Convert JSONB to plain dict
            properties = edge.properties
            if properties is None:
                properties = {}
            elif isinstance(properties, dict):
                # Already a dict, use as-is
                properties = dict(properties)
            else:
                # Fallback: try to parse as JSON string
                try:
                    properties = json.loads(str(properties))
                    if not isinstance(properties, dict):
                        properties = {}
                except (json.JSONDecodeError, TypeError, ValueError):
                    properties = {}
            
            if edge.created_at and from_timestamp <= edge.created_at <= to_timestamp:
                change_type = "edge_created"
            elif edge.valid_until and from_timestamp <= edge.valid_until <= to_timestamp:
                change_type = "edge_deleted"
            else:
                change_type = "edge_updated"
            
            changes.append(ChangeRecord(
                change_type=change_type,
                entity_type="edge",
                entity_id=edge.id,
                entity_label=edge.relation_type,
                timestamp=edge.updated_at,
                properties_changed=list(properties.keys()) if change_type == "edge_updated" else None,
                old_values=None,
                new_values=properties if change_type != "edge_deleted" else None,
                source_text=edge.source_text,
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
    uow: Annotated[object, Depends(get_uow)]
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
        uow: Unit of Work (injected)
    
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
        
        # Get all nodes for user and filter in memory
        all_nodes = await uow.kg_nodes.list(
            filters={'user_id': user_id},
            limit=request.node_limit or 10000
        )
        
        # Filter nodes that were current at the specified time
        nodes_filtered = [
            n for n in all_nodes
            if (not n.valid_from or n.valid_from <= as_of) and
               (not n.valid_until or n.valid_until > as_of)
        ]
        
        # Sort by created_at descending
        nodes_filtered.sort(key=lambda n: n.created_at or '', reverse=True)
        
        nodes = []
        for node in nodes_filtered:
            nodes.append(NodeVersion(
                id=node.id,
                user_id=node.user_id,
                label=node.label,
                properties=json.loads(node.properties) if isinstance(node.properties, str) else (node.properties or {}),
                confidence=node.confidence,
                source_text=node.source_text,
                created_at=node.created_at,
                updated_at=node.updated_at,
                valid_from=node.valid_from,
                valid_until=node.valid_until,
                is_current=bool(node.is_current),
                canonical_id=node.canonical_id,
                aliases=json.loads(node.aliases_json) if node.aliases_json else [],
                reason=node.reason
            ))
        
        edges = []
        if request.include_edges:
            all_edges = await uow.kg_edges.list(
                filters={'user_id': user_id},
                limit=100000
            )
            
            edges_filtered = [
                e for e in all_edges
                if (not e.valid_from or e.valid_from <= as_of) and
                   (not e.valid_until or e.valid_until > as_of)
            ]
            
            edges_filtered.sort(key=lambda e: e.created_at or '', reverse=True)
            
            logger.info(f"[TEMPORAL_DEBUG] Queried edges at {as_of}: found {len(edges_filtered)} edges")
            
            for edge in edges_filtered:
                edge_data = {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation_type": edge.relation_type,
                    "properties": json.loads(edge.properties) if isinstance(edge.properties, str) else (edge.properties or {}),
                    "confidence": edge.confidence,
                    "source_text": edge.source_text,
                    "created_at": edge.created_at,
                    "updated_at": edge.updated_at,
                    "valid_from": edge.valid_from,
                    "valid_until": edge.valid_until,
                    "is_current": bool(edge.is_current)
                }
                edges.append(edge_data)
            
            if len(edges_filtered) > 0:
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
    uow: Annotated[object, Depends(get_uow)]
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
        uow: Unit of Work (injected)
    
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
        
        # Get all nodes for user
        all_nodes = await uow.kg_nodes.list(
            filters={'user_id': user_id},
            limit=100000
        )
        
        # Filter nodes at from_timestamp
        nodes_from = {
            n.id for n in all_nodes
            if (not n.valid_from or n.valid_from <= from_ts) and
               (not n.valid_until or n.valid_until > from_ts)
        }
        
        # Filter nodes at to_timestamp
        nodes_to = {
            n.id for n in all_nodes
            if (not n.valid_from or n.valid_from <= to_ts) and
               (not n.valid_until or n.valid_until > to_ts)
        }
        
        # Calculate differences
        added_nodes = nodes_to - nodes_from
        removed_nodes = nodes_from - nodes_to
        
        # Get modified nodes (nodes that exist in both but were updated between timestamps)
        common_nodes = nodes_from & nodes_to
        modified_nodes = [
            n.id for n in all_nodes
            if n.id in common_nodes and n.updated_at and from_ts < n.updated_at <= to_ts
        ]
        
        # Same for edges
        all_edges = await uow.kg_edges.list(
            filters={'user_id': user_id},
            limit=100000
        )
        
        edges_from = {
            e.id for e in all_edges
            if (not e.valid_from or e.valid_from <= from_ts) and
               (not e.valid_until or e.valid_until > from_ts)
        }
        
        edges_to = {
            e.id for e in all_edges
            if (not e.valid_from or e.valid_from <= to_ts) and
               (not e.valid_until or e.valid_until > to_ts)
        }
        
        added_edges = edges_to - edges_from
        removed_edges = edges_from - edges_to
        
        common_edges = edges_from & edges_to
        modified_edges = [
            e.id for e in all_edges
            if e.id in common_edges and e.updated_at and from_ts < e.updated_at <= to_ts
        ]
        
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
