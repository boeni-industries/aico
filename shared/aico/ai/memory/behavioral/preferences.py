"""
User Preference Management

Manages context-aware user preference vectors with explicit dimensions.
Part of AICO's behavioral learning system.
"""

import json
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from aico.core.logging import get_logger
from .models import PreferenceVector, Skill

logger = get_logger("shared.memory.behavioral.preferences")


class PreferenceManager:
    """
    Manages user preference vectors (16 explicit dimensions per context bucket).
    
    Preference vectors are NOT embeddings - they're explicit style attributes
    like verbosity, formality, technical_depth, etc.
    """
    
    def __init__(self, uow_factory, learning_rate: float = 0.1):
        """
        Initialize preference manager.
        
        Args:
            uow_factory: Unit of Work factory for PostgreSQL access
            learning_rate: How quickly preferences adapt to feedback
        """
        self.uow_factory = uow_factory
        self.learning_rate = learning_rate
    
    async def get_preference_vector(
        self,
        user_id: str,
        context_bucket: int
    ) -> PreferenceVector:
        """
        Get user's preference vector for a context bucket.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket (0-99)
            
        Returns:
            PreferenceVector (creates neutral if not exists)
        """
        async with self.uow_factory() as uow:
            vectors = await uow.ams_context_preference_vectors.list(
                filters={'user_id': user_id, 'context_bucket': context_bucket},
                limit=1
            )
            
            if vectors:
                return vectors[0]
            else:
                # Create neutral preference vector
                neutral_vector = PreferenceVector(
                    user_id=user_id,
                    context_bucket=context_bucket,
                    dimensions=[0.5] * 16,  # Neutral (0.5) for all 16 dimensions
                    last_updated_at=datetime.now(timezone.utc)
                )
                await uow.ams_context_preference_vectors.create(neutral_vector)
                await uow.commit()
                return neutral_vector
    
    async def update_preferences(
        self,
        user_id: str,
        context_bucket: int,
        skill: Skill,
        feedback_score: float
    ) -> PreferenceVector:
        """
        Update user preferences based on skill execution feedback.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            skill: Skill that was executed
            feedback_score: Feedback score (0.0 = bad, 1.0 = good)
            
        Returns:
            Updated preference vector
        """
        # Get current preferences
        current_prefs = await self.get_preference_vector(user_id, context_bucket)
        
        # Get skill's dimension vector (what style this skill represents)
        skill_dims = skill.dimension_vector
        
        # Update preferences using gradient descent
        # Move preferences toward skill dimensions if feedback is positive
        # Move away if feedback is negative
        updated_dims = []
        for i in range(16):
            current_val = current_prefs.dimensions[i]
            skill_val = skill_dims[i]
            
            # Gradient: (feedback - 0.5) * (skill_val - current_val)
            # If feedback > 0.5 (positive), move toward skill_val
            # If feedback < 0.5 (negative), move away from skill_val
            gradient = (feedback_score - 0.5) * (skill_val - current_val)
            updated_val = current_val + self.learning_rate * gradient
            
            # Clip to [0, 1]
            updated_val = max(0.0, min(1.0, updated_val))
            updated_dims.append(updated_val)
        
        # Update in database
        current_prefs.dimensions = updated_dims
        current_prefs.last_updated_at = datetime.now(timezone.utc)
        
        async with self.uow_factory() as uow:
            await uow.ams_context_preference_vectors.update(current_prefs)
            await uow.commit()
        
        logger.info(f"Updated preferences for user {user_id}, context {context_bucket}")
        return current_prefs
    
    async def get_skill_match_score(
        self,
        user_id: str,
        context_bucket: int,
        skill: Skill
    ) -> float:
        """
        Calculate how well a skill matches user's preferences.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            skill: Skill to evaluate
            
        Returns:
            Match score (0.0 to 1.0)
        """
        prefs = await self.get_preference_vector(user_id, context_bucket)
        
        # Calculate cosine similarity between preference vector and skill vector
        pref_array = np.array(prefs.dimensions)
        skill_array = np.array(skill.dimension_vector)
        
        # Cosine similarity
        dot_product = np.dot(pref_array, skill_array)
        pref_norm = np.linalg.norm(pref_array)
        skill_norm = np.linalg.norm(skill_array)
        
        if pref_norm == 0 or skill_norm == 0:
            return 0.5  # Neutral if either vector is zero
        
        similarity = dot_product / (pref_norm * skill_norm)
        
        # Convert from [-1, 1] to [0, 1]
        score = (similarity + 1) / 2
        
        return score
    
    async def get_all_user_preferences(
        self,
        user_id: str
    ) -> List[PreferenceVector]:
        """
        Get all preference vectors for a user across all context buckets.
        
        Args:
            user_id: User ID
            
        Returns:
            List of preference vectors
        """
        async with self.uow_factory() as uow:
            return await uow.ams_context_preference_vectors.list(
                filters={'user_id': user_id},
                limit=100
            )
    
    async def reset_preferences(
        self,
        user_id: str,
        context_bucket: Optional[int] = None
    ) -> None:
        """
        Reset preferences to neutral values.
        
        Args:
            user_id: User ID
            context_bucket: Optional specific context bucket (resets all if None)
        """
        async with self.uow_factory() as uow:
            if context_bucket is not None:
                # Reset specific context
                vectors = await uow.ams_context_preference_vectors.list(
                    filters={'user_id': user_id, 'context_bucket': context_bucket},
                    limit=1
                )
                if vectors:
                    vector = vectors[0]
                    vector.dimensions = [0.5] * 16
                    vector.last_updated_at = datetime.now(timezone.utc)
                    await uow.ams_context_preference_vectors.update(vector)
            else:
                # Reset all contexts
                all_vectors = await uow.ams_context_preference_vectors.list(
                    filters={'user_id': user_id},
                    limit=100
                )
                for vector in all_vectors:
                    vector.dimensions = [0.5] * 16
                    vector.last_updated_at = datetime.now(timezone.utc)
                    await uow.ams_context_preference_vectors.update(vector)
            
            await uow.commit()
        
        logger.info(f"Reset preferences for user {user_id}")
