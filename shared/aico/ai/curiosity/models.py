"""
Curiosity Engine Data Models

Data structures for curiosity signals, hobby templates, and intrinsic motivation.
Based on agency-component-curiosity-engine.md and agency-ontology-schemas.md.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional


class CuriosityType(str, Enum):
    """Types of curiosity signals.
    
    From agency-component-curiosity-engine.md Section 2.1.
    """
    KNOWLEDGE_GAP = "knowledge_gap"  # AICO knows it doesn't know enough
    NOVELTY = "novelty"  # Under-explored but potentially meaningful
    SELF_PERFORMANCE = "self_performance"  # Improve weak/repetitive behavior
    HOBBY_PLAY = "hobby_play"  # Agent-self interest in hobbies


class HobbyCategory(str, Enum):
    """Categories of hobby activities.
    
    From agency-component-curiosity-engine.md hobby templates.
    """
    LEARNING = "learning"
    ORGANIZING = "organizing"
    RESEARCH = "research"
    CREATIVE = "creative"


@dataclass
class IntrinsicSignal:
    """Curiosity opportunity or intrinsic motivation signal.
    
    Represents a detected opportunity for exploration, learning, or hobby pursuit.
    Based on agency-component-curiosity-engine.md Section 3.1.
    
    Attributes:
        signal_id: Unique identifier for this signal
        user_id: User this signal relates to
        signal_type: Type of curiosity (knowledge_gap, novelty, etc.)
        
        # Content
        topic: Main topic or subject of curiosity
        description: Natural language description of the opportunity
        context: Additional context (related entities, conversations, etc.)
        
        # Scoring (0.0-1.0)
        novelty_score: How new/unexplored this area is
        uncertainty_score: Epistemic uncertainty or disagreement
        user_relevance_score: Estimated impact on user wellbeing
        feasibility_score: How achievable/practical this is
        cost_estimate: Rough resource/time estimate
        
        # Computed
        total_score: Weighted combination of scores
        priority: Mapped priority level (low, normal, high)
        
        # Metadata
        source_component: Which detector generated this signal
        target_ref: Reference to target entity in KG/ontology
        topic_tags: Ontology tags for classification
        detected_at: When signal was detected
        expires_at: Optional expiration time
        status: Current status of signal
    """
    signal_id: str
    user_id: str
    signal_type: CuriosityType
    
    # Content
    topic: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Scoring
    novelty_score: float = 0.0
    uncertainty_score: float = 0.0
    user_relevance_score: float = 0.0
    feasibility_score: float = 0.0
    cost_estimate: float = 0.0
    
    # Computed
    total_score: float = 0.0
    priority: str = "normal"
    
    # Metadata
    source_component: str = "curiosity_engine"
    target_ref: Optional[str] = None
    topic_tags: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: str = "pending"  # pending, converted, expired, dismissed


@dataclass
class HobbyTemplate:
    """Template for agent-self hobby goals.
    
    Defines a type of hobby activity that AICO can pursue autonomously.
    Based on agency-component-curiosity-engine.md hobby templates.
    
    Attributes:
        template_id: Unique identifier
        name: Display name
        category: Category (learning, organizing, research, creative)
        
        # Configuration
        description: Natural language description
        goal_template: Template string for goal title
        plan_steps: Template steps for planning
        
        # Constraints
        min_duration_minutes: Minimum time required
        requires_idle: Whether user must be idle
        requires_privacy: Whether privacy is needed
        
        # Personality fit
        personality_traits: Required trait levels (e.g., {"openness": 0.6})
        
        # Lifecycle
        preferred_times: Preferred time windows (morning, afternoon, evening, night)
        max_frequency_per_week: Maximum times per week
    """
    template_id: str
    name: str
    category: HobbyCategory
    
    # Configuration
    description: str
    goal_template: str
    plan_steps: List[str] = field(default_factory=list)
    
    # Constraints
    min_duration_minutes: int = 15
    requires_idle: bool = True
    requires_privacy: bool = False
    
    # Personality fit
    personality_traits: Dict[str, float] = field(default_factory=dict)
    
    # Lifecycle
    preferred_times: List[str] = field(default_factory=list)
    max_frequency_per_week: int = 3


# Default hobby templates from documentation
DEFAULT_HOBBY_TEMPLATES = [
    HobbyTemplate(
        template_id="deep_dive_learning",
        name="Deep Dive Learning",
        category=HobbyCategory.LEARNING,
        description="Explore a topic in depth through questions and research",
        goal_template="Deep dive into {topic}",
        plan_steps=[
            "Identify key questions about {topic}",
            "Research and gather information",
            "Synthesize understanding",
            "Identify follow-up areas",
        ],
        min_duration_minutes=15,
        requires_idle=True,
        personality_traits={"openness": 0.6},
        preferred_times=["afternoon", "evening"],
        max_frequency_per_week=3,
    ),
    HobbyTemplate(
        template_id="skill_building",
        name="Skill Building",
        category=HobbyCategory.LEARNING,
        description="Practice and improve a specific skill",
        goal_template="Practice and improve {skill}",
        plan_steps=[
            "Review current skill level",
            "Identify improvement areas",
            "Practice specific techniques",
            "Evaluate progress",
        ],
        min_duration_minutes=20,
        requires_idle=True,
        personality_traits={"conscientiousness": 0.6},
        preferred_times=["morning", "afternoon"],
        max_frequency_per_week=4,
    ),
    HobbyTemplate(
        template_id="memory_organization",
        name="Memory Organization",
        category=HobbyCategory.ORGANIZING,
        description="Review and organize stored memories",
        goal_template="Organize memories about {topic}",
        plan_steps=[
            "Review recent memories",
            "Identify connections and patterns",
            "Consolidate related memories",
            "Update knowledge graph",
        ],
        min_duration_minutes=10,
        requires_idle=True,
        personality_traits={"conscientiousness": 0.5},
        preferred_times=["night"],
        max_frequency_per_week=2,
    ),
    HobbyTemplate(
        template_id="kg_curation",
        name="Knowledge Graph Curation",
        category=HobbyCategory.ORGANIZING,
        description="Clean up and connect entities in knowledge graph",
        goal_template="Curate knowledge graph for {area}",
        plan_steps=[
            "Identify disconnected entities",
            "Find missing relationships",
            "Resolve ambiguities",
            "Strengthen connections",
        ],
        min_duration_minutes=15,
        requires_idle=True,
        personality_traits={"conscientiousness": 0.6},
        preferred_times=["night"],
        max_frequency_per_week=2,
    ),
    HobbyTemplate(
        template_id="pattern_analysis",
        name="Pattern Analysis",
        category=HobbyCategory.RESEARCH,
        description="Analyze patterns in conversations and interactions",
        goal_template="Analyze patterns in {domain}",
        plan_steps=[
            "Collect relevant data",
            "Identify recurring patterns",
            "Analyze significance",
            "Generate insights",
        ],
        min_duration_minutes=20,
        requires_idle=True,
        personality_traits={"openness": 0.7},
        preferred_times=["evening", "night"],
        max_frequency_per_week=2,
    ),
    HobbyTemplate(
        template_id="user_understanding",
        name="User Understanding",
        category=HobbyCategory.RESEARCH,
        description="Deepen understanding of user preferences and patterns",
        goal_template="Better understand {aspect} about user",
        plan_steps=[
            "Review interaction history",
            "Identify preference patterns",
            "Note important context",
            "Update user model",
        ],
        min_duration_minutes=15,
        requires_idle=True,
        personality_traits={"agreeableness": 0.6},
        preferred_times=["afternoon", "evening"],
        max_frequency_per_week=3,
    ),
]
