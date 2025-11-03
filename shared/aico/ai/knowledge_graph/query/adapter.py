"""
Graph adapter for GrandCypher.

Translates KG storage format to GrandCypher-compatible graph interface.
"""

import json
from typing import Any, Dict, List, Tuple


class KGGraphAdapter:
    """
    Adapter that makes KG storage compatible with GrandCypher.
    
    GrandCypher expects a graph-like object with nodes() and edges() methods
    that return NetworkX-compatible data structures.
    """
    
    def __init__(self, kg_storage, db_connection, user_id: str):
        """
        Initialize adapter for a specific user's graph.
        
        Args:
            kg_storage: KnowledgeGraphStorage instance
            db_connection: Database connection for direct queries
            user_id: User ID to filter data
        """
        self.kg_storage = kg_storage
        self.db_connection = db_connection
        self.user_id = user_id
        self._nodes_cache = None
        self._edges_cache = None
    
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        """
        Return all nodes for the user in NetworkX format.
        
        Returns:
            Dict of {node_id: {properties}} where properties include:
            - label: Entity type (PERSON, PLACE, etc.)
            - All properties from the node's properties JSON
        """
        if self._nodes_cache is not None:
            return self._nodes_cache
        
        # Query nodes from libSQL
        cursor = self.db_connection.execute(
            "SELECT id, label, properties FROM kg_nodes WHERE user_id = ?",
            [self.user_id]
        )
        
        nodes = {}
        for row in cursor.fetchall():
            node_id = row[0]
            label = row[1]
            properties = json.loads(row[2]) if row[2] else {}
            
            # Add label to properties for GrandCypher filtering
            properties['label'] = label
            properties['id'] = node_id
            
            nodes[node_id] = properties
        
        self._nodes_cache = nodes
        return nodes
    
    def edges(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Return all edges for the user in NetworkX format.
        
        Returns:
            List of (source_id, target_id, properties) tuples where properties include:
            - relation_type: Type of relationship
            - All properties from the edge's properties JSON
        """
        if self._edges_cache is not None:
            return self._edges_cache
        
        # Query edges from libSQL
        cursor = self.db_connection.execute(
            "SELECT source_id, target_id, relation_type, properties FROM kg_edges WHERE user_id = ?",
            [self.user_id]
        )
        
        edges = []
        for row in cursor.fetchall():
            source_id = row[0]
            target_id = row[1]
            relation_type = row[2]
            properties = json.loads(row[3]) if row[3] else {}
            
            # Add relation_type to properties for GrandCypher filtering
            properties['relation_type'] = relation_type
            properties['label'] = relation_type  # GrandCypher uses 'label' for edge types
            
            edges.append((source_id, target_id, properties))
        
        self._edges_cache = edges
        return edges
    
    def clear_cache(self):
        """Clear cached nodes and edges."""
        self._nodes_cache = None
        self._edges_cache = None
