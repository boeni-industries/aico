from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Trajectory(BaseModel):
    trajectory_id: str
    user_id: str

    conversation_id: Optional[str] = None
    selected_skill_id: Optional[str] = None
    context_bucket: Optional[str] = None
    feedback_reward: Optional[int] = None

    timestamp: datetime
    archived: bool = False

    agency_context: Optional[str] = None
    message_id: Optional[str] = None
    turn_number: Optional[int] = None
    user_input: Optional[str] = None
    ai_response: Optional[str] = None


class BehavioralFeedback(BaseModel):
    feedback_id: str
    user_id: str
    message_id: Optional[str] = None
    skill_id: Optional[str] = None
    reward: Optional[int] = None
    reason: Optional[str] = None
    timestamp: str
    processed: int = 0
    outcome: Optional[str] = None
    execution_time_ms: Optional[int] = None
    context_json: Optional[str] = None
    user_satisfaction: Optional[float] = None
    free_text: Optional[str] = None


class BehavioralSkill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    trigger_context: str
    procedure_template: str
    dimension_vector: str

    supported_languages: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    status: str = "active"


class AMSUserMemory(BaseModel):
    fact_id: str
    user_id: str

    fact_type: str
    category: str
    confidence: float

    is_immutable: bool = False

    valid_from: datetime
    valid_until: Optional[datetime] = None

    content: str
    entities_json: Optional[Dict[str, Any]] = None
    extraction_method: str

    source_conversation_id: str
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
    content_type: Optional[str] = "message"

    conversation_title: Optional[str] = None
    conversation_summary: Optional[str] = None
    turn_range: Optional[str] = None
    key_moments_json: Optional[Dict[str, Any]] = None
    temporal_metadata: Optional[str] = None

    language: Optional[str] = None
