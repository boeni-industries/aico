"""
AMS (Adaptive Modeling System) Data Models

Dataclasses for AMS entities (trajectories, feedback, skills).
Matches actual PostgreSQL schema.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class BehavioralSkill:
    """Behavioral skill model - matches ams_behavioral_skills table."""
    skill_id: str
    skill_name: str
    skill_type: str
    trigger_context: str
    procedure_template: str
    dimension_vector: str
    supported_languages: Optional[str] = None
    status: str = 'active'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Trajectory:
    """AMS trajectory model - matches ams_trajectories table."""
    trajectory_id: str
    user_id: str
    timestamp: datetime
    conversation_id: Optional[str] = None
    selected_skill_id: Optional[str] = None
    context_bucket: Optional[str] = None
    feedback_reward: Optional[int] = None
    archived: bool = False
    agency_context: Optional[str] = None
    message_id: Optional[str] = None
    turn_number: Optional[int] = None
    user_input: Optional[str] = None
    ai_response: Optional[str] = None


@dataclass
class AMSUserMemory:
    """AMS user memory model - matches ams_user_memories table."""
    fact_id: str
    user_id: str
    fact_type: str
    category: str
    confidence: float
    is_immutable: bool
    valid_from: datetime
    content: str
    extraction_method: str
    source_conversation_id: str
    valid_until: Optional[datetime] = None
    entities_json: Optional[Dict[str, Any]] = None
    source_message_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_note: Optional[str] = None
    tags_json: Optional[Dict[str, Any]] = None
    is_favorite: bool = False
    revisit_count: int = 0
    last_revisited: Optional[datetime] = None
    emotional_tone: Optional[str] = None
    memory_type: Optional[str] = None
    content_type: str = 'message'
    conversation_title: Optional[str] = None
    conversation_summary: Optional[str] = None
    turn_range: Optional[str] = None
    key_moments_json: Optional[Dict[str, Any]] = None
    temporal_metadata: Optional[str] = None
    language: Optional[str] = None


@dataclass
class BehavioralFeedback:
    """AMS behavioral feedback model - matches ams_behavioral_feedback table."""
    feedback_id: str
    user_id: str
    timestamp: str  # TEXT in schema
    message_id: Optional[str] = None
    skill_id: Optional[str] = None
    reward: Optional[int] = None
    reason: Optional[str] = None
    processed: int = 0
    outcome: Optional[str] = None
    execution_time_ms: Optional[int] = None
    context_json: Optional[Dict[str, Any]] = None
    user_satisfaction: Optional[float] = None
    free_text: Optional[str] = None
    processed_at: Optional[datetime] = None
