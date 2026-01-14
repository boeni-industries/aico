"""
Knowledge Graph Service

Replaces shared/aico/ai/knowledge_graph/storage.py with repository-based implementation.
Provides high-level KG operations using the 6 KG repositories.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import uuid4

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

logger = get_logger("shared.services.kg")


class KGService:
    """
    Service layer for Knowledge Graph operations.
    
    Replaces the legacy KG storage classes.
    Uses KG repositories through Unit of Work pattern.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== Node Operations ====================

    async def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new KG node."""
        try:
            from aico.ai.knowledge_graph.models import Node
            
            node = node_data if isinstance(node_data, Node) else Node(**node_data)
            created = await self.uow.kg_nodes.create(node)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Created node", extra={"node_id": created.id, "user_id": created.user_id})
            return created
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to create node: {e}")
            await self.uow.rollback()
            raise

    async def get_node(self, node_id: str) -> Optional[Any]:
        """Retrieve a node by ID."""
        try:
            return await self.uow.kg_nodes.get_by_id(node_id)
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to retrieve node: {e}", extra={"node_id": node_id})
            raise

    async def list_nodes(self, user_id: str, label: Optional[str] = None) -> List[Any]:
        """List nodes for a user, optionally filtered by label."""
        try:
            filters = {"user_id": user_id, "is_current": True}
            if label:
                filters["label"] = label
            
            return await self.uow.kg_nodes.list(filters=filters)
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to list nodes: {e}", extra={"user_id": user_id})
            raise

    async def update_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a node."""
        try:
            from aico.ai.knowledge_graph.models import Node
            
            node = node_data if isinstance(node_data, Node) else Node(**node_data)
            updated = await self.uow.kg_nodes.update(node)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Updated node", extra={"node_id": node.id})
            return updated
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to update node: {e}")
            await self.uow.rollback()
            raise

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node (mark as not current)."""
        try:
            success = await self.uow.kg_nodes.delete(node_id)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Deleted node", extra={"node_id": node_id})
            return success
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to delete node: {e}", extra={"node_id": node_id})
            await self.uow.rollback()
            raise

    # ==================== Edge Operations ====================

    async def create_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new KG edge (relationship)."""
        try:
            from aico.ai.knowledge_graph.models import Edge
            
            edge = edge_data if isinstance(edge_data, Edge) else Edge(**edge_data)
            created = await self.uow.kg_edges.create(edge)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Created edge", extra={
                "edge_id": created.id,
                "source_id": created.source_id,
                "target_id": created.target_id
            })
            return created
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to create edge: {e}")
            await self.uow.rollback()
            raise

    async def get_edge(self, edge_id: str) -> Optional[Any]:
        """Retrieve an edge by ID."""
        try:
            return await self.uow.kg_edges.get_by_id(edge_id)
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to retrieve edge: {e}", extra={"edge_id": edge_id})
            raise

    async def list_edges(self, user_id: str, source_id: Optional[str] = None, target_id: Optional[str] = None) -> List[Any]:
        """List edges for a user, optionally filtered by source/target."""
        try:
            filters = {"user_id": user_id, "is_current": True}
            if source_id:
                filters["source_id"] = source_id
            if target_id:
                filters["target_id"] = target_id
            
            return await self.uow.kg_edges.list(filters=filters)
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to list edges: {e}", extra={"user_id": user_id})
            raise

    async def get_node_edges(self, node_id: str) -> List[Any]:
        """Get all edges connected to a node (both incoming and outgoing)."""
        try:
            outgoing = await self.uow.kg_edges.list(filters={"source_id": node_id, "is_current": True})
            incoming = await self.uow.kg_edges.list(filters={"target_id": node_id, "is_current": True})
            return outgoing + incoming
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to get node edges: {e}", extra={"node_id": node_id})
            raise

    async def update_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an edge."""
        try:
            from aico.ai.knowledge_graph.models import Edge
            
            edge = edge_data if isinstance(edge_data, Edge) else Edge(**edge_data)
            updated = await self.uow.kg_edges.update(edge)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Updated edge", extra={"edge_id": edge.id})
            return updated
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to update edge: {e}", extra={"edge_id": edge.id})
            await self.uow.rollback()
            raise

    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge (mark as not current)."""
        try:
            success = await self.uow.kg_edges.delete(edge_id)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Deleted edge", extra={"edge_id": edge_id})
            return success
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to delete edge: {e}", extra={"edge_id": edge_id})
            await self.uow.rollback()
            raise

    # ==================== Property Operations ====================

    async def set_node_property(self, node_id: str, key: str, value: Any) -> bool:
        """Set a property on a node."""
        try:
            # Node properties are stored in the properties dict of Node
            
            prop = KGNodeProperty(
                node_id=node_id,
                property_key=key,
                property_value=json.dumps(value) if not isinstance(value, str) else value,
                created_at=datetime.now(UTC)
            )
            await self.uow.kg_node_properties.create(prop)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Set node property", extra={"node_id": node_id, "key": key})
            return True
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to set node property: {e}", extra={"node_id": node_id})
            await self.uow.rollback()
            raise

    async def get_node_properties(self, node_id: str) -> Dict[str, Any]:
        """Get all properties for a node."""
        try:
            props = await self.uow.kg_node_properties.list(filters={"node_id": node_id})
            return {p.property_key: p.property_value for p in props}
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to get node properties: {e}", extra={"node_id": node_id})
            raise

    async def set_edge_property(self, edge_id: str, key: str, value: Any) -> bool:
        """Set a property on an edge."""
        try:
            # Edge properties are stored in the properties dict of Edge
            
            prop = KGEdgeProperty(
                edge_id=edge_id,
                property_key=key,
                property_value=json.dumps(value) if not isinstance(value, str) else value,
                created_at=datetime.now(UTC)
            )
            await self.uow.kg_edge_properties.create(prop)
            await self.uow.commit()
            
            logger.info("[KG_SERVICE] Set edge property", extra={"edge_id": edge_id, "key": key})
            return True
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to set edge property: {e}", extra={"edge_id": edge_id})
            await self.uow.rollback()
            raise

    async def get_edge_properties(self, edge_id: str) -> Dict[str, Any]:
        """Get all properties for an edge."""
        try:
            props = await self.uow.kg_edge_properties.list(filters={"edge_id": edge_id})
            return {p.property_key: p.property_value for p in props}
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to get edge properties: {e}", extra={"edge_id": edge_id})
            raise

    # ==================== Query Operations ====================

    async def find_nodes_by_label(self, user_id: str, label: str) -> List[Any]:
        """Find all nodes with a specific label."""
        return await self.list_nodes(user_id, label=label)

    async def find_connected_nodes(self, node_id: str, relation_type: Optional[str] = None) -> List[Any]:
        """Find all nodes connected to a given node."""
        try:
            filters = {"source_id": node_id, "is_current": True}
            if relation_type:
                filters["relation_type"] = relation_type
            
            edges = await self.uow.kg_edges.list(filters=filters)
            
            # Get target nodes
            nodes = []
            for edge in edges:
                node = await self.get_node(edge.target_id)
                if node:
                    nodes.append(node)
            
            return nodes
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to find connected nodes: {e}", extra={"node_id": node_id})
            raise

    async def count_user_nodes(self, user_id: str) -> int:
        """Count total nodes for a user."""
        try:
            return await self.uow.kg_nodes.count(filters={"user_id": user_id, "is_current": True})
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to count nodes: {e}", extra={"user_id": user_id})
            raise

    async def count_user_edges(self, user_id: str) -> int:
        """Count total edges for a user."""
        try:
            return await self.uow.kg_edges.count(filters={"user_id": user_id, "is_current": True})
        except Exception as e:
            logger.error(f"[KG_SERVICE] Failed to count edges: {e}", extra={"user_id": user_id})
            raise
