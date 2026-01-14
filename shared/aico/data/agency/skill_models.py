"""
Agency Skill Data Models

Dataclasses for skill-related entities.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgencySkillGap:
    """Agency skill gap model - matches agency_skill_gaps table."""
    gap_id: str
    step_description: str
    first_seen_at: str
    last_seen_at: str
    created_at: str
    updated_at: str
    llm_suggested_skills: Optional[str] = None
    step_metadata: Optional[str] = None
    pattern_embedding: Optional[str] = None
    frequency_count: int = 1
    priority_score: float = 0.0
    suggested_skill_spec: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AgencySkillExecution:
    """Agency skill execution model - matches agency_skill_executions table."""
    execution_id: str
    skill_id: str
    user_id: str
    outcome: str
    created_at: str
    message_id: Optional[str] = None
    goal_id: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    context_json: Optional[dict] = None


@dataclass
class AgencySkillLearningData:
    """Agency skill learning data model - matches agency_skill_learning_data table."""
    skill_id: str
    dimension_vector: str
    created_at: str
    updated_at: str
