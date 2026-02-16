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

logger = get_logger("shared.memory.behavioral.thompson_sampling")


class ThompsonSamplingSelector:
    """
    Select skills using Thompson Sampling (contextual bandit).
    
    Maintains Beta(α, β) distributions for each (context, skill) pair.
    Balances exploration vs. exploitation automatically.
    """
    
    def __init__(self, uow_factory, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        """
        Initialize Thompson Sampling selector.
        
        Args:
            uow_factory: Unit of Work factory for PostgreSQL access
            prior_alpha: Beta distribution prior (successes)
            prior_beta: Beta distribution prior (failures)
        """
        self.uow_factory = uow_factory
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
        print(f"🎲 [THOMPSON] Starting skill selection for user {user_id}")
        print(f"🎲 [THOMPSON] Candidate skills: {len(candidate_skills)}")
        print(f"🎲 [THOMPSON] Context: {context}")
        
        # Hash context into bucket for contextual learning
        context_bucket = self._hash_context(context)
        print(f"🎲 [THOMPSON] Context bucket: {context_bucket}")
        
        # Get success/failure counts for each skill in this context bucket
        skill_samples = {}
        
        async with self.uow_factory() as uow:
            for skill in candidate_skills:
                # Get stats for this (context_bucket, skill_id) pair
                stats_list = await uow.ams_context_skill_stats.list(
                    filters={
                        'user_id': user_id,
                        'context_bucket': context_bucket,
                        'skill_id': skill.skill_id
                    },
                    limit=1
                )
                
                if stats_list:
                    stats = stats_list[0]
                    alpha = self.prior_alpha + stats.success_count
                    beta = self.prior_beta + stats.failure_count
                else:
                    # No data yet - use priors
                    alpha = self.prior_alpha
                    beta = self.prior_beta
                
                # Sample from Beta(α, β) distribution
                sample = np.random.beta(alpha, beta)
                skill_samples[skill.skill_id] = sample
                
                print(f"🎲 [THOMPSON] Skill {skill.skill_id}: α={alpha:.1f}, β={beta:.1f}, sample={sample:.3f}")
        
        # Select skill with highest sample
        selected_skill_id = max(skill_samples, key=skill_samples.get)
        print(f"🎲 [THOMPSON] ✅ Selected skill: {selected_skill_id} (sample={skill_samples[selected_skill_id]:.3f})")
        
        return selected_skill_id
    
    async def update_feedback(
        self,
        user_id: str,
        context: Dict[str, any],
        skill_id: str,
        success: bool
    ) -> None:
        """
        Update skill statistics based on execution feedback.
        
        Args:
            user_id: User ID
            context: Context in which skill was executed
            skill_id: Skill that was executed
            success: Whether execution was successful
        """
        context_bucket = self._hash_context(context)
        
        async with self.uow_factory() as uow:
            # Get existing stats
            stats_list = await uow.ams_context_skill_stats.list(
                filters={
                    'user_id': user_id,
                    'context_bucket': context_bucket,
                    'skill_id': skill_id
                },
                limit=1
            )
            
            if stats_list:
                # Update existing stats
                stats = stats_list[0]
                if success:
                    stats.success_count += 1
                else:
                    stats.failure_count += 1
                stats.updated_at = datetime.utcnow()
                await uow.ams_context_skill_stats.update(stats)
            else:
                # Create new stats
                stats = ContextSkillStats(
                    user_id=user_id,
                    context_bucket=context_bucket,
                    skill_id=skill_id,
                    success_count=1 if success else 0,
                    failure_count=0 if success else 1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                await uow.ams_context_skill_stats.create(stats)
            
            await uow.commit()
        
        logger.info(f"Updated Thompson Sampling stats: user={user_id}, skill={skill_id}, success={success}")
    
    async def get_skill_performance(
        self,
        user_id: str,
        skill_id: str
    ) -> Dict[str, float]:
        """
        Get overall performance metrics for a skill.
        
        Args:
            user_id: User ID
            skill_id: Skill ID
            
        Returns:
            Dict with success_rate, total_executions, confidence
        """
        async with self.uow_factory() as uow:
            # Get all stats for this skill across all contexts
            all_stats = await uow.ams_context_skill_stats.list(
                filters={'user_id': user_id, 'skill_id': skill_id},
                limit=1000
            )
        
        if not all_stats:
            return {
                'success_rate': 0.5,  # Neutral prior
                'total_executions': 0,
                'confidence': 0.0
            }
        
        total_success = sum(s.success_count for s in all_stats)
        total_failure = sum(s.failure_count for s in all_stats)
        total_executions = total_success + total_failure
        
        if total_executions == 0:
            return {
                'success_rate': 0.5,
                'total_executions': 0,
                'confidence': 0.0
            }
        
        success_rate = total_success / total_executions
        
        # Confidence based on number of executions (Wilson score interval)
        # More executions = higher confidence
        confidence = min(1.0, total_executions / 100.0)
        
        return {
            'success_rate': success_rate,
            'total_executions': total_executions,
            'confidence': confidence
        }
