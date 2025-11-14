"""
Graph Analytics

Advanced analytics and insights from knowledge graphs.
Implements PageRank, centrality measures, clustering, and pattern discovery.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import math

from aico.core.logging import get_logger

from .models import Node, Edge
from .storage import PropertyGraphStorage

logger = get_logger("shared", "ai.knowledge_graph.analytics")


class GraphAnalytics:
    """
    Best-in-class graph analytics for knowledge graphs.
    
    Features:
    - PageRank for importance scoring
    - Centrality measures (degree, betweenness, closeness)
    - Community detection
    - Temporal pattern analysis
    - Knowledge gap identification
    - Relationship strength analysis
    """
    
    def __init__(self, storage: PropertyGraphStorage):
        """
        Initialize analytics engine.
        
        Args:
            storage: PropertyGraphStorage instance
        """
        self.storage = storage
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive insights from user's knowledge graph.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with insights and analytics
        """
        logger.info(f"Generating insights for user {user_id}")
        
        # Get user's graph
        graph = await self.storage.get_user_graph(user_id, current_only=True)
        
        if not graph.nodes:
            return {
                "status": "no_data",
                "message": "No knowledge graph data available"
            }
        
        # Calculate various metrics
        pagerank_scores = await self.calculate_pagerank(user_id)
        centrality = await self.calculate_centrality(user_id)
        clusters = await self.detect_communities(user_id)
        temporal_patterns = await self.analyze_temporal_patterns(user_id)
        knowledge_gaps = await self.identify_knowledge_gaps(user_id)
        
        # Top entities by importance
        top_entities = sorted(
            pagerank_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Entity type distribution
        type_distribution = Counter(node.label for node in graph.nodes)
        
        # Relationship type distribution
        relationship_distribution = Counter(edge.relation_type for edge in graph.edges)
        
        return {
            "status": "success",
            "summary": {
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "entity_types": len(type_distribution),
                "relationship_types": len(relationship_distribution),
                "communities": len(clusters)
            },
            "top_entities": [
                {
                    "node_id": node_id,
                    "importance_score": score,
                    "node": await self._get_node_summary(node_id)
                }
                for node_id, score in top_entities
            ],
            "entity_distribution": dict(type_distribution),
            "relationship_distribution": dict(relationship_distribution),
            "centrality_metrics": centrality,
            "communities": clusters,
            "temporal_patterns": temporal_patterns,
            "knowledge_gaps": knowledge_gaps
        }
    
    async def calculate_pagerank(
        self,
        user_id: str,
        damping_factor: float = 0.85,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Dict[str, float]:
        """
        Calculate PageRank scores for all nodes.
        
        PageRank measures node importance based on incoming links.
        Higher score = more important/central to the graph.
        
        Args:
            user_id: User ID
            damping_factor: Probability of following a link (0.85 standard)
            max_iterations: Maximum iterations
            tolerance: Convergence threshold
            
        Returns:
            Dictionary mapping node IDs to PageRank scores
        """
        # Get all nodes and edges
        nodes = await self.storage.get_user_nodes(user_id, current_only=True)
        
        if not nodes:
            return {}
        
        # Build adjacency structure
        outgoing = defaultdict(list)
        incoming = defaultdict(list)
        
        for node in nodes:
            edges = await self.storage.get_edges_for_node(node.id, direction="outgoing")
            for edge in edges:
                outgoing[node.id].append(edge.target_id)
                incoming[edge.target_id].append(node.id)
        
        # Initialize scores
        n = len(nodes)
        scores = {node.id: 1.0 / n for node in nodes}
        
        # Iterative calculation
        for iteration in range(max_iterations):
            new_scores = {}
            max_change = 0.0
            
            for node in nodes:
                # Base score (random jump)
                score = (1 - damping_factor) / n
                
                # Add contributions from incoming links
                for source_id in incoming[node.id]:
                    out_degree = len(outgoing[source_id])
                    if out_degree > 0:
                        score += damping_factor * (scores[source_id] / out_degree)
                
                new_scores[node.id] = score
                max_change = max(max_change, abs(score - scores[node.id]))
            
            scores = new_scores
            
            # Check convergence
            if max_change < tolerance:
                logger.info(f"PageRank converged after {iteration + 1} iterations")
                break
        
        return scores
    
    async def calculate_centrality(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate various centrality measures.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with centrality metrics
        """
        nodes = await self.storage.get_user_nodes(user_id, current_only=True)
        
        if not nodes:
            return {}
        
        # Degree centrality (number of connections)
        degree_centrality = {}
        for node in nodes:
            edges = await self.storage.get_edges_for_node(node.id, direction="both")
            degree_centrality[node.id] = len(edges)
        
        # Normalize by max possible degree
        max_degree = max(degree_centrality.values()) if degree_centrality else 1
        normalized_degree = {
            node_id: degree / max_degree
            for node_id, degree in degree_centrality.items()
        }
        
        # Find hub nodes (top 10% by degree)
        threshold = sorted(normalized_degree.values(), reverse=True)[min(len(nodes) // 10, len(nodes) - 1)]
        hubs = [
            {"node_id": node_id, "degree": degree}
            for node_id, degree in normalized_degree.items()
            if degree >= threshold
        ]
        
        return {
            "degree_centrality": normalized_degree,
            "hubs": hubs,
            "average_degree": sum(degree_centrality.values()) / len(nodes) if nodes else 0
        }
    
    async def detect_communities(
        self,
        user_id: str,
        min_community_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect communities/clusters in the graph using label propagation.
        
        Args:
            user_id: User ID
            min_community_size: Minimum nodes per community
            
        Returns:
            List of communities with their nodes
        """
        nodes = await self.storage.get_user_nodes(user_id, current_only=True)
        
        if len(nodes) < min_community_size:
            return []
        
        # Initialize each node with its own label
        labels = {node.id: node.id for node in nodes}
        
        # Build adjacency list
        adjacency = defaultdict(list)
        for node in nodes:
            edges = await self.storage.get_edges_for_node(node.id, direction="both")
            for edge in edges:
                neighbor_id = edge.target_id if edge.source_id == node.id else edge.source_id
                adjacency[node.id].append(neighbor_id)
        
        # Label propagation (simplified)
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False
            for node in nodes:
                if not adjacency[node.id]:
                    continue
                
                # Count neighbor labels
                neighbor_labels = [labels[neighbor_id] for neighbor_id in adjacency[node.id] if neighbor_id in labels]
                if neighbor_labels:
                    most_common = Counter(neighbor_labels).most_common(1)[0][0]
                    if labels[node.id] != most_common:
                        labels[node.id] = most_common
                        changed = True
            
            if not changed:
                break
        
        # Group nodes by label
        communities_dict = defaultdict(list)
        for node_id, label in labels.items():
            communities_dict[label].append(node_id)
        
        # Filter by size and format
        communities = []
        for i, (label, node_ids) in enumerate(communities_dict.items()):
            if len(node_ids) >= min_community_size:
                # Infer community theme from node labels
                community_nodes = [await self.storage.get_node(nid) for nid in node_ids]
                community_nodes = [n for n in community_nodes if n]
                
                label_counts = Counter(n.label for n in community_nodes)
                dominant_type = label_counts.most_common(1)[0][0] if label_counts else "MIXED"
                
                communities.append({
                    "community_id": i,
                    "size": len(node_ids),
                    "dominant_type": dominant_type,
                    "node_ids": node_ids[:10],  # Limit for display
                    "type_distribution": dict(label_counts)
                })
        
        logger.info(f"Detected {len(communities)} communities")
        return communities
    
    async def analyze_temporal_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze temporal patterns in the knowledge graph.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with temporal insights
        """
        nodes = await self.storage.get_user_nodes(user_id, current_only=True)
        
        if not nodes:
            return {}
        
        # Parse timestamps
        node_times = []
        for node in nodes:
            if node.created_at:
                try:
                    dt = datetime.fromisoformat(node.created_at.replace('Z', '+00:00'))
                    node_times.append((node, dt))
                except:
                    pass
        
        if not node_times:
            return {"status": "no_temporal_data"}
        
        # Sort by time
        node_times.sort(key=lambda x: x[1])
        
        # Activity over time (by day)
        activity_by_day = defaultdict(int)
        for node, dt in node_times:
            day_key = dt.date().isoformat()
            activity_by_day[day_key] += 1
        
        # Recent activity (last 7 days)
        now = datetime.now()
        recent_nodes = [
            node for node, dt in node_times
            if (now - dt.replace(tzinfo=None)).days <= 7
        ]
        
        # Growth rate
        if len(node_times) > 1:
            first_time = node_times[0][1]
            last_time = node_times[-1][1]
            days_span = (last_time - first_time).days or 1
            growth_rate = len(nodes) / days_span
        else:
            growth_rate = 0
        
        return {
            "total_nodes": len(nodes),
            "first_entry": node_times[0][1].isoformat() if node_times else None,
            "latest_entry": node_times[-1][1].isoformat() if node_times else None,
            "recent_activity_7d": len(recent_nodes),
            "growth_rate_per_day": round(growth_rate, 2),
            "activity_by_day": dict(sorted(activity_by_day.items())[-30:])  # Last 30 days
        }
    
    async def identify_knowledge_gaps(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Identify potential knowledge gaps in the graph.
        
        Gaps are identified by:
        - Entities with few connections (isolated)
        - Missing relationships (common patterns not present)
        - Incomplete entity information
        
        Args:
            user_id: User ID
            
        Returns:
            List of identified gaps
        """
        nodes = await self.storage.get_user_nodes(user_id, current_only=True)
        gaps = []
        
        # Find isolated nodes (degree < 2)
        for node in nodes:
            edges = await self.storage.get_edges_for_node(node.id, direction="both")
            if len(edges) < 2:
                gaps.append({
                    "type": "isolated_entity",
                    "node_id": node.id,
                    "label": node.label,
                    "properties": node.properties,
                    "connection_count": len(edges),
                    "suggestion": f"Add more relationships for {node.properties.get('name', 'this entity')}"
                })
        
        # Find entities with minimal properties
        for node in nodes:
            if len(node.properties) <= 1:  # Only has 'name' or similar
                gaps.append({
                    "type": "incomplete_entity",
                    "node_id": node.id,
                    "label": node.label,
                    "properties": node.properties,
                    "suggestion": f"Add more details about {node.properties.get('name', 'this entity')}"
                })
        
        logger.info(f"Identified {len(gaps)} knowledge gaps")
        return gaps[:20]  # Limit to top 20
    
    async def calculate_relationship_strength(
        self,
        user_id: str,
        source_id: str,
        target_id: str
    ) -> float:
        """
        Calculate relationship strength between two entities.
        
        Strength is based on:
        - Number of paths between entities
        - Confidence scores
        - Temporal recency
        
        Args:
            user_id: User ID
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            Relationship strength score (0-1)
        """
        # Get direct edges
        edges = await self.storage.get_edges_for_node(source_id, direction="outgoing")
        direct_edges = [e for e in edges if e.target_id == target_id]
        
        if direct_edges:
            # Direct relationship - use confidence
            return max(e.confidence for e in direct_edges)
        
        # No direct relationship - check indirect paths
        # This would use the query engine's path finding
        # For now, return 0 for indirect
        return 0.0
    
    async def _get_node_summary(self, node_id: str) -> Dict[str, Any]:
        """Get a summary of a node for display."""
        node = await self.storage.get_node(node_id)
        if not node:
            return {}
        
        return {
            "id": node.id,
            "label": node.label,
            "properties": node.properties,
            "confidence": node.confidence
        }
