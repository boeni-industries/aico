"""
Knowledge Graph Analytics Engine

Calculates comprehensive metrics for graph quality, structure, and insights.
Implements all 4 priority levels of KG analytics.
"""

from typing import Dict, List, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import math
import asyncio

from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork
from aico.data.kg.repository import KGNodeRepository, KGEdgeRepository


class KGAnalyticsEngine:
    """Comprehensive knowledge graph analytics calculator."""
    
    def __init__(self, user_id: str):
        # No longer takes db connection - will use UoW
        self.user_id = user_id
        self._nodes_cache = None
        self._edges_cache = None
        self._adjacency_cache = None
        self._logger = None
        
        # Try to get logger
        try:
            import logging
            self._logger = logging.getLogger(__name__)
        except:
            pass
    
    async def _load_graph_data(self):
        """Load and cache graph data for analysis via UoW."""
        if self._nodes_cache is None or self._edges_cache is None:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Load current nodes for user
                nodes_models = await uow.kg_nodes.list(
                    filters={'user_id': self.user_id, 'is_current': True},
                    limit=100000
                )
                self._nodes_cache = nodes_models
                
                # Load current edges for user
                edges_models = await uow.kg_edges.list(
                    filters={'user_id': self.user_id, 'is_current': True},
                    limit=100000
                )
                self._edges_cache = edges_models
        
        return self._nodes_cache, self._edges_cache
    
    async def _build_adjacency_list(self) -> Dict[str, Set[str]]:
        """Build adjacency list for graph algorithms."""
        if self._adjacency_cache is not None:
            return self._adjacency_cache
        
        _, edges = await self._load_graph_data()
        adjacency = defaultdict(set)
        
        # Building adjacency list from edge models
        for edge in edges:
            source_id = edge.source_id
            target_id = edge.target_id
            adjacency[source_id].add(target_id)
            adjacency[target_id].add(source_id)  # Undirected
        
        self._adjacency_cache = adjacency
        return adjacency
    
    # ========== PRIORITY 1: HEALTH & QUALITY METRICS ==========
    
    async def calculate_health_metrics(self) -> Dict[str, Any]:
        """Calculate health and quality metrics from repository data."""
        nodes, edges = await self._load_graph_data()
        
        # Build node ID set for orphan detection
        node_ids = {node.id for node in nodes}
        
        # Orphaned edges (edges pointing to non-existent nodes)
        orphaned_edges = sum(
            1 for edge in edges
            if edge.source_id not in node_ids or edge.target_id not in node_ids
        )
        
        # Duplicate nodes (same label + name in properties)
        label_name_counts = defaultdict(int)
        for node in nodes:
            props = json.loads(node.properties) if isinstance(node.properties, str) else node.properties
            name = props.get('name', '') if props else ''
            key = (node.label, name)
            label_name_counts[key] += 1
        duplicate_nodes = sum(1 for count in label_name_counts.values() if count > 1)
        
        # Stale nodes (not updated in 30+ days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        stale_nodes = sum(
            1 for node in nodes
            if node.updated_at and (
                datetime.fromisoformat(node.updated_at.replace('Z', '+00:00')) if isinstance(node.updated_at, str)
                else node.updated_at
            ) < thirty_days_ago
        )
        
        total_current_nodes = len(nodes)
        stale_percent = (stale_nodes / total_current_nodes * 100) if total_current_nodes > 0 else 0
        
        # Property completeness
        total_properties = 0
        for node in nodes:
            props = json.loads(node.properties) if isinstance(node.properties, str) else node.properties
            total_properties += len(props) if props else 0
        avg_properties = total_properties / total_current_nodes if total_current_nodes > 0 else 0
        
        # Growth in last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        nodes_24h = sum(
            1 for node in nodes
            if node.created_at and (
                datetime.fromisoformat(node.created_at.replace('Z', '+00:00')) if isinstance(node.created_at, str)
                else node.created_at
            ) >= yesterday
        )
        
        edges_24h = sum(
            1 for edge in edges
            if edge.created_at and (
                datetime.fromisoformat(edge.created_at.replace('Z', '+00:00')) if isinstance(edge.created_at, str)
                else edge.created_at
            ) >= yesterday
        )
        
        return {
            "orphaned_edges": orphaned_edges,
            "duplicate_nodes": duplicate_nodes,
            "stale_nodes_count": stale_nodes,
            "stale_nodes_percent": round(stale_percent, 2),
            "property_completeness": round(avg_properties, 2),
            "nodes_added_24h": nodes_24h,
            "edges_added_24h": edges_24h
        }
    
    # ========== PRIORITY 2: GRAPH STRUCTURE METRICS ==========
    
    async def calculate_structure_metrics(self) -> Dict[str, Any]:
        """Calculate graph structure and topology metrics."""
        nodes, edges = await self._load_graph_data()
        adjacency = await self._build_adjacency_list()
        
        n = len(nodes)
        m = len(edges)
        
        # Graph density: actual edges / possible edges
        max_edges = n * (n - 1) / 2 if n > 1 else 1
        density = m / max_edges if max_edges > 0 else 0
        
        # Degree statistics
        degrees = [len(adjacency[node.id]) for node in nodes]
        avg_degree = sum(degrees) / n if n > 0 else 0
        max_degree = max(degrees) if degrees else 0
        min_degree = min(degrees) if degrees else 0
        
        # Isolated nodes
        isolated = sum(1 for d in degrees if d == 0)
        
        # Connected components (BFS)
        components, largest_size = self._find_connected_components(current_nodes, adjacency)
        
        return {
            "graph_density": round(density, 4),
            "average_degree": round(avg_degree, 2),
            "max_degree": max_degree,
            "min_degree": min_degree,
            "isolated_nodes": isolated,
            "connected_components": components,
            "largest_component_size": largest_size
        }
    
    def _find_connected_components(self, nodes: List, adjacency: Dict) -> Tuple[int, int]:
        """Find connected components using BFS."""
        visited = set()
        component_sizes = []
        
        for node in nodes:
            node_id = node[0]
            if node_id not in visited:
                # BFS to find component
                component_size = 0
                queue = [node_id]
                visited.add(node_id)
                
                while queue:
                    current = queue.pop(0)
                    component_size += 1
                    
                    for neighbor in adjacency.get(current, set()):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                component_sizes.append(component_size)
        
        num_components = len(component_sizes)
        largest = max(component_sizes) if component_sizes else 0
        
        return num_components, largest
    
    # ========== PRIORITY 3: KNOWLEDGE INSIGHTS ==========
    
    async def calculate_temporal_metrics(self) -> Dict[str, Any]:
        """Calculate temporal activity metrics from cached data."""
        nodes, _ = await self._load_graph_data()
        
        # Growth rates
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        nodes_7d = sum(1 for n in nodes 
                      if n.created_at and (
                          datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) if isinstance(n.created_at, str)
                          else n.created_at
                      ) >= seven_days_ago)
        
        nodes_30d = sum(1 for n in nodes 
                       if n.created_at and (
                           datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) if isinstance(n.created_at, str)
                           else n.created_at
                       ) >= thirty_days_ago)
        
        total_nodes = len(nodes)
        
        growth_7d = (nodes_7d / total_nodes * 100) if total_nodes > 0 else 0
        growth_30d = (nodes_30d / total_nodes * 100) if total_nodes > 0 else 0
        
        # Activity by day (last 7 days)
        activity_by_day = {}
        for i in range(7):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            count = sum(1 for n in nodes 
                       if n.created_at and (
                           day_start <= (
                               datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) if isinstance(n.created_at, str)
                               else n.created_at
                           ) <= day_end
                       ))
            
            activity_by_day[day.strftime("%Y-%m-%d")] = count
        
        # Most active day
        most_active = max(activity_by_day.items(), key=lambda x: x[1])[0] if activity_by_day else None
        
        return {
            "growth_rate_7d": round(growth_7d, 2),
            "growth_rate_30d": round(growth_30d, 2),
            "most_active_day": most_active,
            "activity_by_day": activity_by_day
        }
    
    # ========== PRIORITY 4: ADVANCED ANALYTICS ==========
    
    async def calculate_centrality_metrics(self) -> Dict[str, Any]:
        """Calculate centrality and importance metrics."""
        nodes, edges = await self._load_graph_data()
        adjacency = await self._build_adjacency_list()
        
        # Nodes are already filtered for is_current=1 in _load_graph_data
        current_nodes = nodes
        
        # Top by degree centrality
        node_degrees = []
        for node in current_nodes:
            node_id = node[0]
            label = node[2]
            properties = json.loads(node[3]) if node[3] else {}
            degree = len(adjacency.get(node_id, set()))
            
            node_degrees.append({
                "id": node_id,
                "label": label,
                "name": properties.get("name", "Unknown"),
                "degree": degree
            })
        
        top_by_degree = sorted(node_degrees, key=lambda x: x["degree"], reverse=True)[:10]
        
        # Degree centrality calculated
        
        # PageRank (simplified iterative algorithm)
        # Calculating PageRank
        pagerank = self._calculate_pagerank(current_nodes, edges)
        top_by_pagerank = sorted(
            [{"id": k, "label": self._get_node_label(k, current_nodes), 
              "name": self._get_node_name(k, current_nodes), "score": v} 
             for k, v in pagerank.items()],
            key=lambda x: x["score"],
            reverse=True
        )[:10]
        # PageRank complete
        
        # Betweenness centrality (approximate for large graphs)
        betweenness = self._calculate_betweenness(current_nodes, adjacency)
        top_by_betweenness = sorted(
            [{"id": k, "label": self._get_node_label(k, current_nodes),
              "name": self._get_node_name(k, current_nodes), "score": v}
             for k, v in betweenness.items()],
            key=lambda x: x["score"],
            reverse=True
        )[:10]
        
        # Betweenness centrality calculated
        
        return {
            "top_by_degree": top_by_degree,
            "top_by_pagerank": top_by_pagerank,
            "top_by_betweenness": top_by_betweenness
        }
    
    def detect_duplicate_pairs(self) -> List[Dict[str, Any]]:
        """Detect and return actual duplicate node pairs."""
        nodes, _ = self._load_graph_data()
        
        if len(nodes) < 2:
            return []
        
        # Convert nodes to dict format
        node_dicts = []
        for node in nodes:
            node_dict = {
                'id': node['id'],
                'label': node['label'],
                'properties': node.get('properties', {})
            }
            node_dicts.append(node_dict)
        
        # Use duplicate detector
        from backend.api.kg.duplicate_detector import DuplicateDetector
        detector = DuplicateDetector(similarity_threshold=0.80)
        
        duplicate_pairs = detector.detect_duplicates(node_dicts)
        
        return duplicate_pairs
    
    def calculate_clustering_metrics(self) -> Dict[str, Any]:
        """Calculate clustering and community metrics."""
        nodes, _ = self._load_graph_data()
        adjacency = self._build_adjacency_list()
        
        # Nodes are already filtered for is_current=1 in _load_graph_data
        current_nodes = nodes
        
        # Local clustering coefficients
        clustering_coeffs = []
        for node in current_nodes:
            node_id = node[0]
            neighbors = adjacency.get(node_id, set())
            k = len(neighbors)
            
            if k < 2:
                clustering_coeffs.append(0)
                continue
            
            # Count edges between neighbors
            edges_between = 0
            neighbors_list = list(neighbors)
            for i, n1 in enumerate(neighbors_list):
                for n2 in neighbors_list[i+1:]:
                    if n2 in adjacency.get(n1, set()):
                        edges_between += 1
            
            max_edges = k * (k - 1) / 2
            coeff = edges_between / max_edges if max_edges > 0 else 0
            clustering_coeffs.append(coeff)
        
        # Global clustering coefficient
        global_cc = sum(clustering_coeffs) / len(clustering_coeffs) if clustering_coeffs else 0
        
        # Average clustering coefficient
        avg_cc = global_cc  # Same for unweighted graphs
        
        # Community detection (simple label propagation)
        communities = self._detect_communities(current_nodes, adjacency)
        num_communities = len(set(communities.values()))
        
        # Modularity score
        modularity = self._calculate_modularity(adjacency, communities)
        
        return {
            "global_clustering_coefficient": round(global_cc, 4),
            "average_clustering_coefficient": round(avg_cc, 4),
            "communities_detected": num_communities,
            "modularity_score": round(modularity, 4)
        }
    
    def _calculate_pagerank(self, nodes: List, edges: List, damping: float = 0.85, iterations: int = 20) -> Dict[str, float]:
        """Calculate PageRank scores."""
        node_ids = [n[0] for n in nodes]
        n = len(node_ids)
        
        if n == 0:
            return {}
        
        # Initialize PageRank
        pagerank = {node_id: 1.0 / n for node_id in node_ids}
        
        # Build outgoing edges map
        outgoing = defaultdict(list)
        for edge in edges:
            if edge[10] == 1:  # is_current
                outgoing[edge[2]].append(edge[3])  # source -> target
        
        # Calculating PageRank
        
        # Iterative calculation
        for _ in range(iterations):
            new_pagerank = {}
            
            for node_id in node_ids:
                rank_sum = 0
                # Sum contributions from incoming edges
                for other_id in node_ids:
                    if node_id in outgoing.get(other_id, []):
                        out_degree = len(outgoing.get(other_id, []))
                        if out_degree > 0:
                            rank_sum += pagerank[other_id] / out_degree
                
                new_pagerank[node_id] = (1 - damping) / n + damping * rank_sum
            
            pagerank = new_pagerank
        
        return pagerank
    
    def _calculate_betweenness(self, nodes: List, adjacency: Dict, sample_size: int = 100) -> Dict[str, float]:
        """Calculate approximate betweenness centrality (sampled for performance)."""
        node_ids = [n[0] for n in nodes]
        betweenness = {node_id: 0.0 for node_id in node_ids}
        
        if len(node_ids) < 2:
            return betweenness
        
        # Sample nodes for BFS (full calculation is O(n^3))
        import random
        sample = random.sample(node_ids, min(sample_size, len(node_ids)))
        
        for source in sample:
            # BFS to find shortest paths
            stack = []
            paths = {node_id: [] for node_id in node_ids}
            paths[source] = [[source]]
            sigma = {node_id: 0 for node_id in node_ids}
            sigma[source] = 1
            dist = {node_id: -1 for node_id in node_ids}
            dist[source] = 0
            queue = [source]
            
            while queue:
                v = queue.pop(0)
                stack.append(v)
                
                for w in adjacency.get(v, set()):
                    if w not in node_ids:
                        continue
                    
                    # First time we see w
                    if dist[w] < 0:
                        queue.append(w)
                        dist[w] = dist[v] + 1
                    
                    # Shortest path to w via v
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        for path in paths[v]:
                            paths[w].append(path + [w])
            
            # Accumulate betweenness
            delta = {node_id: 0 for node_id in node_ids}
            while stack:
                w = stack.pop()
                for v in adjacency.get(w, set()):
                    if v in node_ids and dist[v] == dist[w] - 1:
                        delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
                if w != source:
                    betweenness[w] += delta[w]
        
        # Normalize
        n = len(node_ids)
        if n > 2:
            scale = 2.0 / ((n - 1) * (n - 2))
            for node_id in betweenness:
                betweenness[node_id] *= scale
        
        return betweenness
    
    def _detect_communities(self, nodes: List, adjacency: Dict, iterations: int = 10) -> Dict[str, int]:
        """Detect communities using label propagation."""
        node_ids = [n[0] for n in nodes]
        
        # Initialize each node with unique label
        labels = {node_id: i for i, node_id in enumerate(node_ids)}
        
        # Iteratively update labels
        for _ in range(iterations):
            new_labels = labels.copy()
            
            for node_id in node_ids:
                neighbors = adjacency.get(node_id, set())
                if not neighbors:
                    continue
                
                # Count neighbor labels
                neighbor_labels = [labels[n] for n in neighbors if n in labels]
                if neighbor_labels:
                    # Adopt most common label
                    most_common = Counter(neighbor_labels).most_common(1)[0][0]
                    new_labels[node_id] = most_common
            
            labels = new_labels
        
        return labels
    
    def _calculate_modularity(self, adjacency: Dict, communities: Dict) -> float:
        """Calculate modularity score for community structure."""
        if not communities:
            return 0.0
        
        # Count edges
        m = sum(len(neighbors) for neighbors in adjacency.values()) / 2
        
        if m == 0:
            return 0.0
        
        modularity = 0.0
        for node_i, comm_i in communities.items():
            for node_j, comm_j in communities.items():
                if comm_i == comm_j:
                    # Same community
                    actual_edge = 1 if node_j in adjacency.get(node_i, set()) else 0
                    ki = len(adjacency.get(node_i, set()))
                    kj = len(adjacency.get(node_j, set()))
                    expected_edge = (ki * kj) / (2 * m)
                    modularity += actual_edge - expected_edge
        
        modularity /= (2 * m)
        return modularity
    
    def _get_node_label(self, node_id: str, nodes: List) -> str:
        """Get node label by ID."""
        for node in nodes:
            if node[0] == node_id:
                return node[2]
        return "Unknown"
    
    def _get_node_name(self, node_id: str, nodes: List) -> str:
        """Get node name by ID."""
        for node in nodes:
            if node[0] == node_id:
                properties = json.loads(node[3]) if node[3] else {}
                return properties.get("name", "Unknown")
        return "Unknown"
