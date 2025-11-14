"""
Experience Replay

Generates prioritized replay sequences from working memory for consolidation.
Implements prioritized experience replay based on importance, recency, and feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random
import numpy as np

from aico.core.logging import get_logger

logger = get_logger("shared", "memory.consolidation.replay")


@dataclass
class ExperiencePriority:
    """
    Priority calculation for an experience.
    
    Attributes:
        experience_id: Unique identifier for the experience
        importance_score: Cosine similarity to recent queries
        recency_bonus: Bonus based on recency (1 / days_since)
        feedback_bonus: Bonus if experience has user feedback
        total_priority: Combined priority score
    """
    experience_id: str
    importance_score: float
    recency_bonus: float
    feedback_bonus: float
    total_priority: float
    
    @classmethod
    def calculate(
        cls,
        experience_id: str,
        importance_score: float,
        days_since: float,
        has_feedback: bool
    ) -> "ExperiencePriority":
        """
        Calculate priority for an experience.
        
        Args:
            experience_id: Experience identifier
            importance_score: Importance score (0.0 to 1.0)
            days_since: Days since experience occurred
            has_feedback: Whether experience has user feedback
            
        Returns:
            ExperiencePriority object
        """
        # Recency bonus: 1 / max(1, days_since)
        recency_bonus = 1.0 / max(1.0, days_since)
        
        # Feedback bonus: +1.0 if has feedback
        feedback_bonus = 1.0 if has_feedback else 0.0
        
        # Total priority
        total_priority = abs(importance_score) + recency_bonus + feedback_bonus
        
        return cls(
            experience_id=experience_id,
            importance_score=importance_score,
            recency_bonus=recency_bonus,
            feedback_bonus=feedback_bonus,
            total_priority=total_priority
        )


@dataclass
class ReplaySequence:
    """
    A sequence of experiences selected for replay.
    
    Attributes:
        sequence_id: Unique identifier for this sequence
        user_id: User this sequence belongs to
        experiences: List of experience IDs in replay order
        priorities: Priority scores for each experience
        created_at: When sequence was generated
        metadata: Additional metadata
    """
    sequence_id: str
    user_id: str
    experiences: List[str]
    priorities: List[ExperiencePriority]
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size(self) -> int:
        """Get number of experiences in sequence."""
        return len(self.experiences)
    
    @property
    def avg_priority(self) -> float:
        """Get average priority of experiences."""
        if not self.priorities:
            return 0.0
        return sum(p.total_priority for p in self.priorities) / len(self.priorities)
    
    @property
    def has_feedback_count(self) -> int:
        """Count experiences with feedback."""
        return sum(1 for p in self.priorities if p.feedback_bonus > 0)


class ExperienceReplay:
    """
    Generates prioritized replay sequences from working memory.
    
    Implements prioritized experience replay algorithm for memory consolidation.
    Selects experiences based on importance, recency, and user feedback.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        priority_alpha: float = 0.6,
        recent_queries_window: int = 10
    ):
        """
        Initialize experience replay generator.
        
        Args:
            batch_size: Number of experiences per replay batch
            priority_alpha: Weight for priority-based sampling (0.0 = uniform, 1.0 = greedy)
            recent_queries_window: Number of recent queries to consider for importance
        """
        self.batch_size = batch_size
        self.priority_alpha = priority_alpha
        self.recent_queries_window = recent_queries_window
        
        self._recent_queries: List[np.ndarray] = []
    
    def update_recent_queries(self, query_embedding: np.ndarray) -> None:
        """
        Update recent queries for importance scoring.
        
        Args:
            query_embedding: Embedding of recent query
        """
        self._recent_queries.append(query_embedding)
        
        # Keep only last N queries
        if len(self._recent_queries) > self.recent_queries_window:
            self._recent_queries = self._recent_queries[-self.recent_queries_window:]
    
    def calculate_importance(self, experience_embedding: np.ndarray) -> float:
        """
        Calculate importance score based on similarity to recent queries.
        
        Args:
            experience_embedding: Embedding of experience
            
        Returns:
            Importance score (average cosine similarity to recent queries)
        """
        if not self._recent_queries:
            return 0.5  # Default importance if no recent queries
        
        # Calculate cosine similarity to each recent query
        similarities = []
        for query_emb in self._recent_queries:
            similarity = np.dot(experience_embedding, query_emb) / (
                np.linalg.norm(experience_embedding) * np.linalg.norm(query_emb)
            )
            similarities.append(similarity)
        
        # Return average similarity
        return float(np.mean(similarities))
    
    def generate_replay_sequence(
        self,
        experiences: List[Dict[str, Any]],
        user_id: str
    ) -> ReplaySequence:
        """
        Generate a prioritized replay sequence from experiences.
        
        Args:
            experiences: List of experience dictionaries with:
                - id: Experience ID
                - embedding: Experience embedding (numpy array)
                - timestamp: When experience occurred
                - has_feedback: Whether experience has user feedback
            user_id: User ID
            
        Returns:
            ReplaySequence with prioritized experiences
        """
        if not experiences:
            return ReplaySequence(
                sequence_id=f"replay_{user_id}_{datetime.utcnow().isoformat()}",
                user_id=user_id,
                experiences=[],
                priorities=[]
            )
        
        # Calculate priorities for all experiences
        priorities = []
        now = datetime.utcnow()
        
        for exp in experiences:
            # Calculate days since experience
            exp_time = exp.get("timestamp", now)
            if isinstance(exp_time, str):
                exp_time = datetime.fromisoformat(exp_time)
            days_since = (now - exp_time).total_seconds() / 86400.0
            
            # Calculate importance score
            embedding = exp.get("embedding")
            if embedding is not None and isinstance(embedding, np.ndarray):
                importance = self.calculate_importance(embedding)
            else:
                importance = 0.5  # Default if no embedding
            
            # Calculate priority
            priority = ExperiencePriority.calculate(
                experience_id=exp["id"],
                importance_score=importance,
                days_since=days_since,
                has_feedback=exp.get("has_feedback", False)
            )
            priorities.append(priority)
        
        # Select experiences using weighted sampling
        selected_priorities = self._prioritized_sample(priorities, self.batch_size)
        selected_ids = [p.experience_id for p in selected_priorities]
        
        sequence = ReplaySequence(
            sequence_id=f"replay_{user_id}_{datetime.utcnow().isoformat()}",
            user_id=user_id,
            experiences=selected_ids,
            priorities=selected_priorities,
            metadata={
                "total_experiences": len(experiences),
                "selected_count": len(selected_ids),
                "avg_priority": sum(p.total_priority for p in selected_priorities) / len(selected_priorities) if selected_priorities else 0,
                "feedback_count": sum(1 for p in selected_priorities if p.feedback_bonus > 0)
            }
        )
        
        logger.info("Replay sequence generated", extra={
            "user_id": user_id,
            "sequence_id": sequence.sequence_id,
            "total_experiences": len(experiences),
            "selected_count": sequence.size,
            "avg_priority": sequence.avg_priority,
            "feedback_count": sequence.has_feedback_count
        })
        
        return sequence
    
    def _prioritized_sample(
        self,
        priorities: List[ExperiencePriority],
        k: int
    ) -> List[ExperiencePriority]:
        """
        Sample experiences using prioritized sampling.
        
        Uses weighted random sampling based on priority scores.
        O(N) complexity using random.choices.
        
        Args:
            priorities: List of experience priorities
            k: Number of samples to select
            
        Returns:
            List of selected priorities
        """
        if not priorities:
            return []
        
        # Limit k to available experiences
        k = min(k, len(priorities))
        
        # Extract weights (total_priority values)
        weights = [p.total_priority for p in priorities]
        
        # Apply priority exponent (alpha)
        if self.priority_alpha != 1.0:
            weights = [w ** self.priority_alpha for w in weights]
        
        # Sample without replacement
        # Note: random.choices samples with replacement, so we use a different approach
        selected_indices = []
        remaining_priorities = list(priorities)
        remaining_weights = list(weights)
        
        for _ in range(k):
            if not remaining_priorities:
                break
            
            # Sample one experience
            selected = random.choices(
                remaining_priorities,
                weights=remaining_weights,
                k=1
            )[0]
            
            # Find and remove selected experience
            idx = remaining_priorities.index(selected)
            selected_indices.append(priorities.index(selected))
            remaining_priorities.pop(idx)
            remaining_weights.pop(idx)
        
        # Return selected priorities in original order
        selected_indices.sort()
        return [priorities[i] for i in selected_indices]
    
    async def replay_to_semantic(
        self,
        sequence: ReplaySequence,
        semantic_store,
        working_store
    ) -> Dict[str, Any]:
        """
        Replay experiences to semantic memory.
        
        Args:
            sequence: Replay sequence to process
            semantic_store: Semantic memory store instance
            working_store: Working memory store instance
            
        Returns:
            Dictionary with replay results
        """
        transferred = 0
        errors = []
        
        for exp_id in sequence.experiences:
            try:
                # Retrieve experience from working memory
                experience = await working_store.get(exp_id)
                
                if experience is None:
                    logger.warning("Experience not found in working memory", extra={
                        "experience_id": exp_id
                    })
                    continue
                
                # Transfer to semantic memory
                await semantic_store.store(experience)
                transferred += 1
                
            except Exception as e:
                error_msg = f"Failed to transfer {exp_id}: {str(e)}"
                errors.append(error_msg)
                logger.error("Experience transfer failed", extra={
                    "experience_id": exp_id,
                    "error": str(e)
                }, exc_info=True)
        
        result = {
            "sequence_id": sequence.sequence_id,
            "user_id": sequence.user_id,
            "total_experiences": sequence.size,
            "transferred": transferred,
            "failed": len(errors),
            "errors": errors
        }
        
        logger.info("Replay to semantic complete", extra=result)
        
        return result
