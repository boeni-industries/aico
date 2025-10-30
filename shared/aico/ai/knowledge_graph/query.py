"""
Graph Query Engine

Advanced graph traversal and multi-hop reasoning for knowledge graphs.
Implements best-in-class algorithms for path finding and relationship discovery.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque, defaultdict
import heapq
from dataclasses import dataclass

from aico.core.logging import get_logger

from .models import Node, Edge, PropertyGraph
from .storage import PropertyGraphStorage

logger = get_logger("shared", "ai.knowledge_graph.query")


@dataclass
class GraphPath:
    """Represents a path through the graph."""
    nodes: List[Node]
    edges: List[Edge]
    total_weight: float
    hop_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "nodes": [{"id": n.id, "label": n.label, "properties": n.properties} for n in self.nodes],
            "edges": [{"id": e.id, "relation_type": e.relation_type, "properties": e.properties} for e in self.edges],
            "total_weight": self.total_weight,
            "hop_count": self.hop_count
        }


@dataclass
class SubgraphResult:
    """Result of a subgraph query."""
    center_node: Node
    neighbors: List[Node]
    edges: List[Edge]
    depth: int
    node_count: int
    edge_count: int


class GraphQueryEngine:
    """
    Advanced graph query engine with traversal and reasoning capabilities.
    
    Features:
    - BFS/DFS traversal
    - Shortest path finding (Dijkstra's algorithm)
    - Multi-hop relationship queries
    - Subgraph extraction
    - Pattern matching
    """
    
    def __init__(self, storage: PropertyGraphStorage):
        """
        Initialize query engine.
        
        Args:
            storage: PropertyGraphStorage instance
        """
        self.storage = storage
    
    async def traverse_bfs(
        self,
        start_node_id: str,
        max_depth: int = 3,
        edge_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Node, int]]:
        """
        Breadth-first traversal from a starting node.
        
        Args:
            start_node_id: Starting node ID
            max_depth: Maximum traversal depth
            edge_filter: Optional filter for edge types
            
        Returns:
            List of (node, depth) tuples in BFS order
        """
        visited = set()
        queue = deque([(start_node_id, 0)])
        result = []
        
        while queue:
            node_id, depth = queue.popleft()
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            
            # Get node
            node = await self.storage.get_node(node_id)
            if not node:
                continue
            
            result.append((node, depth))
            
            # Get outgoing edges
            edges = await self.storage.get_edges_for_node(node_id, direction="outgoing")
            
            # Filter edges if needed
            if edge_filter:
                edges = [e for e in edges if self._matches_filter(e, edge_filter)]
            
            # Add neighbors to queue
            for edge in edges:
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))
        
        logger.info(f"BFS traversal found {len(result)} nodes in {max_depth} hops")
        return result
    
    async def traverse_dfs(
        self,
        start_node_id: str,
        max_depth: int = 3,
        edge_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Node, int]]:
        """
        Depth-first traversal from a starting node.
        
        Args:
            start_node_id: Starting node ID
            max_depth: Maximum traversal depth
            edge_filter: Optional filter for edge types
            
        Returns:
            List of (node, depth) tuples in DFS order
        """
        visited = set()
        result = []
        
        async def dfs_recursive(node_id: str, depth: int):
            if node_id in visited or depth > max_depth:
                return
            
            visited.add(node_id)
            
            # Get node
            node = await self.storage.get_node(node_id)
            if not node:
                return
            
            result.append((node, depth))
            
            # Get outgoing edges
            edges = await self.storage.get_edges_for_node(node_id, direction="outgoing")
            
            # Filter edges if needed
            if edge_filter:
                edges = [e for e in edges if self._matches_filter(e, edge_filter)]
            
            # Recursively visit neighbors
            for edge in edges:
                await dfs_recursive(edge.target_id, depth + 1)
        
        await dfs_recursive(start_node_id, 0)
        
        logger.info(f"DFS traversal found {len(result)} nodes in {max_depth} hops")
        return result
    
    async def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 5
    ) -> Optional[GraphPath]:
        """
        Find shortest path between two nodes using Dijkstra's algorithm.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_hops: Maximum number of hops to search
            
        Returns:
            GraphPath if found, None otherwise
        """
        # Priority queue: (total_weight, node_id, path_nodes, path_edges)
        pq = [(0.0, source_id, [], [])]
        visited = set()
        
        while pq:
            weight, current_id, path_nodes, path_edges = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # Get current node
            current_node = await self.storage.get_node(current_id)
            if not current_node:
                continue
            
            path_nodes = path_nodes + [current_node]
            
            # Check if we reached target
            if current_id == target_id:
                return GraphPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    total_weight=weight,
                    hop_count=len(path_edges)
                )
            
            # Check max hops
            if len(path_edges) >= max_hops:
                continue
            
            # Explore neighbors
            edges = await self.storage.get_edges_for_node(current_id, direction="outgoing")
            
            for edge in edges:
                if edge.target_id not in visited:
                    # Edge weight = 1 - confidence (lower confidence = higher cost)
                    edge_weight = 1.0 - edge.confidence
                    new_weight = weight + edge_weight
                    new_path_edges = path_edges + [edge]
                    
                    heapq.heappush(pq, (new_weight, edge.target_id, path_nodes, new_path_edges))
        
        logger.info(f"No path found between {source_id} and {target_id}")
        return None
    
    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 4,
        max_paths: int = 10
    ) -> List[GraphPath]:
        """
        Find all paths between two nodes (up to max_paths).
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_hops: Maximum number of hops
            max_paths: Maximum number of paths to return
            
        Returns:
            List of GraphPath objects
        """
        paths = []
        
        async def dfs_paths(current_id: str, path_nodes: List[Node], path_edges: List[Edge], visited: Set[str]):
            if len(paths) >= max_paths:
                return
            
            if current_id == target_id:
                # Found a path
                total_weight = sum(1.0 - e.confidence for e in path_edges)
                paths.append(GraphPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    total_weight=total_weight,
                    hop_count=len(path_edges)
                ))
                return
            
            if len(path_edges) >= max_hops:
                return
            
            # Get outgoing edges
            edges = await self.storage.get_edges_for_node(current_id, direction="outgoing")
            
            for edge in edges:
                if edge.target_id not in visited:
                    next_node = await self.storage.get_node(edge.target_id)
                    if next_node:
                        new_visited = visited | {edge.target_id}
                        await dfs_paths(
                            edge.target_id,
                            path_nodes + [next_node],
                            path_edges + [edge],
                            new_visited
                        )
        
        # Start DFS
        source_node = await self.storage.get_node(source_id)
        if source_node:
            await dfs_paths(source_id, [source_node], [], {source_id})
        
        # Sort by hop count and weight
        paths.sort(key=lambda p: (p.hop_count, p.total_weight))
        
        logger.info(f"Found {len(paths)} paths between {source_id} and {target_id}")
        return paths[:max_paths]
    
    async def multi_hop_query(
        self,
        query: str,
        user_id: str,
        max_hops: int = 3
    ) -> List[GraphPath]:
        """
        Answer multi-hop questions using graph traversal.
        
        Example: "Who does Sarah know that works on AI?"
        - Find Sarah (PERSON)
        - Follow KNOWS edges
        - Filter by WORKS_ON -> AI
        
        Args:
            query: Natural language query
            user_id: User ID
            max_hops: Maximum hops to search
            
        Returns:
            List of GraphPath objects representing answers
        """
        # Parse query to extract entities and relationships
        # This is a simplified version - in production, use LLM for query parsing
        
        # For now, use semantic search to find starting nodes
        start_nodes = await self.storage.search_nodes(query, user_id, top_k=5)
        
        if not start_nodes:
            logger.info(f"No starting nodes found for query: {query}")
            return []
        
        # Traverse from each starting node
        all_paths = []
        for start_node in start_nodes:
            # BFS traversal
            traversal = await self.traverse_bfs(start_node.id, max_depth=max_hops)
            
            # Convert to paths
            for node, depth in traversal:
                if depth > 0:  # Skip the start node itself
                    # Find path from start to this node
                    path = await self.find_shortest_path(start_node.id, node.id, max_hops=max_hops)
                    if path:
                        all_paths.append(path)
        
        # Rank by relevance (shorter paths + higher confidence)
        all_paths.sort(key=lambda p: (p.hop_count, p.total_weight))
        
        logger.info(f"Multi-hop query found {len(all_paths)} paths")
        return all_paths[:10]  # Return top 10
    
    async def get_subgraph(
        self,
        center_node_id: str,
        radius: int = 2,
        max_nodes: int = 50
    ) -> SubgraphResult:
        """
        Extract a subgraph around a center node.
        
        Args:
            center_node_id: Center node ID
            radius: Number of hops to include
            max_nodes: Maximum nodes to include
            
        Returns:
            SubgraphResult with nodes and edges
        """
        center_node = await self.storage.get_node(center_node_id)
        if not center_node:
            raise ValueError(f"Node {center_node_id} not found")
        
        # BFS to collect nodes within radius
        traversal = await self.traverse_bfs(center_node_id, max_depth=radius)
        
        # Limit nodes
        nodes_with_depth = traversal[:max_nodes]
        node_ids = {n.id for n, _ in nodes_with_depth}
        
        # Collect all edges between these nodes
        all_edges = []
        for node, _ in nodes_with_depth:
            edges = await self.storage.get_edges_for_node(node.id, direction="both")
            # Only include edges where both endpoints are in the subgraph
            for edge in edges:
                if edge.source_id in node_ids and edge.target_id in node_ids:
                    all_edges.append(edge)
        
        # Deduplicate edges
        seen_edge_ids = set()
        unique_edges = []
        for edge in all_edges:
            if edge.id not in seen_edge_ids:
                seen_edge_ids.add(edge.id)
                unique_edges.append(edge)
        
        neighbors = [n for n, d in nodes_with_depth if d > 0]
        
        return SubgraphResult(
            center_node=center_node,
            neighbors=neighbors,
            edges=unique_edges,
            depth=radius,
            node_count=len(nodes_with_depth),
            edge_count=len(unique_edges)
        )
    
    async def pattern_match(
        self,
        pattern: List[Tuple[str, str]],
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Node]]:
        """
        Match a pattern in the graph.
        
        Pattern format: [(node_label, edge_type), ...]
        Example: [("PERSON", "KNOWS"), ("PERSON", "WORKS_ON"), ("PROJECT", None)]
        Matches: PERSON -KNOWS-> PERSON -WORKS_ON-> PROJECT
        
        Args:
            pattern: List of (node_label, edge_type) tuples
            user_id: User ID
            limit: Maximum matches to return
            
        Returns:
            List of dictionaries mapping pattern positions to nodes
        """
        if not pattern:
            return []
        
        matches = []
        
        # Get all nodes of the first type
        first_label = pattern[0][0]
        start_nodes = await self.storage.get_user_nodes(user_id, label=first_label, current_only=True)
        
        for start_node in start_nodes:
            # Try to match pattern from this node
            match = await self._match_pattern_from_node(start_node, pattern)
            if match:
                matches.append(match)
                if len(matches) >= limit:
                    break
        
        logger.info(f"Pattern matching found {len(matches)} matches")
        return matches
    
    async def _match_pattern_from_node(
        self,
        start_node: Node,
        pattern: List[Tuple[str, str]]
    ) -> Optional[Dict[str, Node]]:
        """
        Try to match a pattern starting from a specific node.
        
        Args:
            start_node: Starting node
            pattern: Pattern to match
            
        Returns:
            Dictionary mapping pattern positions to nodes, or None if no match
        """
        match = {"0": start_node}
        current_node = start_node
        
        for i, (next_label, edge_type) in enumerate(pattern[1:], start=1):
            # Get outgoing edges of the required type
            edges = await self.storage.get_edges_for_node(current_node.id, direction="outgoing")
            
            if edge_type:
                edges = [e for e in edges if e.relation_type == edge_type]
            
            # Find a target node with the required label
            found = False
            for edge in edges:
                target_node = await self.storage.get_node(edge.target_id)
                if target_node and target_node.label == next_label:
                    match[str(i)] = target_node
                    current_node = target_node
                    found = True
                    break
            
            if not found:
                return None
        
        return match
    
    def _matches_filter(self, edge: Edge, filter_dict: Dict[str, Any]) -> bool:
        """Check if edge matches filter criteria."""
        for key, value in filter_dict.items():
            if key == "relation_type":
                if edge.relation_type != value:
                    return False
            elif key in edge.properties:
                if edge.properties[key] != value:
                    return False
        return True
