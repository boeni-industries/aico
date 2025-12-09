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
            self.logger = get_logger("shared", "personality.service")
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
