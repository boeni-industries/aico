"""
Graph adapter for GrandCypher.

Translates KG storage format to GrandCypher-compatible graph interface.
"""

import json
import logging
from typing import Any, Dict, List, Tuple
import networkx as nx

logger = logging.getLogger(__name__)


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
        try:
            logger.info(f"Building graph for user {self.user_id}")
            graph = nx.DiGraph()
            
            # Load nodes
            logger.debug(f"Loading nodes for user {self.user_id}")
            cursor = self.db_connection.execute(
                """SELECT id, label, properties, confidence, source_text, 
                          created_at, updated_at, is_current, language, valid_from, valid_until
                   FROM kg_nodes WHERE user_id = ? AND is_current = 1""",
                [self.user_id]
            )
            
            node_count = 0
            for row in cursor.fetchall():
                node_id = row[0]
                label = row[1]
                properties = json.loads(row[2]) if row[2] else {}
                
                # Add node with properties from JSON
                graph.add_node(node_id, **properties)
                
                # Add database columns as node attributes
                graph.nodes[node_id]['id'] = node_id
                graph.nodes[node_id]['label'] = label
                graph.nodes[node_id]['confidence'] = row[3]
                graph.nodes[node_id]['source_text'] = row[4]
                graph.nodes[node_id]['created_at'] = row[5]
                graph.nodes[node_id]['updated_at'] = row[6]
                graph.nodes[node_id]['is_current'] = row[7]
                graph.nodes[node_id]['language'] = row[8]
                graph.nodes[node_id]['valid_from'] = row[9]
                graph.nodes[node_id]['valid_until'] = row[10]
                
                # Set __labels__ attribute (GrandCypher uses this for MATCH (n:Label))
                # MUST be a set - GrandCypher uses set.intersection() for label matching
                graph.nodes[node_id]['__labels__'] = {label}
                node_count += 1
            
            logger.info(f"Loaded {node_count} nodes for user {self.user_id}")
            
            # Load edges
            logger.debug(f"Loading edges for user {self.user_id}")
            cursor = self.db_connection.execute(
                """SELECT id, source_id, target_id, relation_type, properties, 
                          confidence, created_at, updated_at, is_current
                   FROM kg_edges WHERE user_id = ? AND is_current = 1""",
                [self.user_id]
            )
            
            edge_count = 0
            for row in cursor.fetchall():
                edge_id = row[0]
                source_id = row[1]
                target_id = row[2]
                relation_type = row[3]
                properties = json.loads(row[4]) if row[4] else {}
                
                # Add edge with properties from JSON
                graph.add_edge(source_id, target_id, **properties)
                
                # Add database columns as edge attributes
                graph.edges[source_id, target_id]['id'] = edge_id
                graph.edges[source_id, target_id]['relation_type'] = relation_type
                graph.edges[source_id, target_id]['confidence'] = row[5]
                graph.edges[source_id, target_id]['created_at'] = row[6]
                graph.edges[source_id, target_id]['updated_at'] = row[7]
                graph.edges[source_id, target_id]['is_current'] = row[8]
                
                # Set __labels__ attribute (GrandCypher uses this for MATCH ()-[r:TYPE]->())
                # MUST be a set - GrandCypher uses set.intersection() for label matching
                graph.edges[source_id, target_id]['__labels__'] = {relation_type}
                if edge_count == 0:  # Log first edge for debugging
                    logger.info(f"First edge __labels__ type: {type(graph.edges[source_id, target_id]['__labels__'])}, value: {graph.edges[source_id, target_id]['__labels__']}")
                    logger.info(f"First edge relation_type: {type(relation_type)}, value: {relation_type}")
                edge_count += 1
            
            logger.info(f"Loaded {edge_count} edges for user {self.user_id}")
            logger.info(f"Graph built successfully: {node_count} nodes, {edge_count} edges")
            
            return graph
            
        except Exception as e:
            logger.error(f"Failed to build graph for user {self.user_id}: {e}", exc_info=True)
            raise
    
    def get_graph(self) -> nx.DiGraph:
        """
        Get NetworkX DiGraph for GrandCypher queries.
        
        Returns:
            NetworkX DiGraph with nodes and edges from KG storage
        """
        try:
            if self._graph is None:
                logger.debug(f"Building new graph for user {self.user_id}")
                self._graph = self._build_graph()
            else:
                logger.debug(f"Using cached graph for user {self.user_id}")
            return self._graph
        except Exception as e:
            logger.error(f"Failed to get graph for user {self.user_id}: {e}", exc_info=True)
            raise
    
    def clear_cache(self):
        """Clear cached graph."""
        self._graph = None
