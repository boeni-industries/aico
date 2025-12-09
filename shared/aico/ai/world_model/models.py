"""
World Model Data Structures

Data models for world model queries and context representation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class Entity:
    """Entity from knowledge graph."""
    id: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    last_mentioned: Optional[datetime] = None


@dataclass
class Project:
    """User project or ongoing activity."""
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"  # active, paused, completed
    related_entities: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OpenLoop:
    """Unresolved topic or pending follow-up from AMS."""
    id: str
    user_id: str
    description: str
    created_at: datetime
    priority: float = 0.5
    related_entities: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    """Recurring context or situation."""
    id: str
    name: str
    description: Optional[str] = None
    frequency: str = "unknown"  # daily, weekly, monthly, occasional
    related_entities: List[str] = field(default_factory=list)
    last_occurrence: Optional[datetime] = None


@dataclass
class UncertainArea:
    """Area of uncertainty or incomplete knowledge."""
    id: str
    topic: str
    description: str
    confidence_gap: float  # 0.0 = complete uncertainty, 1.0 = minor gap
    related_entities: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)


@dataclass
class UserContext:
    """Comprehensive user context from world model."""
    user_id: str
    active_projects: List[Project] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    recent_topics: List[str] = field(default_factory=list)
    relationship_closeness: float = 0.5
    last_interaction: Optional[datetime] = None
    primary_language: str = "en"


@dataclass
class WorldContext:
    """Complete world model context for a query."""
    user_id: str
    entities: List[Entity] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    open_loops: List[OpenLoop] = field(default_factory=list)
    recurring_contexts: List[Context] = field(default_factory=list)
    uncertain_areas: List[UncertainArea] = field(default_factory=list)
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
