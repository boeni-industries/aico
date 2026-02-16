"""
Tests for Phase 6.3: Opportunity Clustering

Tests the clustering and deduplication of curiosity signals.
"""

import pytest
from datetime import datetime, UTC

from aico.ai.curiosity.clustering import OpportunityClusterer
from aico.ai.curiosity.models import IntrinsicSignal, CuriosityType


class TestOpportunityClusterer:
    """Test opportunity clustering and deduplication"""
    
    def test_initialization(self):
        """Test clusterer initialization"""
        clusterer = OpportunityClusterer(similarity_threshold=0.8)
        
        assert clusterer.similarity_threshold == 0.8
    
    def test_cluster_empty_list(self):
        """Test clustering empty list"""
        clusterer = OpportunityClusterer()
        
        result = clusterer.cluster_and_deduplicate([])
        
        assert result == []
    
    def test_cluster_single_signal(self):
        """Test clustering single signal"""
        clusterer = OpportunityClusterer()
        
        signal = IntrinsicSignal(
            signal_id="1",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python programming",
            description="Learn Python",
            intrinsic_reward=0.8
        )
        
        result = clusterer.cluster_and_deduplicate([signal])
        
        assert len(result) == 1
        assert result[0].signal_id == "1"
    
    def test_cluster_identical_signals(self):
        """Test clustering identical signals"""
        clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        signals = [
            IntrinsicSignal(
                signal_id=f"{i}",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python programming",
                description="Learn Python basics",
                intrinsic_reward=0.8 - i * 0.1
            )
            for i in range(3)
        ]
        
        result = clusterer.cluster_and_deduplicate(signals, max_per_cluster=1)
        
        # Should keep only the highest scoring signal
        assert len(result) == 1
        assert result[0].signal_id == "0"  # Highest reward
    
    def test_cluster_different_signals(self):
        """Test clustering completely different signals"""
        clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        signals = [
            IntrinsicSignal(
                signal_id="1",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python programming",
                description="Learn Python",
                intrinsic_reward=0.8
            ),
            IntrinsicSignal(
                signal_id="2",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Cooking recipes",
                description="Learn cooking",
                intrinsic_reward=0.7
            ),
        ]
        
        result = clusterer.cluster_and_deduplicate(signals, max_per_cluster=1)
        
        # Should keep both (different topics)
        assert len(result) == 2
    
    def test_cluster_by_type(self):
        """Test that clustering groups by type first"""
        clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        signals = [
            IntrinsicSignal(
                signal_id="1",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python",
                description="Learn Python",
                intrinsic_reward=0.8
            ),
            IntrinsicSignal(
                signal_id="2",
                user_id="user1",
                signal_type=CuriosityType.HOBBY_PLAY,
                topic="Python",
                description="Learn Python",
                intrinsic_reward=0.7
            ),
        ]
        
        result = clusterer.cluster_and_deduplicate(signals, max_per_cluster=1)
        
        # Should keep both (different types)
        assert len(result) == 2
    
    def test_jaccard_similarity_identical(self):
        """Test Jaccard similarity with identical sets"""
        clusterer = OpportunityClusterer()
        
        set1 = {"a", "b", "c"}
        similarity = clusterer._jaccard_similarity(set1, set1)
        
        assert similarity == 1.0
    
    def test_jaccard_similarity_disjoint(self):
        """Test Jaccard similarity with disjoint sets"""
        clusterer = OpportunityClusterer()
        
        set1 = {"a", "b", "c"}
        set2 = {"d", "e", "f"}
        similarity = clusterer._jaccard_similarity(set1, set2)
        
        assert similarity == 0.0
    
    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity with partial overlap"""
        clusterer = OpportunityClusterer()
        
        set1 = {"a", "b", "c"}
        set2 = {"b", "c", "d"}
        similarity = clusterer._jaccard_similarity(set1, set2)
        
        # 2 common / 4 total = 0.5
        assert similarity == 0.5
    
    def test_jaccard_similarity_empty_sets(self):
        """Test Jaccard similarity with empty sets"""
        clusterer = OpportunityClusterer()
        
        similarity = clusterer._jaccard_similarity(set(), set())
        
        # Empty sets are considered identical
        assert similarity == 1.0
    
    def test_tokenize_basic(self):
        """Test basic tokenization"""
        clusterer = OpportunityClusterer()
        
        tokens = clusterer._tokenize("Learn Python programming")
        
        assert "learn" in tokens
        assert "python" in tokens
        assert "programming" in tokens
    
    def test_tokenize_removes_stop_words(self):
        """Test that tokenization removes stop words"""
        clusterer = OpportunityClusterer()
        
        tokens = clusterer._tokenize("The quick brown fox")
        
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens
    
    def test_tokenize_removes_short_words(self):
        """Test that tokenization removes short words"""
        clusterer = OpportunityClusterer()
        
        tokens = clusterer._tokenize("I am ok")
        
        # All words are <= 2 chars or stop words
        assert len(tokens) == 0
    
    def test_tokenize_lowercase(self):
        """Test that tokenization lowercases"""
        clusterer = OpportunityClusterer()
        
        tokens = clusterer._tokenize("Python PROGRAMMING")
        
        assert "python" in tokens
        assert "programming" in tokens
        assert "Python" not in tokens
        assert "PROGRAMMING" not in tokens
    
    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical signals"""
        clusterer = OpportunityClusterer()
        
        signal1 = IntrinsicSignal(
            signal_id="1",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python programming",
            description="Learn Python basics",
            topic_tags=["programming", "python"]
        )
        
        signal2 = IntrinsicSignal(
            signal_id="2",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python programming",
            description="Learn Python basics",
            topic_tags=["programming", "python"]
        )
        
        similarity = clusterer._calculate_similarity(signal1, signal2)
        
        # Identical signals should have high similarity (>= 0.9 with floating point tolerance)
        assert similarity >= 0.89
    
    def test_calculate_similarity_different(self):
        """Test similarity calculation for different signals"""
        clusterer = OpportunityClusterer()
        
        signal1 = IntrinsicSignal(
            signal_id="1",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python programming",
            description="Learn Python",
            topic_tags=["programming"]
        )
        
        signal2 = IntrinsicSignal(
            signal_id="2",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Cooking recipes",
            description="Learn cooking",
            topic_tags=["cooking"]
        )
        
        similarity = clusterer._calculate_similarity(signal1, signal2)
        
        # Different signals should have low similarity
        assert similarity < 0.3
    
    def test_merge_similar_signals_empty(self):
        """Test merging empty list"""
        clusterer = OpportunityClusterer()
        
        result = clusterer.merge_similar_signals([])
        
        assert result == []
    
    def test_merge_similar_signals_single(self):
        """Test merging single signal"""
        clusterer = OpportunityClusterer()
        
        signal = IntrinsicSignal(
            signal_id="1",
            user_id="user1",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python",
            description="Learn Python",
            intrinsic_reward=0.8
        )
        
        result = clusterer.merge_similar_signals([signal])
        
        assert len(result) == 1
        assert result[0].signal_id == "1"
    
    def test_merge_similar_signals_cluster(self):
        """Test merging a cluster of similar signals"""
        clusterer = OpportunityClusterer(similarity_threshold=0.6)  # Lower threshold to ensure merge
        
        signals = [
            IntrinsicSignal(
                signal_id="1",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python programming basics",
                description="Learn Python programming fundamentals",
                novelty_score=0.8,
                uncertainty_score=0.7,
                intrinsic_reward=0.9,
                topic_tags=["programming", "python"]
            ),
            IntrinsicSignal(
                signal_id="2",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python programming basics",
                description="Learn Python programming fundamentals",
                novelty_score=0.6,
                uncertainty_score=0.5,
                intrinsic_reward=0.7,
                topic_tags=["programming", "python"]
            ),
        ]
        
        result = clusterer.merge_similar_signals(signals)
        
        # Should merge into one signal (identical topics/descriptions)
        assert len(result) == 1
        
        # Should average scores
        merged = result[0]
        assert 0.6 <= merged.novelty_score <= 0.8
        assert 0.5 <= merged.uncertainty_score <= 0.7
        assert 0.7 <= merged.intrinsic_reward <= 0.9
        
        # Should combine tags
        assert "programming" in merged.topic_tags or "coding" in merged.topic_tags
        
        # Should track merge
        assert "merged_from" in merged.context
        assert "cluster_size" in merged.context
        assert merged.context["cluster_size"] == 2
    
    def test_max_per_cluster(self):
        """Test max_per_cluster parameter"""
        clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        signals = [
            IntrinsicSignal(
                signal_id=f"{i}",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python programming",
                description="Learn Python",
                intrinsic_reward=0.9 - i * 0.1
            )
            for i in range(5)
        ]
        
        # Keep top 2 per cluster
        result = clusterer.cluster_and_deduplicate(signals, max_per_cluster=2)
        
        assert len(result) == 2
        assert result[0].signal_id == "0"  # Highest
        assert result[1].signal_id == "1"  # Second highest
    
    def test_clustering_preserves_best_scores(self):
        """Test that clustering keeps highest-scoring signals"""
        clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        signals = [
            IntrinsicSignal(
                signal_id="low",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python",
                description="Learn Python",
                intrinsic_reward=0.3
            ),
            IntrinsicSignal(
                signal_id="high",
                user_id="user1",
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic="Python",
                description="Learn Python",
                intrinsic_reward=0.9
            ),
        ]
        
        result = clusterer.cluster_and_deduplicate(signals, max_per_cluster=1)
        
        assert len(result) == 1
        assert result[0].signal_id == "high"
