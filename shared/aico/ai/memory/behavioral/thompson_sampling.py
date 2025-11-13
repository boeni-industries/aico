"""
Thompson Sampling for Skill Selection

Contextual bandit algorithm for learning which skills work best through
Bayesian statistical learning. No neural network training required.
"""

import numpy as np
import json
from typing import List, Dict, Optional
from datetime import datetime

from aico.core.logging import get_logger
from .models import Skill, ContextSkillStats

logger = get_logger("shared", "memory.behavioral.thompson_sampling")


class ThompsonSamplingSelector:
    """
    Select skills using Thompson Sampling (contextual bandit).
    
    Maintains Beta(α, β) distributions for each (context, skill) pair.
    Balances exploration vs. exploitation automatically.
    """
    
    def __init__(self, db_connection, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        """
        Initialize Thompson Sampling selector.
        
        Args:
            db_connection: Encrypted libSQL database connection
            prior_alpha: Beta distribution prior (successes)
            prior_beta: Beta distribution prior (failures)
        """
        self.db = db_connection
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
    
    def _hash_context(self, context: Dict[str, any]) -> int:
        """
        Hash context into bucket ID for contextual learning.
        
        Args:
            context: Current conversation context (intent, sentiment, time_of_day, etc.)
            
        Returns:
            Bucket ID (0-99)
        """
        context_str = f"{context.get('intent', 'unknown')}_" \
                     f"{context.get('sentiment', 'neutral')}_" \
                     f"{context.get('time_of_day', 'any')}"
        return hash(context_str) % 100  # 100 context buckets
    
    async def select_skill(
        self,
        user_id: str,
        context: Dict[str, any],
        candidate_skills: List[Skill]
    ) -> str:
        """
        Select best skill for given context using Thompson Sampling.
        
        Args:
            user_id: User ID
            context: Current conversation context
            candidate_skills: List of applicable skills
        
        Returns:
            skill_id of selected skill
        """
        # Hash context into bucket for contextual learning
        context_bucket = self._hash_context(context)
        
        # Get success/failure counts for each skill in this context bucket
        skill_scores = {}
        for skill in candidate_skills:
            stats = await self._get_skill_stats(user_id, skill.skill_id, context_bucket)
            
            # Sample from Beta distribution
            alpha = self.prior_alpha + stats['successes']
            beta = self.prior_beta + stats['failures']
            sampled_score = np.random.beta(alpha, beta)
            
            skill_scores[skill.skill_id] = sampled_score
        
        # Select skill with highest sampled score
        selected_skill_id = max(skill_scores, key=skill_scores.get)
        
        logger.info("Skill selected via Thompson Sampling", extra={
            "user_id": user_id,
            "skill_id": selected_skill_id,
            "context_bucket": context_bucket,
            "sampled_score": skill_scores[selected_skill_id],
            "metric_type": "behavioral_memory_selection"
        })
        
        return selected_skill_id
    
    async def update_from_feedback(
        self,
        user_id: str,
        skill_id: str,
        context: Dict[str, any],
        reward: int
    ) -> None:
        """
        Update skill statistics based on user feedback.
        
        Args:
            user_id: User ID
            skill_id: ID of skill that was applied
            context: Context in which skill was used (will be hashed to bucket)
            reward: 1 (success), -1 (failure), 0 (neutral - no update)
        """
        if reward == 0:
            return  # Neutral feedback doesn't update statistics
        
        # Hash context into bucket
        context_bucket = self._hash_context(context)
        
        # Get stats for this (context_bucket, skill) pair
        stats = await self._get_skill_stats(user_id, skill_id, context_bucket)
        
        if reward > 0:
            stats['successes'] += 1
        else:
            stats['failures'] += 1
        
        # Save stats for this specific context bucket
        await self._save_skill_stats(user_id, skill_id, context_bucket, stats)
        
        logger.info("Thompson Sampling stats updated", extra={
            "user_id": user_id,
            "skill_id": skill_id,
            "context_bucket": context_bucket,
            "reward": reward,
            "alpha": self.prior_alpha + stats['successes'],
            "beta": self.prior_beta + stats['failures']
        })
    
    async def _get_skill_stats(
        self,
        user_id: str,
        skill_id: str,
        context_bucket: int
    ) -> Dict[str, int]:
        """
        Get success/failure counts for (user, context_bucket, skill) triple.
        
        Returns:
            Dict with 'successes' and 'failures' counts
        """
        row = self.db.execute(
            """SELECT alpha, beta FROM context_skill_stats
               WHERE user_id = ? AND context_bucket = ? AND skill_id = ?""",
            (user_id, context_bucket, skill_id)
        ).fetchone()
        
        if row:
            # Convert Beta parameters back to success/failure counts
            # alpha = prior_alpha + successes, beta = prior_beta + failures
            successes = int(row[0] - self.prior_alpha)
            failures = int(row[1] - self.prior_beta)
            return {'successes': max(0, successes), 'failures': max(0, failures)}
        else:
            return {'successes': 0, 'failures': 0}
    
    async def _save_skill_stats(
        self,
        user_id: str,
        skill_id: str,
        context_bucket: int,
        stats: Dict[str, int]
    ) -> None:
        """Save success/failure counts for (user, context_bucket, skill) triple."""
        alpha = self.prior_alpha + stats['successes']
        beta = self.prior_beta + stats['failures']
        
        # Upsert stats
        self.db.execute(
            """INSERT INTO context_skill_stats (
                user_id, context_bucket, skill_id, alpha, beta, last_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, context_bucket, skill_id)
            DO UPDATE SET
                alpha = excluded.alpha,
                beta = excluded.beta,
                last_updated_at = excluded.last_updated_at""",
            (
                user_id,
                context_bucket,
                skill_id,
                alpha,
                beta,
                datetime.utcnow().isoformat()
            )
        )
        self.db.commit()
