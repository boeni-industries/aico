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
from aico.data.libsql.encrypted import EncryptedLibSQLConnection


class KGAnalyticsEngine:
    """Comprehensive knowledge graph analytics calculator."""
    
    def __init__(self, db: EncryptedLibSQLConnection, user_id: str):
        self.db = db
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
    
    def _load_graph_data(self):
        """Load and cache graph data for analysis."""
        if self._nodes_cache is None:
            cursor = self.db.execute(
                "SELECT * FROM kg_nodes WHERE user_id = ? AND is_current = 1",
                [self.user_id]
            )
            self._nodes_cache = cursor.fetchall()
        
        if self._edges_cache is None:
            cursor = self.db.execute(
                "SELECT * FROM kg_edges WHERE user_id = ? AND is_current = 1",
                [self.user_id]
            )
            self._edges_cache = cursor.fetchall()
        
        return self._nodes_cache, self._edges_cache
    
    def _build_adjacency_list(self) -> Dict[str, Set[str]]:
        """Build adjacency list for graph algorithms."""
        if self._adjacency_cache is not None:
            return self._adjacency_cache
        
        _, edges = self._load_graph_data()
        adjacency = defaultdict(set)
        
        from backend.api.kg.router import logger
        logger.info(f"Building adjacency list from {len(edges)} edges")
        
        # Edges are already filtered for is_current=1 in _load_graph_data
        for edge in edges:
            source_id = edge[2]
            target_id = edge[3]
            adjacency[source_id].add(target_id)
            adjacency[target_id].add(source_id)  # Undirected
        
        logger.info(f"Adjacency list built with {len(adjacency)} nodes")
        
        self._adjacency_cache = adjacency
        return adjacency
    
    # ========== PRIORITY 1: HEALTH & QUALITY METRICS ==========
    
    def calculate_health_metrics(self) -> Dict[str, Any]:
        """Calculate health and quality metrics."""
        nodes, edges = self._load_graph_data()
        
        # Orphaned edges
        orphaned_edges = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_edges e
            WHERE e.user_id = ? AND e.is_current = 1
            AND (
                NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.source_id AND n.is_current = 1)
                OR NOT EXISTS (SELECT 1 FROM kg_nodes n WHERE n.id = e.target_id AND n.is_current = 1)
            )
        """, [self.user_id]).fetchone()[0]
        
        # Duplicate nodes (same label + name)
        duplicate_nodes = self.db.execute("""
            SELECT COUNT(*) FROM (
                SELECT label, json_extract(properties, '$.name') as name, COUNT(*) as cnt
                FROM kg_nodes
                WHERE user_id = ? AND is_current = 1
                GROUP BY label, json_extract(properties, '$.name')
                HAVING cnt > 1
            )
        """, [self.user_id]).fetchone()[0]
        
        # Stale nodes (not updated in 30+ days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        stale_nodes = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_nodes
            WHERE user_id = ? AND is_current = 1 AND updated_at < ?
        """, [self.user_id, thirty_days_ago]).fetchone()[0]
        
        total_current_nodes = sum(1 for n in nodes if n[9] == 1)  # is_current column
        stale_percent = (stale_nodes / total_current_nodes * 100) if total_current_nodes > 0 else 0
        
        # Property completeness
        total_properties = sum(
            len(json.loads(node[3])) if node[3] else 0  # properties column
            for node in nodes if node[9] == 1
        )
        avg_properties = total_properties / total_current_nodes if total_current_nodes > 0 else 0
        
        # Growth in last 24 hours
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        nodes_24h = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_nodes
            WHERE user_id = ? AND created_at >= ?
        """, [self.user_id, yesterday]).fetchone()[0]
        
        edges_24h = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_edges
            WHERE user_id = ? AND created_at >= ?
        """, [self.user_id, yesterday]).fetchone()[0]
        
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
    
    def calculate_structure_metrics(self) -> Dict[str, Any]:
        """Calculate graph structure and topology metrics."""
        nodes, edges = self._load_graph_data()
        adjacency = self._build_adjacency_list()
        
        current_nodes = [n for n in nodes if n[9] == 1]
        current_edges = [e for e in edges if e[10] == 1]
        
        n = len(current_nodes)
        m = len(current_edges)
        
        # Graph density: actual edges / possible edges
        max_edges = n * (n - 1) / 2 if n > 1 else 1
        density = m / max_edges if max_edges > 0 else 0
        
        # Degree statistics
        degrees = [len(adjacency[node[0]]) for node in current_nodes]
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
    
    def calculate_temporal_metrics(self) -> Dict[str, Any]:
        """Calculate temporal activity metrics."""
        # Growth rates
        now = datetime.now()
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        
        nodes_7d = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_nodes
            WHERE user_id = ? AND created_at >= ?
        """, [self.user_id, seven_days_ago]).fetchone()[0]
        
        nodes_30d = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_nodes
            WHERE user_id = ? AND created_at >= ?
        """, [self.user_id, thirty_days_ago]).fetchone()[0]
        
        total_nodes = self.db.execute("""
            SELECT COUNT(*)
            FROM kg_nodes
            WHERE user_id = ? AND is_current = 1
        """, [self.user_id]).fetchone()[0]
        
        growth_7d = (nodes_7d / total_nodes * 100) if total_nodes > 0 else 0
        growth_30d = (nodes_30d / total_nodes * 100) if total_nodes > 0 else 0
        
        # Activity by day (last 7 days)
        activity_by_day = {}
        for i in range(7):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            
            count = self.db.execute("""
                SELECT COUNT(*)
                FROM kg_nodes
                WHERE user_id = ? AND created_at >= ? AND created_at <= ?
            """, [self.user_id, day_start, day_end]).fetchone()[0]
            
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
    
    def calculate_centrality_metrics(self) -> Dict[str, Any]:
        """Calculate centrality and importance metrics."""
        nodes, edges = self._load_graph_data()
        adjacency = self._build_adjacency_list()
        
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
        
        from backend.api.kg.router import logger
        logger.info(f"Calculated degree centrality for {len(node_degrees)} nodes, top 10: {len(top_by_degree)}")
        
        # PageRank (simplified iterative algorithm)
        from backend.api.kg.router import logger
        logger.info(f"Calculating PageRank with {len(current_nodes)} nodes and {len(edges)} edges")
        pagerank = self._calculate_pagerank(current_nodes, edges)
        logger.info(f"PageRank calculated, got {len(pagerank)} results")
        top_by_pagerank = sorted(
            [{"id": k, "label": self._get_node_label(k, current_nodes), 
              "name": self._get_node_name(k, current_nodes), "score": v} 
             for k, v in pagerank.items()],
            key=lambda x: x["score"],
            reverse=True
        )[:10]
        logger.info(f"Top PageRank nodes: {len(top_by_pagerank)}")
        
        # Betweenness centrality (approximate for large graphs)
        betweenness = self._calculate_betweenness(current_nodes, adjacency)
        top_by_betweenness = sorted(
            [{"id": k, "label": self._get_node_label(k, current_nodes),
              "name": self._get_node_name(k, current_nodes), "score": v}
             for k, v in betweenness.items()],
            key=lambda x: x["score"],
            reverse=True
        )[:10]
        
        from backend.api.kg.router import logger
        logger.info(f"Calculated betweenness centrality, top 10: {len(top_by_betweenness)}")
        
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
        
        if self._logger:
            self._logger.info(f"Detected {len(duplicate_pairs)} duplicate pairs for user {self.user_id}")
        
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
        
        from backend.api.kg.router import logger
        logger.info(f"Calculating PageRank for {n} nodes")
        
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
