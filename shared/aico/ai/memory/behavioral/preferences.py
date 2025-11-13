"""
User Preference Management

Manages context-aware user preference vectors with explicit dimensions.
Part of AICO's behavioral learning system.
"""

import json
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime

from aico.core.logging import get_logger
from .models import PreferenceVector, Skill

logger = get_logger("shared", "memory.behavioral.preferences")


class PreferenceManager:
    """
    Manages user preference vectors (16 explicit dimensions per context bucket).
    
    Preference vectors are NOT embeddings - they're explicit style attributes
    like verbosity, formality, technical_depth, etc.
    """
    
    def __init__(self, db_connection, learning_rate: float = 0.1):
        """
        Initialize preference manager.
        
        Args:
            db_connection: Encrypted libSQL database connection
            learning_rate: How quickly preferences adapt to feedback
        """
        self.db = db_connection
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
        row = self.db.execute(
            """SELECT dimensions, last_updated_at FROM context_preference_vectors
               WHERE user_id = ? AND context_bucket = ?""",
            (user_id, context_bucket)
        ).fetchone()
        
        if row:
            return PreferenceVector(
                user_id=user_id,
                context_bucket=context_bucket,
                dimensions=json.loads(row[0]),
                last_updated_at=datetime.fromisoformat(row[1])
            )
        else:
            # Create neutral preference vector (all 0.5)
            pref = PreferenceVector.create_neutral(user_id, context_bucket)
            await self._save_preference_vector(pref)
            return pref
    
    async def update_from_feedback(
        self,
        user_id: str,
        context_bucket: int,
        skill: Skill,
        reward: int
    ) -> PreferenceVector:
        """
        Update user preferences based on feedback using gradient-based learning.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            skill: Skill that was applied
            reward: Feedback reward (-1 or 1, 0 ignored)
            
        Returns:
            Updated preference vector
        """
        if reward == 0:
            return await self.get_preference_vector(user_id, context_bucket)
        
        # Get current preferences
        pref = await self.get_preference_vector(user_id, context_bucket)
        
        # Gradient-based update: move toward/away from skill dimensions
        direction = reward * self.learning_rate
        new_dimensions = []
        
        for i in range(16):
            current = pref.dimensions[i]
            target = skill.dimension_vector[i]
            
            # Move toward target if positive feedback, away if negative
            new_value = current + direction * (target - current)
            
            # Clamp to [0.0, 1.0]
            new_value = max(0.0, min(1.0, new_value))
            new_dimensions.append(new_value)
        
        # Update preference vector
        updated_pref = PreferenceVector(
            user_id=user_id,
            context_bucket=context_bucket,
            dimensions=new_dimensions,
            last_updated_at=datetime.utcnow()
        )
        
        await self._save_preference_vector(updated_pref)
        
        logger.info("Preference vector updated", extra={
            "user_id": user_id,
            "context_bucket": context_bucket,
            "reward": reward,
            "change": np.linalg.norm(np.array(new_dimensions) - np.array(pref.dimensions))
        })
        
        return updated_pref
    
    def calculate_preference_alignment(
        self,
        user_preferences: PreferenceVector,
        skill: Skill
    ) -> float:
        """
        Calculate alignment between user preferences and skill dimensions.
        
        Uses Euclidean distance normalized to [0, 1] score.
        
        Args:
            user_preferences: User's preference vector
            skill: Skill to evaluate
            
        Returns:
            Alignment score (0.0 to 1.0, higher = better match)
        """
        # Calculate Euclidean distance
        distance = np.linalg.norm(
            np.array(user_preferences.dimensions) - np.array(skill.dimension_vector)
        )
        
        # Normalize to [0, 1] score (max distance = sqrt(16) for 16 dimensions)
        max_distance = np.sqrt(16.0)
        score = 1.0 - (distance / max_distance)
        
        return max(0.0, min(1.0, score))
    
    async def _save_preference_vector(self, pref: PreferenceVector) -> None:
        """Save preference vector to database."""
        self.db.execute(
            """INSERT INTO context_preference_vectors (
                user_id, context_bucket, dimensions, last_updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, context_bucket)
            DO UPDATE SET
                dimensions = excluded.dimensions,
                last_updated_at = excluded.last_updated_at""",
            (
                pref.user_id,
                pref.context_bucket,
                json.dumps(pref.dimensions),
                pref.last_updated_at.isoformat()
            )
        )
        self.db.commit()
