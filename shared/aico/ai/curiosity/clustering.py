"""
Opportunity Clustering and Deduplication

Groups similar curiosity signals and removes duplicates to avoid redundant exploration.

Phase 6.3: Advanced Curiosity Scoring
"""

from typing import List, Set, Dict, Any
from collections import defaultdict
import re

from .models import IntrinsicSignal, CuriosityType


class OpportunityClusterer:
    """Clusters and deduplicates curiosity signals"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize clusterer.
        
        Args:
            similarity_threshold: Minimum similarity to consider signals as duplicates (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
    
    def cluster_and_deduplicate(
        self,
        signals: List[IntrinsicSignal],
        max_per_cluster: int = 1
    ) -> List[IntrinsicSignal]:
        """Cluster similar signals and keep only the best from each cluster.
        
        Args:
            signals: List of intrinsic signals to cluster
            max_per_cluster: Maximum signals to keep per cluster
            
        Returns:
            Deduplicated list of signals
        """
        if not signals:
            return []
        
        # Group signals by type first
        by_type: Dict[CuriosityType, List[IntrinsicSignal]] = defaultdict(list)
        for signal in signals:
            by_type[signal.signal_type].append(signal)
        
        # Cluster and deduplicate within each type
        deduplicated = []
        for signal_type, type_signals in by_type.items():
            clusters = self._cluster_signals(type_signals)
            
            # Keep top N from each cluster
            for cluster in clusters:
                # Sort by intrinsic_reward descending
                cluster.sort(key=lambda s: s.intrinsic_reward, reverse=True)
                deduplicated.extend(cluster[:max_per_cluster])
        
        return deduplicated
    
    def _cluster_signals(self, signals: List[IntrinsicSignal]) -> List[List[IntrinsicSignal]]:
        """Cluster signals using topic similarity.
        
        Args:
            signals: Signals to cluster
            
        Returns:
            List of clusters (each cluster is a list of signals)
        """
        if not signals:
            return []
        
        clusters: List[List[IntrinsicSignal]] = []
        assigned: Set[str] = set()
        
        for signal in signals:
            if signal.signal_id in assigned:
                continue
            
            # Start new cluster with this signal
            cluster = [signal]
            assigned.add(signal.signal_id)
            
            # Find similar signals
            for other in signals:
                if other.signal_id in assigned:
                    continue
                
                similarity = self._calculate_similarity(signal, other)
                if similarity >= self.similarity_threshold:
                    cluster.append(other)
                    assigned.add(other.signal_id)
            
            clusters.append(cluster)
        
        return clusters
    
    def _calculate_similarity(
        self,
        signal1: IntrinsicSignal,
        signal2: IntrinsicSignal
    ) -> float:
        """Calculate similarity between two signals.
        
        Args:
            signal1: First signal
            signal2: Second signal
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Topic similarity (Jaccard on words)
        topic_sim = self._jaccard_similarity(
            self._tokenize(signal1.topic),
            self._tokenize(signal2.topic)
        )
        
        # Description similarity
        desc_sim = self._jaccard_similarity(
            self._tokenize(signal1.description),
            self._tokenize(signal2.description)
        )
        
        # Tag overlap
        tag_sim = self._jaccard_similarity(
            set(signal1.topic_tags),
            set(signal2.topic_tags)
        ) if signal1.topic_tags and signal2.topic_tags else 0.0
        
        # Context similarity (check for common keys)
        context_sim = self._jaccard_similarity(
            set(signal1.context.keys()),
            set(signal2.context.keys())
        ) if signal1.context and signal2.context else 0.0
        
        # Weighted combination
        similarity = (
            topic_sim * 0.4 +      # Topic is most important
            desc_sim * 0.3 +       # Description second
            tag_sim * 0.2 +        # Tags third
            context_sim * 0.1      # Context least important
        )
        
        return similarity
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets.
        
        Args:
            set1: First set
            set2: Second set
            
        Returns:
            Jaccard similarity (0.0-1.0)
        """
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize(self, text: str) -> Set[str]:
        """Tokenize text into normalized words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            Set of normalized tokens
        """
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\w+', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        return {t for t in tokens if t not in stop_words and len(t) > 2}
    
    def merge_similar_signals(
        self,
        signals: List[IntrinsicSignal]
    ) -> List[IntrinsicSignal]:
        """Merge very similar signals into single signals with combined scores.
        
        Args:
            signals: Signals to merge
            
        Returns:
            List of merged signals
        """
        if not signals:
            return []
        
        clusters = self._cluster_signals(signals)
        merged = []
        
        for cluster in clusters:
            if len(cluster) == 1:
                merged.append(cluster[0])
            else:
                # Merge cluster into single signal
                merged_signal = self._merge_cluster(cluster)
                merged.append(merged_signal)
        
        return merged
    
    def _merge_cluster(self, cluster: List[IntrinsicSignal]) -> IntrinsicSignal:
        """Merge a cluster of signals into one signal.
        
        Args:
            cluster: Signals to merge
            
        Returns:
            Merged signal with combined scores
        """
        # Use the highest-scoring signal as base
        cluster.sort(key=lambda s: s.intrinsic_reward, reverse=True)
        base = cluster[0]
        
        # Average the scores
        n = len(cluster)
        
        base.novelty_score = sum(s.novelty_score for s in cluster) / n
        base.uncertainty_score = sum(s.uncertainty_score for s in cluster) / n
        base.user_relevance_score = sum(s.user_relevance_score for s in cluster) / n
        base.feasibility_score = sum(s.feasibility_score for s in cluster) / n
        base.cost_estimate = sum(s.cost_estimate for s in cluster) / n
        
        base.prediction_error = sum(s.prediction_error for s in cluster) / n
        base.information_gain = sum(s.information_gain for s in cluster) / n
        base.empowerment = sum(s.empowerment for s in cluster) / n
        base.long_term_value = sum(s.long_term_value for s in cluster) / n
        
        base.total_score = sum(s.total_score for s in cluster) / n
        base.intrinsic_reward = sum(s.intrinsic_reward for s in cluster) / n
        
        # Combine topic tags
        all_tags = set()
        for signal in cluster:
            all_tags.update(signal.topic_tags)
        base.topic_tags = list(all_tags)
        
        # Add note about merge in context
        base.context["merged_from"] = [s.signal_id for s in cluster[1:]]
        base.context["cluster_size"] = n
        
        return base
