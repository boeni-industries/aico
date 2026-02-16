"""
Perceptual Event Data Structures

Defines the PerceptualEvent types used by the agency system to consume
interpreted signals from conversation, memory, sensors, and other sources.

Based on agency-ontology-schemas.md specification.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from enum import Enum


class PerceptType(Enum):
    """Top-level perceptual event types"""
    USER_INTENT = "UserIntentEvent"
    STATE_CHANGE = "StateChangeEvent"
    PATTERN = "PatternEvent"
    SOCIAL = "SocialEvent"
    RISK_OR_OPPORTUNITY = "RiskOrOpportunityEvent"
    SYSTEM_MAINTENANCE = "SystemMaintenanceEvent"
    CURIOSITY_SIGNAL = "CuriositySignalEvent"


class GoalHorizon(Enum):
    """Goal abstraction levels"""
    THEME = "theme"
    PROJECT = "project"
    TASK = "task"


class GoalOriginType(Enum):
    """Goal origin types"""
    USER = "user"
    AGENT_SELF = "agent_self"
    CURIOSITY = "curiosity"
    SYSTEM_MAINTENANCE = "system_maintenance"


@dataclass
class PerceptualEvent:
    """
    Central interpreted event unit consumed by the agency subsystem.
    
    Represents a semantic event extracted from raw signals (conversation,
    sensors, memory patterns, etc.) by upstream interpretation components.
    """
    
    # Identity
    percept_id: str
    timestamp: datetime
    source_component: str  # conversation_engine, world_model, ams, sensor_adapter, etc.
    
    # Type
    percept_type: PerceptType
    
    # Natural language summary
    summary_text: str
    
    # Structured slots (flexible JSON-like attributes)
    actors: List[str] = field(default_factory=list)  # Person/Agent IDs
    topic_tags: List[str] = field(default_factory=list)
    time_window: Optional[Dict[str, Any]] = None  # {start, end, granularity}
    location_ref: Optional[str] = None  # Place ID or descriptor
    
    # Scores and signals
    salience_score: float = 0.5  # 0-1, how important/noticeable
    urgency_score: float = 0.0  # 0-1, how time-sensitive
    risk_score: float = 0.0  # 0-1, potential harm
    opportunity_score: float = 0.0  # 0-1, potential benefit
    confidence_score: float = 1.0  # 0-1, interpretation confidence
    
    # Provenance
    raw_observation_ids: List[str] = field(default_factory=list)  # Message IDs, sensor IDs, etc.
    interpretation_chain: List[str] = field(default_factory=list)  # Components that processed this
    
    # Goal-related metadata (for UserIntentEvent and similar)
    candidate_goal_summaries: List[str] = field(default_factory=list)
    candidate_goal_horizon: Optional[GoalHorizon] = None
    candidate_origin: Optional[GoalOriginType] = None
    
    # Additional context (flexible)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Be resilient to enum fields being passed as raw strings from upstream.
        # This prevents runtime failures like: "'str' object has no attribute 'value'".
        if isinstance(self.percept_type, str):
            try:
                self.percept_type = PerceptType(self.percept_type)
            except ValueError:
                pass

        if isinstance(self.candidate_goal_horizon, str):
            try:
                self.candidate_goal_horizon = GoalHorizon(self.candidate_goal_horizon)
            except ValueError:
                pass

        if isinstance(self.candidate_origin, str):
            try:
                self.candidate_origin = GoalOriginType(self.candidate_origin)
            except ValueError:
                pass
    
    @classmethod
    def create_user_intent_event(
        cls,
        user_id: str,
        message_id: str,
        summary_text: str,
        goal_title: str,
        goal_description: Optional[str] = None,
        horizon: GoalHorizon = GoalHorizon.PROJECT,
        urgency: float = 0.5,
        confidence: float = 0.8,
        **kwargs
    ) -> "PerceptualEvent":
        """
        Factory method for creating UserIntentEvent from conversation.
        
        Args:
            user_id: User who expressed the intent
            message_id: Conversation message ID
            summary_text: Natural language summary of the intent
            goal_title: Extracted goal title
            goal_description: Optional detailed description
            horizon: Goal abstraction level (theme/project/task)
            urgency: How time-sensitive (0-1)
            confidence: Extraction confidence (0-1)
            **kwargs: Additional metadata
            
        Returns:
            PerceptualEvent configured as UserIntentEvent
        """
        import uuid
        
        return cls(
            percept_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            source_component="conversation_engine",
            percept_type=PerceptType.USER_INTENT,
            summary_text=summary_text,
            actors=[user_id],
            salience_score=0.9,  # User intents are highly salient
            urgency_score=urgency,
            confidence_score=confidence,
            raw_observation_ids=[message_id],
            interpretation_chain=["intent_classifier", "goal_extractor"],
            candidate_goal_summaries=[goal_title],
            candidate_goal_horizon=horizon,
            candidate_origin=GoalOriginType.USER,
            metadata={
                "goal_description": goal_description,
                "extracted_from_conversation": True,
                **kwargs
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        def _enum_value(value: Any) -> Any:
            return value.value if hasattr(value, "value") else value

        return {
            "percept_id": self.percept_id,
            "timestamp": self.timestamp.isoformat(),
            "source_component": self.source_component,
            "percept_type": _enum_value(self.percept_type),
            "summary_text": self.summary_text,
            "actors": self.actors,
            "topic_tags": self.topic_tags,
            "time_window": self.time_window,
            "location_ref": self.location_ref,
            "salience_score": self.salience_score,
            "urgency_score": self.urgency_score,
            "risk_score": self.risk_score,
            "opportunity_score": self.opportunity_score,
            "confidence_score": self.confidence_score,
            "raw_observation_ids": self.raw_observation_ids,
            "interpretation_chain": self.interpretation_chain,
            "candidate_goal_summaries": self.candidate_goal_summaries,
            "candidate_goal_horizon": _enum_value(self.candidate_goal_horizon) if self.candidate_goal_horizon else None,
            "candidate_origin": _enum_value(self.candidate_origin) if self.candidate_origin else None,
            "metadata": self.metadata
        }
