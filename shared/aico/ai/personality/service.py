"""
Personality Service

Provides personality traits and relationship context for agency decisions.
Phase 2: Basic wrapper with placeholders for future personality simulation integration.
"""

from typing import Optional
from .models import PersonalityContext, PersonalityTraits, RelationshipVector


class PersonalityService:
    """
    Personality Service provides personality and relationship context.
    
    Phase 2: Basic implementation with default values.
    Later phases: Full personality simulation integration.
    """
    
    def __init__(self, db_connection=None):
        """Initialize personality service.
        
        Args:
            db_connection: Optional database connection for future use
        """
        self.db = db_connection
        # Lazy logger initialization to avoid import errors
        try:
            from aico.core.logging import get_logger
            self.logger = get_logger("shared.personality.service")
            self.logger.info("[PERSONALITY] Service initialized (Phase 2 - basic mode)")
        except Exception:
            self.logger = None
    
    async def get_personality_context(self, user_id: str) -> PersonalityContext:
        """Get personality and relationship context for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            PersonalityContext with traits and relationship info
        """
        try:
            # Phase 2: Return default/neutral values
            # TODO: Integrate with actual personality simulation
            
            # Default AICO personality traits (balanced, slightly agreeable)
            traits = PersonalityTraits(
                extraversion=0.6,      # Moderately extraverted
                agreeableness=0.7,     # Quite agreeable
                conscientiousness=0.6, # Moderately conscientious
                neuroticism=0.3,       # Low neuroticism (stable)
                openness=0.8,          # High openness (curious)
            )
            
            # Default relationship vector (neutral, building trust)
            relationship = RelationshipVector(
                user_id=user_id,
                closeness=0.5,
                trust_level=0.5,
                familiarity=0.5,
                interaction_count=0,
                proactivity_preference=0.5,
                topic_boundaries={},
            )
            
            context = PersonalityContext(
                user_id=user_id,
                traits=traits,
                relationship=relationship,
                preferences={},
            )
            
            # Apply lesson-based persona adjustments
            adjustments = self.get_persona_adjustments(user_id)
            if adjustments:
                context = self.apply_persona_adjustments(context, adjustments)
                if self.logger:
                    self.logger.debug(
                        f"[PERSONALITY] Retrieved context for user {user_id} "
                        f"with {len(adjustments)} lesson-based adjustments"
                    )
            else:
                if self.logger:
                    self.logger.debug(f"[PERSONALITY] Retrieved context for user {user_id} (Phase 2 defaults)")
            
            return context
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[PERSONALITY] Failed to get personality context: {e}")
            # Return minimal context on error
            return PersonalityContext(user_id=user_id)
    
    def adjust_priority_for_personality(
        self,
        base_priority: str,
        personality: PersonalityContext,
    ) -> str:
        """Adjust goal priority based on personality traits.
        
        Args:
            base_priority: Base priority level (low, normal, high, urgent)
            personality: Personality context
            
        Returns:
            Adjusted priority level
        """
        try:
            # Phase 2: Simple adjustment based on conscientiousness
            # High conscientiousness = tend toward higher priorities
            # Low conscientiousness = more relaxed priorities
            
            conscientiousness = personality.traits.conscientiousness
            
            priority_map = {
                "low": 0,
                "normal": 1,
                "high": 2,
            }
            
            reverse_map = {0: "low", 1: "normal", 2: "high"}
            
            current_level = priority_map.get(base_priority.lower(), 1)
            
            # Adjust based on conscientiousness
            if conscientiousness > 0.7:
                # High conscientiousness: bump up one level (max high)
                adjusted_level = min(current_level + 1, 2)
            elif conscientiousness < 0.3:
                # Low conscientiousness: reduce one level (min low)
                adjusted_level = max(current_level - 1, 0)
            else:
                # Moderate: no change
                adjusted_level = current_level
            
            adjusted_priority = reverse_map[adjusted_level]
            
            if adjusted_priority != base_priority and self.logger:
                self.logger.debug(
                    f"[PERSONALITY] Adjusted priority from {base_priority} to {adjusted_priority} "
                    f"(conscientiousness={conscientiousness:.2f})"
                )
            
            return adjusted_priority
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[PERSONALITY] Failed to adjust priority: {e}")
            return base_priority
    
    def calculate_proactivity_level(
        self,
        personality: PersonalityContext,
    ) -> float:
        """Calculate appropriate proactivity level based on relationship.
        
        Args:
            personality: Personality context
            
        Returns:
            Proactivity level (0.0 = minimal, 1.0 = maximum)
        """
        try:
            # Phase 2: Base proactivity on relationship closeness and preference
            closeness = personality.relationship.closeness
            preference = personality.relationship.proactivity_preference
            
            # Weighted average: 60% preference, 40% closeness
            proactivity = (preference * 0.6) + (closeness * 0.4)
            
            if self.logger:
                self.logger.debug(
                    f"[PERSONALITY] Calculated proactivity={proactivity:.2f} "
                    f"(closeness={closeness:.2f}, preference={preference:.2f})"
                )
            
            return proactivity
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[PERSONALITY] Failed to calculate proactivity: {e}")
            return 0.5  # Default to moderate
    
    def get_persona_adjustments(self, user_id: str) -> dict:
        """
        Get active persona adjustments from behavioral learning lessons.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of trait_key -> adjustment_value
        """
        if not self.db:
            return {}
        
        try:
            # Query active persona lessons from agency_lessons
            rows = self.db.execute(
                """SELECT target_id, proposed_change
                   FROM agency_lessons
                   WHERE user_id = ? 
                   AND target_kind = 'persona_trait'
                   AND status = 'active'
                   AND applied_at IS NOT NULL""",
                (user_id,)
            ).fetchall()
            
            adjustments = {}
            for row in rows:
                trait_key = row["target_id"]  # e.g., "response_tone", "empathy_level"
                
                # Parse proposed change
                import json
                try:
                    change_data = json.loads(row["proposed_change"])
                    new_value = change_data.get("new")
                    if new_value is not None:
                        adjustments[trait_key] = new_value
                except (json.JSONDecodeError, KeyError):
                    continue
            
            if adjustments and self.logger:
                self.logger.debug(
                    f"[PERSONALITY] Loaded {len(adjustments)} persona adjustments for user {user_id}"
                )
            
            return adjustments
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[PERSONALITY] Failed to load persona adjustments: {e}")
            return {}
    
    def apply_persona_adjustments(
        self,
        base_context: PersonalityContext,
        adjustments: dict
    ) -> PersonalityContext:
        """
        Apply lesson-based adjustments to personality context.
        
        Args:
            base_context: Base personality context
            adjustments: Dictionary of adjustments from lessons
            
        Returns:
            Adjusted personality context
        """
        if not adjustments:
            return base_context
        
        # Create a copy to avoid mutating the original
        adjusted_context = PersonalityContext(
            user_id=base_context.user_id,
            traits=base_context.traits,
            relationship=base_context.relationship,
            preferences=base_context.preferences.copy() if base_context.preferences else {}
        )
        
        # Apply adjustments to preferences
        for key, value in adjustments.items():
            adjusted_context.preferences[key] = value
            
            if self.logger:
                self.logger.debug(
                    f"[PERSONALITY] Applied adjustment: {key} = {value}"
                )
        
        return adjusted_context
