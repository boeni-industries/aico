"""
Personality Service

Wrapper for personality simulation and relationship modeling.
Provides personality traits and relationship context for agency decisions.
"""

from .service import PersonalityService
from .models import PersonalityContext, RelationshipVector, PersonalityTraits

__all__ = [
    "PersonalityService",
    "PersonalityContext",
    "RelationshipVector",
    "PersonalityTraits",
]
