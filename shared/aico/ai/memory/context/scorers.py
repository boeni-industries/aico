"""
Context Scoring and Ranking

Handles relevance scoring, tier weighting, and context prioritization.
"""

from typing import List
from datetime import datetime

from aico.core.logging import get_logger

from .models import ContextItem

logger = get_logger("ai", "memory.context.scorers")


class ContextScorer:
    """
    Scores and ranks context items based on relevance, recency, and tier weights.
    """
    
    def __init__(self, tier_weights: dict = None, relevance_threshold: float = 0.3):
        """
        Initialize context scorer.
        
        Args:
            tier_weights: Weight for each memory tier
            relevance_threshold: Minimum relevance score to include
        """
        self.tier_weights = tier_weights or {
            "working": 1.0,
            "semantic": 0.7,
            "procedural": 0.6
        }
        self.relevance_threshold = relevance_threshold
    
    def score_and_rank(
        self,
        items: List[ContextItem],
        max_items: int = 50
    ) -> List[ContextItem]:
        """
        Score and rank context items.
        
        Args:
            items: List of context items
            max_items: Maximum items to return
            
        Returns:
            Ranked list of context items
        """
        if not items:
            return []
        
        # Apply tier weights
        for item in items:
            tier_weight = self.tier_weights.get(item.source_tier, 0.5)
            item.relevance_score *= tier_weight
        
        # Filter by threshold
        items = [item for item in items if item.relevance_score >= self.relevance_threshold]
        
        # Sort by relevance (descending)
        items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to max items
        return items[:max_items]
    
    def calculate_conversation_strength(self, items: List[ContextItem]) -> float:
        """
        Calculate conversation context strength.
        
        Args:
            items: Context items
            
        Returns:
            Strength score (0-1)
        """
        if not items:
            return 0.0
        
        # Calculate average relevance score
        avg_relevance = sum(item.relevance_score for item in items) / len(items)
        
        # Calculate recency factor based on most recent item
        now = datetime.utcnow()
        most_recent = max(items, key=lambda x: x.timestamp)
        time_diff = now - most_recent.timestamp
        recency_hours = time_diff.total_seconds() / 3600
        recency_factor = max(0.1, 1.0 - (recency_hours / 48.0))  # Decay over 48 hours
        
        # Calculate item density factor (more items = stronger context)
        density_factor = min(1.0, len(items) / 10.0)  # Normalize to 10 items
        
        # Combine factors for conversation strength
        conversation_strength = (avg_relevance * 0.5) + (recency_factor * 0.3) + (density_factor * 0.2)
        
        return round(min(1.0, conversation_strength), 3)
