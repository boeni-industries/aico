"""
Feedback System Type Definitions

Enums for feedback event classification and categorization.
"""

from enum import Enum


class FeedbackEventType(str, Enum):
    """Top-level feedback event classification"""
    SIGNAL = "signal"    # Tier 1: Ambient behavioral signals
    ACTION = "action"    # Tier 2: Contextual user actions
    RATING = "rating"    # Tier 3: Explicit conversation ratings
    SURVEY = "survey"    # Tier 3: Explicit survey responses


class SignalCategory(str, Enum):
    """Categories for ambient signals (Tier 1)"""
    ENGAGEMENT = "engagement"
    TIMING = "timing"
    EDITING = "editing"
    NAVIGATION = "navigation"
    CONTENT_INTERACTION = "content_interaction"


class ActionCategory(str, Enum):
    """Categories for contextual actions (Tier 2)"""
    REMEMBER = "remember"
    REGENERATE = "regenerate"
    COPY = "copy"
    EXPLAIN = "explain"
    EDIT = "edit"
    DISMISS = "dismiss"


class RatingCategory(str, Enum):
    """Categories for explicit ratings (Tier 3)"""
    CONVERSATION_QUALITY = "conversation_quality"
    MESSAGE_QUALITY = "message_quality"
    FEATURE_SATISFACTION = "feature_satisfaction"


class SurveyCategory(str, Enum):
    """Categories for surveys (Tier 3)"""
    WEEKLY_CHECK = "weekly_check"
    HEALTH_CHECK = "health_check"
    FEATURE_DISCOVERY = "feature_discovery"
    NPS = "nps"
