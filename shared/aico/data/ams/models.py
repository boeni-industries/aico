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
