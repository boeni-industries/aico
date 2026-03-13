"""
AMS API Schemas

Pydantic models for AMS API request/response validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Consolidation Status Schemas
# ============================================================================

class ConsolidationSessionResponse(BaseModel):
    """Last consolidation session details."""
    experiences_replayed: int = Field(..., description="Number of conversation segments replayed")
    facts_consolidated: int = Field(..., description="Number of facts stored in semantic memory")
    graph_updates: Dict[str, int] = Field(..., description="Knowledge graph updates (entities, relationships)")
    duration_seconds: int = Field(..., description="Session duration in seconds")
    success: bool = Field(..., description="Whether session completed successfully")
    completed_at: str = Field(..., description="ISO timestamp of completion")


class ConsolidationStatusResponse(BaseModel):
    """Current consolidation engine status."""
    last_run: Optional[str] = Field(None, description="Human-readable time since last run")
    next_scheduled: str = Field(..., description="Next scheduled consolidation time")
    current_cycle_day: int = Field(..., description="Current day in rotation cycle (1-7)")
    total_cycle_days: int = Field(7, description="Total days in rotation cycle")
    status: str = Field(..., description="Current status: idle, running, scheduled")
    last_session: Optional[ConsolidationSessionResponse] = Field(None, description="Last session details")


# ============================================================================
# Behavioral Learning Schemas
# ============================================================================

class SkillInfoResponse(BaseModel):
    """Individual skill information."""
    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    confidence: float = Field(..., description="Confidence score (0-100)")
    usage_count: int = Field(..., description="Number of times skill has been used")
    last_feedback: Optional[str] = Field(None, description="Last feedback type: positive, negative, neutral")
    last_used: Optional[str] = Field(None, description="ISO timestamp of last use")


class BehavioralLearningStatsResponse(BaseModel):
    """Behavioral learning statistics."""
    active_skills: int = Field(..., description="Total number of active skills")
    total_feedback_received: int = Field(..., description="Total feedback events received")
    learning_rate: str = Field(..., description="Current learning state: Adapting, Stable, etc.")
    average_confidence: float = Field(..., description="Average confidence across all skills")
    top_skills: List[SkillInfoResponse] = Field(..., description="Top 5 performing skills")
    recent_learning_insights: List[str] = Field(..., description="Recent learning discoveries")


# ============================================================================
# User Preferences Schemas
# ============================================================================

class PreferenceDimensionResponse(BaseModel):
    """Single preference dimension."""
    name: str = Field(..., description="Dimension name (e.g., Verbosity, Formality)")
    value: float = Field(..., description="Preference value (0.0-1.0)")
    label: str = Field(..., description="Human-readable label for current value")


class UserPreferencesResponse(BaseModel):
    """User preference profile."""
    dimensions: List[PreferenceDimensionResponse] = Field(..., description="Preference dimensions")
    context_buckets: int = Field(..., description="Number of context buckets")
    insights: List[str] = Field(..., description="Context-specific insights")


# ============================================================================
# Feedback Stats Schemas
# ============================================================================

class RecentFeedbackResponse(BaseModel):
    """Recent feedback event."""
    time: str = Field(..., description="Human-readable time")
    message: str = Field(..., description="Feedback message")
    skill: str = Field(..., description="Skill name")
    type: str = Field(..., description="Feedback type: positive, negative, neutral")


class FeedbackStatsResponse(BaseModel):
    """Feedback statistics."""
    total: int = Field(..., description="Total feedback events")
    positive: int = Field(..., description="Positive feedback count")
    negative: int = Field(..., description="Negative feedback count")
    neutral: int = Field(..., description="Neutral feedback count")
    response_rate: float = Field(..., description="Percentage of messages with feedback")
    recent_feedback: List[RecentFeedbackResponse] = Field(..., description="Recent feedback events")


# ============================================================================
# Combined AMS Stats Schema
# ============================================================================

class AMSStatsResponse(BaseModel):
    """Complete AMS statistics."""
    consolidation: ConsolidationStatusResponse = Field(..., description="Consolidation engine status")
    behavioral_learning: BehavioralLearningStatsResponse = Field(..., description="Behavioral learning stats")
    user_preferences: UserPreferencesResponse = Field(..., description="User preference profile")
    feedback: FeedbackStatsResponse = Field(..., description="Feedback statistics")


# ============================================================================
# Skill Overview Schemas
# ============================================================================

class SkillDetailResponse(BaseModel):
    """Detailed skill information."""
    skill_id: str = Field(..., description="Unique skill identifier")
    skill_name: str = Field(..., description="Human-readable skill name")
    skill_type: str = Field(..., description="Skill type (base, composite, etc.)")
    status: str = Field(..., description="Skill status (active, inactive, etc.)")
    confidence_score: Optional[float] = Field(None, description="User confidence score (0-100)")
    usage_count: Optional[int] = Field(None, description="Number of times used")
    positive_count: Optional[int] = Field(None, description="Positive feedback count")
    negative_count: Optional[int] = Field(None, description="Negative feedback count")
    last_used_at: Optional[str] = Field(None, description="ISO timestamp of last use")
    created_at: str = Field(..., description="ISO timestamp of skill creation")


class SkillOverviewResponse(BaseModel):
    """Complete skill overview with all available skills."""
    total_skills: int = Field(..., description="Total number of available skills")
    active_skills: int = Field(..., description="Number of skills with usage data")
    skills: List[SkillDetailResponse] = Field(..., description="List of all skills with details")


# ============================================================================
# Memory Evolution Schemas
# ============================================================================

class MemoryMetricsSnapshot(BaseModel):
    """Memory metrics at a point in time."""
    timestamp: str = Field(..., description="ISO timestamp")
    working_memory_count: int = Field(..., description="Number of working memory items")
    semantic_facts_count: int = Field(..., description="Number of semantic facts")
    knowledge_graph_entities: int = Field(..., description="Number of KG entities")
    knowledge_graph_relationships: int = Field(..., description="Number of KG relationships")
    total_conversations: int = Field(..., description="Total conversation count")


class MemoryGrowthStats(BaseModel):
    """Memory growth statistics over time."""
    period_days: int = Field(..., description="Time period in days")
    facts_added: int = Field(..., description="New facts added in period")
    entities_added: int = Field(..., description="New entities added in period")
    relationships_added: int = Field(..., description="New relationships added in period")
    consolidation_sessions: int = Field(..., description="Number of consolidation sessions")


class MemoryEvolutionResponse(BaseModel):
    """Memory evolution tracking over time."""
    current_metrics: MemoryMetricsSnapshot = Field(..., description="Current memory state")
    growth_7d: MemoryGrowthStats = Field(..., description="Growth in last 7 days")
    growth_30d: MemoryGrowthStats = Field(..., description="Growth in last 30 days")
    historical_snapshots: List[MemoryMetricsSnapshot] = Field(..., description="Historical data points")
    insights: List[str] = Field(..., description="Memory evolution insights")
