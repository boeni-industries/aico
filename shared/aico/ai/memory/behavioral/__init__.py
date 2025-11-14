"""
Behavioral Learning Module (Phase 3)

Implements skill-based interaction learning with RLHF for AICO's Adaptive Memory System.
Enables the system to learn user preferences and adapt interaction styles through feedback.

This module provides:
- Skill library management
- Thompson Sampling for contextual bandit learning
- User preference tracking (16 explicit dimensions)
- Multilingual feedback classification
- RLHF integration
- Prompt template management
"""

from .models import (
    Skill,
    UserSkillConfidence,
    FeedbackEvent,
    Trajectory,
    ContextSkillStats,
    PreferenceVector
)
from .skills import SkillStore
from .thompson_sampling import ThompsonSamplingSelector
from .preferences import PreferenceManager

__all__ = [
    # Data models
    "Skill",
    "UserSkillConfidence",
    "FeedbackEvent",
    "Trajectory",
    "ContextSkillStats",
    "PreferenceVector",
    # Core components
    "SkillStore",
    "ThompsonSamplingSelector",
    "PreferenceManager",
]
