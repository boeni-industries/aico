"""
Personality Data Models

Simplified data models for personality and relationship context.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PersonalityTraits:
    """Big Five personality traits."""
    extraversion: float = 0.5
    agreeableness: float = 0.5
    conscientiousness: float = 0.5
    neuroticism: float = 0.5
    openness: float = 0.5


@dataclass
class EmotionState:
    """Simplified emotional state for a user.

    Provides valence/arousal signals for components like CuriosityEngine
    that apply emotion/relationship gates.
    """
    valence: float = 0.0  # -1.0 = very negative, 0.0 = neutral, 1.0 = very positive
    arousal: float = 0.0  # 0.0 = calm, 1.0 = highly activated


@dataclass
class RelationshipVector:
    """Relationship context for a user."""
    user_id: str
    closeness: float = 0.5  # 0.0 = distant, 1.0 = very close
    trust_level: float = 0.5
    familiarity: float = 0.5
    interaction_count: int = 0
    proactivity_preference: float = 0.5  # How much proactivity user prefers
    topic_boundaries: Dict[str, bool] = field(default_factory=dict)  # Topics to avoid/prefer


@dataclass
class PersonalityContext:
    """Complete personality and relationship context."""
    user_id: str
    traits: PersonalityTraits = field(default_factory=PersonalityTraits)
    relationship: RelationshipVector = field(default_factory=lambda: RelationshipVector(user_id=""))
    emotion: EmotionState = field(default_factory=EmotionState)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure relationship has correct user_id
        if not self.relationship.user_id:
            self.relationship.user_id = self.user_id
