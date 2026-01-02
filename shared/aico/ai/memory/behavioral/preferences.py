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
            
        Raises:
            RuntimeError: If ams_context_preference_vectors table doesn't exist
        """
        try:
            row = self.db.execute(
                """SELECT dimensions, last_updated_at FROM ams_context_preference_vectors
                   WHERE user_id = ? AND context_bucket = ?""",
                (user_id, context_bucket)
            ).fetchone()
        except Exception as e:
            if "no such table" in str(e).lower():
                logger.error(f"CRITICAL: ams_context_preference_vectors table does not exist: {e}")
                raise RuntimeError(
                    "ams_context_preference_vectors table does not exist. "
                    "Run database migration to create missing AMS tables."
                ) from e
            else:
                logger.error(f"Database error querying preference vectors: {e}")
                raise
        
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
        """Save preference vector to database.
        
        Raises:
            RuntimeError: If ams_context_preference_vectors table doesn't exist
        """
        try:
            self.db.execute(
                """INSERT INTO ams_context_preference_vectors (
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
        except Exception as e:
            if "no such table" in str(e).lower():
                logger.error(f"CRITICAL: ams_context_preference_vectors table does not exist: {e}")
                raise RuntimeError(
                    "ams_context_preference_vectors table does not exist. "
                    "Run database migration to create missing AMS tables."
                ) from e
            else:
                logger.error(f"Database error saving preference vector: {e}")
                raise

    async def get_user_interests(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Derive user interests from behavioral data for CuriosityEngine.

        This implementation uses the existing behavioral tables instead of a
        dedicated interests table:

        - "user_skill_confidence" provides usage counts and last_used_at
        - "skills" provides human-readable names we can treat as topics

        It returns a list of dictionaries compatible with CuriosityEngine
        expectations:

        {
            "topic": str,
            "engagement_score": float,
            "mention_count": int,
            "recency_score": float,
        }
        """
        try:
            # Join user_skill_confidence with skills to get names/topics
            rows = self.db.execute(
                """
                SELECT
                    s.skill_name,
                    usc.usage_count,
                    usc.confidence_score,
                    usc.last_used_at
                FROM user_skill_confidence usc
                JOIN skills s ON usc.skill_id = s.skill_id
                WHERE usc.user_id = ?
                ORDER BY usc.usage_count DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            if not rows:
                logger.info(
                    "[PREF] get_user_interests: no behavioral data for user, returning empty list",
                    extra={"user_id": user_id},
                )
                return []

            now = datetime.now(timezone.utc)
            interests: List[Dict[str, Any]] = []

            for row in rows:
                topic = row[0]
                usage_count = int(row[1] or 0)
                confidence = float(row[2] or 0.5)
                last_used_raw = row[3]

                recency_score = 0.5
                if last_used_raw:
                    try:
                        # last_used_at is stored as ISO string without timezone
                        last_used = datetime.fromisoformat(last_used_raw)
                        if last_used.tzinfo is None:
                            last_used = last_used.replace(tzinfo=timezone.utc)
                        age_days = max(0.0, (now - last_used).total_seconds() / 86400.0)
                        # Map 0 days -> 1.0, 30+ days -> ~0.0
                        recency_score = max(0.0, min(1.0, 1.0 - age_days / 30.0))
                    except Exception as e:
                        logger.warning(
                            "[PREF] Failed to parse last_used_at for user interest; using default recency",
                            extra={"user_id": user_id, "error": str(e)},
                        )

                # Engagement is primarily confidence, lightly scaled by usage
                engagement_score = confidence
                if usage_count > 0:
                    # Cap log factor to keep value in [0, 1]
                    import math

                    engagement_boost = min(0.3, math.log1p(usage_count) / 10.0)
                    engagement_score = max(0.0, min(1.0, confidence + engagement_boost))

                interests.append(
                    {
                        "topic": topic,
                        "engagement_score": engagement_score,
                        "mention_count": usage_count,
                        "recency_score": recency_score,
                    }
                )

            logger.info(
                "[PREF] get_user_interests: derived interests from behavioral data",
                extra={"user_id": user_id, "interest_count": len(interests)},
            )
            return interests

        except Exception as e:
            logger.error(
                f"[PREF] get_user_interests failed for user {user_id}: {e}",
            )
            return []
