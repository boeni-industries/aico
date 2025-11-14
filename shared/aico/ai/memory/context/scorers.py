"""
Context Scoring and Ranking

Handles relevance scoring, tier weighting, and context prioritization.
Enhanced with temporal intelligence for AMS Phase 1.
"""

from typing import List
from datetime import datetime, timedelta
import math

from aico.core.logging import get_logger

from .models import ContextItem

logger = get_logger("ai", "memory.context.scorers")


class ContextScorer:
    """
    Scores and ranks context items based on relevance, recency, and tier weights.
    """
    
    def __init__(self, tier_weights: dict = None, relevance_threshold: float = 0.3, temporal_enabled: bool = True):
        """
        Initialize context scorer.
        
        Args:
            tier_weights: Weight for each memory tier
            relevance_threshold: Minimum relevance score to include
            temporal_enabled: Enable temporal/recency weighting (AMS Phase 1)
        """
        self.tier_weights = tier_weights or {
            "working": 1.0,
            "semantic": 0.7,
            "behavioral": 0.6
        }
        self.relevance_threshold = relevance_threshold
        self.temporal_enabled = temporal_enabled
        
        # Temporal decay parameters (AMS Phase 1)
        self.recency_half_life_hours = 168.0  # 7 days - half relevance after 1 week
        self.recency_weight = 0.3  # 30% weight for recency in final score
    
    def calculate_recency_factor(self, timestamp: datetime) -> float:
        """
        Calculate exponential recency decay factor.
        
        Uses exponential decay: factor = 0.5^(hours_ago / half_life)
        
        Args:
            timestamp: Item timestamp
            
        Returns:
            Recency factor (0-1, where 1 is most recent)
        """
        now = datetime.utcnow()
        hours_ago = (now - timestamp).total_seconds() / 3600.0
        
        # Exponential decay with configurable half-life
        decay_factor = math.pow(0.5, hours_ago / self.recency_half_life_hours)
        
        return min(1.0, decay_factor)  # Cap at 1.0 for future timestamps
    
    def score_and_rank(
        self,
        items: List[ContextItem],
        max_items: int = 50
    ) -> List[ContextItem]:
        """
        Score and rank context items with temporal intelligence.
        
        Args:
            items: List of context items
            max_items: Maximum items to return
            
        Returns:
            Ranked list of context items
        """
        if not items:
            return []
        
        # Apply tier weights and temporal scoring
        for item in items:
            # Base tier weight
            tier_weight = self.tier_weights.get(item.source_tier, 0.5)
            base_score = item.relevance_score * tier_weight
            
            # Apply temporal recency weighting if enabled
            if self.temporal_enabled:
                recency_factor = self.calculate_recency_factor(item.timestamp)
                # Blend base score with recency: 70% base + 30% recency
                item.relevance_score = (base_score * (1 - self.recency_weight)) + (recency_factor * self.recency_weight)
            else:
                item.relevance_score = base_score
        
        # Filter by threshold
        items = [item for item in items if item.relevance_score >= self.relevance_threshold]
        
        # Sort by final relevance score (descending)
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
