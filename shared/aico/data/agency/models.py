"""
Agency System Data Models

Dataclasses for agency-related entities (goals, plans, lessons).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Goal:
    """Agency goal model."""
    goal_id: str
    user_id: str
    origin: str
    title: str
    status: str
    priority: str
    goal_type: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Plan:
    """Agency plan model."""
    plan_id: str
    goal_id: str
    status: str
    steps_json: List[Dict[str, Any]]
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Lesson:
    """Agency lesson model."""
    lesson_id: str
    user_id: str
    lesson_type: str
    content: str
    confidence: float
    status: str
    source_data: Optional[Dict[str, Any]] = None
    superseded_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Policy:
    """Agency policy rule model."""
    rule_id: str
    rule_name: str
    target_type: str
    conditions: str
    effect: str
    scope: str
    user_id: Optional[str] = None
    user_message_template: Optional[str] = None
    priority: int = 50
    version: int = 1
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
