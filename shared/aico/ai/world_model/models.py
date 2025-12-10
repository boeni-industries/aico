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


# Phase 6.4: Schema Learning, Hypothesis, and Drift Detection Models


@dataclass
class FieldSchema:
    """Schema definition for a field."""
    name: str
    field_type: str  # string, number, boolean, array, object
    required: bool = False
    description: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)  # min, max, pattern, etc.
    examples: List[Any] = field(default_factory=list)


@dataclass
class Schema:
    """Learned schema for an entity type."""
    schema_id: str
    version: str  # semantic versioning (major.minor.patch)
    entity_type: str
    fields: Dict[str, FieldSchema] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sample_count: int = 0  # Number of samples used to learn schema
    confidence: float = 0.0  # 0.0-1.0, based on sample consistency


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Hypothesis:
    """Hypothesis about user state or patterns."""
    hypothesis_id: str
    user_id: str
    description: str
    hypothesis_type: str  # state_change, pattern, relationship, behavioral
    affected_entities: List[str] = field(default_factory=list)
    confidence: float = 0.5  # 0.0-1.0, Bayesian posterior
    status: str = "open"  # open, confirmed, rejected, needs_user_confirmation
    evidence: List[str] = field(default_factory=list)  # PerceptualEvent IDs
    counter_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HypothesisTestResult:
    """Result of hypothesis testing."""
    hypothesis_id: str
    test_type: str  # evidence_check, pattern_match, user_confirmation
    supports_hypothesis: bool
    confidence_delta: float  # Change in confidence (-1.0 to +1.0)
    evidence_ids: List[str] = field(default_factory=list)
    tested_at: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


@dataclass
class DriftReport:
    """Report of detected drift in entity or pattern."""
    drift_id: str
    entity_id: str
    entity_type: str
    drift_type: str  # temporal, behavioral, contextual, relational
    severity: float  # 0.0-1.0, how significant the drift is
    old_state: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    description: Optional[str] = None


@dataclass
class Contradiction:
    """Contradiction between facts or beliefs."""
    contradiction_id: str
    fact_ids: List[str]  # WorldStateFact IDs in conflict
    description: str
    severity: float  # 0.0-1.0, impact of contradiction
    resolution_strategy: str  # favor_recent, favor_confident, ask_user, open_hypothesis
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class ConfidenceDecayConfig:
    """Configuration for confidence decay over time."""
    half_life_days: float = 30.0  # Days for confidence to decay to 50%
    min_confidence: float = 0.1  # Minimum confidence floor
    decay_function: str = "exponential"  # exponential, linear, step
