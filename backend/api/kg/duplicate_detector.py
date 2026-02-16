"""
Duplicate Node Detection for Knowledge Graph

Detects potential duplicate nodes using semantic similarity.
"""

from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate nodes in knowledge graph using semantic similarity."""
    
    def __init__(self, similarity_threshold: float = 0.80):
        """
        Initialize duplicate detector.
        
        Args:
            similarity_threshold: Minimum similarity score to consider nodes as duplicates (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def detect_duplicates(self, nodes: List[Dict]) -> List[Dict]:
        """
        Detect duplicate node pairs.
        
        Args:
            nodes: List of node dictionaries with 'id', 'label', and 'properties'
        
        Returns:
            List of duplicate pairs with similarity scores
        """
        duplicate_pairs = []
        
        # Group nodes by label for efficient comparison
        nodes_by_label = defaultdict(list)
        for node in nodes:
            label = node.get('label', 'UNKNOWN')
            nodes_by_label[label].append(node)
        
        # Compare nodes within each label group
        for label, label_nodes in nodes_by_label.items():
            if len(label_nodes) < 2:
                continue
            
            # Compare each pair of nodes
            for i in range(len(label_nodes)):
                for j in range(i + 1, len(label_nodes)):
                    node1 = label_nodes[i]
                    node2 = label_nodes[j]
                    
                    # Calculate similarity
                    similarity = self._calculate_similarity(node1, node2)
                    
                    if similarity >= self.similarity_threshold:
                        # Extract name from properties or use label
                        name1 = self._get_node_name(node1)
                        name2 = self._get_node_name(node2)
                        
                        duplicate_pairs.append({
                            'id1': node1['id'],
                            'name1': name1,
                            'label1': label,
                            'id2': node2['id'],
                            'name2': name2,
                            'label2': label,
                            'similarity': similarity
                        })
        
        # Sort by similarity (highest first)
        duplicate_pairs.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicate_pairs
    
    def _get_node_name(self, node: Dict) -> str:
        """Extract display name from node."""
        properties = node.get('properties', {})
        if isinstance(properties, str):
            try:
                import json
                properties = json.loads(properties)
            except:
                properties = {}
        
        # Try common name fields
        for field in ['name', 'title', 'label', 'value']:
            if field in properties:
                return str(properties[field])
        
        # Fallback to node label
        return node.get('label', 'Unknown')
    
    def _calculate_similarity(self, node1: Dict, node2: Dict) -> float:
        """
        Calculate similarity between two nodes.
        
        Uses multiple signals:
        - String similarity of names
        - Property overlap
        - Alias matching
        
        Returns:
            Similarity score between 0 and 1
        """
        name1 = self._get_node_name(node1).lower()
        name2 = self._get_node_name(node2).lower()
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Check if one is substring of other (e.g., "Alice J." vs "Alice Johnson")
        if name1 in name2 or name2 in name1:
            return 0.95
        
        # Check for common abbreviations
        if self._is_abbreviation(name1, name2):
            return 0.90
        
        # Calculate Levenshtein-based similarity
        string_sim = self._string_similarity(name1, name2)
        
        # Check property overlap
        props1 = node1.get('properties', {})
        props2 = node2.get('properties', {})
        if isinstance(props1, str):
            try:
                import json
                props1 = json.loads(props1)
            except:
                props1 = {}
        if isinstance(props2, str):
            try:
                import json
                props2 = json.loads(props2)
            except:
                props2 = {}
        
        property_sim = self._property_similarity(props1, props2)
        
        # Weighted combination
        return (string_sim * 0.7) + (property_sim * 0.3)
    
    def _is_abbreviation(self, str1: str, str2: str) -> bool:
        """Check if one string is an abbreviation of the other."""
        # Split into words
        words1 = str1.split()
        words2 = str2.split()
        
        # Check if shorter string matches initials of longer
        if len(words1) == 1 and len(words2) > 1:
            # Check if str1 is initials of str2
            initials = ''.join([w[0] for w in words2 if w])
            if str1.replace('.', '').replace(' ', '').lower() == initials.lower():
                return True
        
        if len(words2) == 1 and len(words1) > 1:
            # Check if str2 is initials of str1
            initials = ''.join([w[0] for w in words1 if w])
            if str2.replace('.', '').replace(' ', '').lower() == initials.lower():
                return True
        
        return False
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using Levenshtein distance."""
        if not str1 or not str2:
            return 0.0
        
        # Simple Levenshtein distance
        len1, len2 = len(str1), len(str2)
        if len1 > len2:
            str1, str2 = str2, str1
            len1, len2 = len2, len1
        
        current_row = range(len1 + 1)
        for i in range(1, len2 + 1):
            previous_row, current_row = current_row, [i] + [0] * len1
            for j in range(1, len1 + 1):
                add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
                if str1[j - 1] != str2[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)
        
        distance = current_row[len1]
        max_len = max(len(str1), len(str2))
        
        return 1.0 - (distance / max_len) if max_len > 0 else 0.0
    
    def _property_similarity(self, props1: Dict, props2: Dict) -> float:
        """Calculate similarity based on property overlap."""
        if not props1 or not props2:
            return 0.0
        
        # Get common keys
        keys1 = set(props1.keys())
        keys2 = set(props2.keys())
        common_keys = keys1 & keys2
        
        if not common_keys:
            return 0.0
        
        # Calculate value similarity for common keys
        matches = 0
        for key in common_keys:
            val1 = str(props1[key]).lower()
            val2 = str(props2[key]).lower()
            if val1 == val2:
                matches += 1
        
        return matches / len(common_keys) if common_keys else 0.0
