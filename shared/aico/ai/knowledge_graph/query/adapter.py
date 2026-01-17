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
    
    def __init__(self, kg_storage, user_id: str):
        """
        Initialize adapter and build NetworkX graph for user.
        No longer takes db_connection - uses UoW pattern.
        
        Args:
            kg_storage: KnowledgeGraphStorage instance
            user_id: User ID to filter data
        """
        self.kg_storage = kg_storage
        self.user_id = user_id
        self._graph = None
    
    async def _build_graph(self) -> nx.DiGraph:
        """Build NetworkX DiGraph from KG storage via UoW."""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            logger.info(f"Building graph for user {self.user_id}")
            graph = nx.DiGraph()
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Load nodes via repository
                logger.debug(f"Loading nodes for user {self.user_id}")
                nodes = await uow.kg_nodes.list(
                    filters={'user_id': self.user_id, 'is_current': True},
                    limit=100000
                )
                
                node_count = 0
                for node in nodes:
                    node_id = node.id
                    label = node.label
                    
                    # Parse properties, ensuring it's always a dict
                    if node.properties is None:
                        properties = {}
                    elif isinstance(node.properties, str):
                        try:
                            properties = json.loads(node.properties)
                        except (json.JSONDecodeError, ValueError):
                            properties = {}
                    elif isinstance(node.properties, dict):
                        properties = node.properties
                    else:
                        properties = {}
                    
                    # Add node with properties from JSON
                    graph.add_node(node_id, **properties)
                    
                    # Add database columns as node attributes
                    graph.nodes[node_id]['id'] = node_id
                    graph.nodes[node_id]['label'] = label
                    graph.nodes[node_id]['confidence'] = node.confidence
                    graph.nodes[node_id]['source_text'] = node.source_text
                    graph.nodes[node_id]['created_at'] = node.created_at
                    graph.nodes[node_id]['updated_at'] = node.updated_at
                    graph.nodes[node_id]['is_current'] = node.is_current
                    graph.nodes[node_id]['language'] = node.language
                    graph.nodes[node_id]['valid_from'] = node.valid_from
                    graph.nodes[node_id]['valid_until'] = node.valid_until
                    
                    # Set __labels__ attribute (GrandCypher uses this for MATCH (n:Label))
                    graph.nodes[node_id]['__labels__'] = {label}
                    node_count += 1
                
                logger.info(f"Loaded {node_count} nodes for user {self.user_id}")
                
                # Load edges via repository
                logger.debug(f"Loading edges for user {self.user_id}")
                edges = await uow.kg_edges.list(
                    filters={'user_id': self.user_id, 'is_current': True},
                    limit=100000
                )
                
                edge_count = 0
                for edge in edges:
                    edge_id = edge.id
                    source_id = edge.source_id
                    target_id = edge.target_id
                    relation_type = edge.relation_type
                    
                    # Parse properties, ensuring it's always a dict
                    logger.debug(f"Edge {edge_id}: RAW properties type={type(edge.properties)}, value={repr(edge.properties)}")
                    
                    if edge.properties is None:
                        properties = {}
                        logger.debug(f"Edge {edge_id}: properties is None, using empty dict")
                    elif isinstance(edge.properties, str):
                        try:
                            parsed = json.loads(edge.properties)
                            logger.debug(f"Edge {edge_id}: JSON parsed to type={type(parsed)}, value={repr(parsed)}")
                            # Ensure parsed result is a dict
                            if isinstance(parsed, dict):
                                properties = parsed
                            else:
                                logger.warning(f"Edge {edge_id}: JSON parsed to {type(parsed)} instead of dict, using empty dict")
                                properties = {}
                        except (json.JSONDecodeError, ValueError) as e:
                            properties = {}
                            logger.debug(f"Edge {edge_id}: JSON parse failed ({e}), using empty dict")
                    elif isinstance(edge.properties, dict):
                        properties = edge.properties
                        logger.debug(f"Edge {edge_id}: properties is already dict")
                    else:
                        properties = {}
                        logger.debug(f"Edge {edge_id}: properties is unknown type {type(edge.properties)}, using empty dict")
                    
                    # Final safety check
                    if not isinstance(properties, dict):
                        logger.error(f"Edge {edge_id}: properties is {type(properties)} after parsing! Setting to empty dict")
                        properties = {}
                    
                    logger.debug(f"Edge {edge_id}: Final properties type={type(properties)}, is_dict={isinstance(properties, dict)}")
                
                    # Add edge with properties from JSON
                    graph.add_edge(source_id, target_id, **properties)
                
                # Add database columns as edge attributes
                graph.edges[source_id, target_id]['id'] = edge_id
                graph.edges[source_id, target_id]['relation_type'] = relation_type
                graph.edges[source_id, target_id]['confidence'] = edge.confidence
                graph.edges[source_id, target_id]['created_at'] = edge.created_at
                graph.edges[source_id, target_id]['updated_at'] = edge.updated_at
                graph.edges[source_id, target_id]['is_current'] = edge.is_current
                
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
    
    async def get_graph(self) -> nx.DiGraph:
        """
        Get NetworkX DiGraph for GrandCypher queries.
        
        Returns:
            NetworkX DiGraph with nodes and edges from KG storage
        """
        try:
            if self._graph is None:
                logger.debug(f"Building new graph for user {self.user_id}")
                self._graph = await self._build_graph()
            else:
                logger.debug(f"Using cached graph for user {self.user_id}")
            return self._graph
        except Exception as e:
            logger.error(f"Failed to get graph for user {self.user_id}: {e}", exc_info=True)
            raise
    
    def clear_cache(self):
        """Clear cached graph."""
        self._graph = None
