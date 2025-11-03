"""
Graph adapter for GrandCypher.

Translates KG storage format to GrandCypher-compatible graph interface.
"""

import json
from typing import Any, Dict, List, Tuple
import networkx as nx


class KGGraphAdapter:
    """
    Adapter that builds a NetworkX DiGraph from KG storage for GrandCypher.
    
    GrandCypher expects a NetworkX graph with:
    - Node properties as attributes
    - Node labels in __labels__ attribute (set of strings)
    - Edge properties as attributes
    - Edge labels in __labels__ attribute (set of strings)
    """
    
    def __init__(self, kg_storage, db_connection, user_id: str):
        """
        Initialize adapter and build NetworkX graph for user.
        
        Args:
            kg_storage: KnowledgeGraphStorage instance
            db_connection: Database connection for direct queries
            user_id: User ID to filter data
        """
        self.kg_storage = kg_storage
        self.db_connection = db_connection
        self.user_id = user_id
        self._graph = None
    
    def _build_graph(self) -> nx.DiGraph:
        """Build NetworkX DiGraph from KG storage."""
        graph = nx.DiGraph()
        
        # Load nodes
        cursor = self.db_connection.execute(
            "SELECT id, label, properties FROM kg_nodes WHERE user_id = ? AND is_current = 1",
            [self.user_id]
        )
        
        for row in cursor.fetchall():
            node_id = row[0]
            label = row[1]
            properties = json.loads(row[2]) if row[2] else {}
            
            # Add node with properties
            graph.add_node(node_id, **properties)
            
            # Set __labels__ attribute (GrandCypher uses this for MATCH (n:Label))
            graph.nodes[node_id]['__labels__'] = {label}
        
        # Load edges
        cursor = self.db_connection.execute(
            "SELECT source_id, target_id, relation_type, properties FROM kg_edges WHERE user_id = ? AND is_current = 1",
            [self.user_id]
        )
        
        for row in cursor.fetchall():
            source_id = row[0]
            target_id = row[1]
            relation_type = row[2]
            properties = json.loads(row[3]) if row[3] else {}
            
            # Add edge with properties
            graph.add_edge(source_id, target_id, **properties)
            
            # Set __labels__ attribute (GrandCypher uses this for MATCH ()-[r:TYPE]->())
            graph.edges[source_id, target_id]['__labels__'] = {relation_type}
        
        return graph
    
    def get_graph(self) -> nx.DiGraph:
        """
        Get NetworkX DiGraph for GrandCypher queries.
        
        Returns:
            NetworkX DiGraph with nodes and edges from KG storage
        """
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    def clear_cache(self):
        """Clear cached graph."""
        self._graph = None
