"""
Behavioral Learning Module

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

from .skills import (
    Skill,
    SkillStore,
    SkillSelector,
    TriggerContext
)
from .thompson_sampling import (
    ThompsonSamplingSelector,
    ContextBucket
)
from .preferences import (
    ContextPreferenceManager,
    PreferenceVector,
    PreferenceDimensions
)
from .feedback_classifier import (
    FeedbackClassifier,
    FeedbackCategory,
    ClassificationResult
)
from .rlhf import (
    RLHFProcessor,
    FeedbackEvent,
    RewardSignal
)
from .templates import (
    TemplateManager,
    PromptTemplate,
    TemplateVariable
)

__all__ = [
    # Skills
    "Skill",
    "SkillStore",
    "SkillSelector",
    "TriggerContext",
    # Thompson Sampling
    "ThompsonSamplingSelector",
    "ContextBucket",
    # Preferences
    "ContextPreferenceManager",
    "PreferenceVector",
    "PreferenceDimensions",
    # Feedback Classification
    "FeedbackClassifier",
    "FeedbackCategory",
    "ClassificationResult",
    # RLHF
    "RLHFProcessor",
    "FeedbackEvent",
    "RewardSignal",
    # Templates
    "TemplateManager",
    "PromptTemplate",
    "TemplateVariable",
]
