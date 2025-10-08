"""
Semantic Memory Data Schemas

This module defines the core data structures and schemas used throughout AICO's
semantic memory system. These schemas serve as the single source of truth for
all semantic memory operations including fact extraction, storage, querying,
and inter-module communication.

The schemas defined here are persisted to ChromaDB and used across multiple
modules:
- AI Analysis (fact extraction)
- Memory Management (semantic storage)
- Backend APIs (REST endpoints)
- CLI Commands (user interaction)
- Frontend Integration (data display)

Schema Evolution:
- All changes to these schemas must maintain backward compatibility
- New fields should be optional with sensible defaults
- Deprecated fields should be marked and gradually phased out
- Version increments should follow semantic versioning principles

Data Persistence:
- PersonalFact objects are stored in ChromaDB with vector embeddings
- Metadata is preserved in ChromaDB collection metadata
- User scoping ensures data isolation between users
- Confidence scoring enables quality-based filtering

Thread Safety:
- All dataclasses are immutable by design (frozen=True where applicable)
- No shared mutable state between schema instances
- Safe for concurrent access across async operations

@author: AICO Development Team
@since: Phase 2 - Semantic Memory Implementation
@version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class FactCategory(Enum):
    """
    Categories for personal facts to enable structured organization and retrieval.
    
    Each category has different retention and confidence characteristics:
    - IDENTITY: Core personal information (name, birthday) - permanent storage
    - PREFERENCE: User preferences and choices - evolving over time
    - RELATIONSHIP: Family, friends, colleagues - evolving relationships
    - DATE: Important dates and appointments - mixed permanence
    - CONTEXT: Work, living situation, temporary context - shorter retention
    """
    IDENTITY = "identity"
    PREFERENCE = "preference" 
    RELATIONSHIP = "relationship"
    DATE = "date"
    CONTEXT = "context"


class FactPermanence(Enum):
    """
    Permanence levels for facts to guide retention policies.
    
    Used by the scheduler's memory maintenance tasks:
    - PERMANENT: Never expires (name, birthday)
    - EVOLVING: Slowly decays over time (preferences, relationships)
    - TEMPORARY: Faster decay (appointments, context)
    """
    PERMANENT = "permanent"
    EVOLVING = "evolving"
    TEMPORARY = "temporary"


@dataclass(frozen=True)
class PersonalFact:
    """
    Core data structure representing a personal fact extracted from user messages.
    
    This is the fundamental unit of semantic memory storage. Each fact represents
    a piece of information about a user that is worth remembering for relationship
    building and personalized interactions.
    
    Immutable Design:
    - Frozen dataclass prevents accidental mutation
    - All modifications create new instances
    - Thread-safe for concurrent operations
    
    Persistence:
    - Stored in ChromaDB with vector embeddings for semantic search
    - Metadata preserved in ChromaDB collection metadata
    - User-scoped storage prevents cross-user contamination
    
    Attributes:
        fact_text: The actual factual statement about the user
        category: Classification of the fact type (see FactCategory)
        permanence: Retention policy indicator (see FactPermanence)
        confidence: AI confidence score (0.0-1.0) for quality filtering
        reasoning: LLM explanation of why this fact is worth storing
        source_message: Original user message that contained this fact
        timestamp: When this fact was extracted (UTC)
        user_id: User identifier for data scoping and isolation
        metadata: Additional structured data for fact context
    """
    fact_text: str
    category: FactCategory
    permanence: FactPermanence
    confidence: float
    reasoning: str
    source_message: str
    timestamp: datetime
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fact data integrity"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if not self.fact_text.strip():
            raise ValueError("Fact text cannot be empty")
        
        if not self.user_id.strip():
            raise ValueError("User ID cannot be empty")


@dataclass(frozen=True)
class SemanticQuery:
    """
    Query structure for semantic memory searches.
    
    Encapsulates all parameters needed for semantic similarity search
    including user scoping, filtering, and result limits.
    
    Attributes:
        query_text: Natural language query for semantic search
        user_id: User identifier to scope search results
        max_results: Maximum number of results to return
        confidence_threshold: Minimum confidence score for results
        category_filter: Optional filter by fact category
        permanence_filter: Optional filter by fact permanence
        metadata_filters: Optional ChromaDB metadata filters
    """
    query_text: str
    user_id: str
    max_results: int = 20
    confidence_threshold: float = 0.8
    category_filter: Optional[FactCategory] = None
    permanence_filter: Optional[FactPermanence] = None
    metadata_filters: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SemanticResult:
    """
    Result structure for semantic memory queries.
    
    Represents a single search result with similarity scoring and metadata.
    Results are ordered by semantic similarity (highest first).
    
    Attributes:
        fact: The personal fact that matched the query
        similarity_score: Semantic similarity score (0.0-1.0, higher is better)
        distance: Vector distance from ChromaDB (lower is better)
        search_metadata: Additional search context and debugging info
    """
    fact: PersonalFact
    similarity_score: float
    distance: float
    search_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate result data integrity"""
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {self.similarity_score}")


@dataclass
class FactExtractionResult:
    """
    Result of fact extraction operation from user message.
    
    Contains all facts extracted from a single message along with
    extraction metadata for debugging and quality assessment.
    
    Attributes:
        facts: List of extracted personal facts
        extraction_confidence: Overall confidence in extraction quality
        processing_time_ms: Time taken for extraction in milliseconds
        llm_model_used: Name of the LLM model used for extraction
        parsing_strategy: Which parsing strategy succeeded (json, regex, fallback)
        extraction_metadata: Additional debugging and context information
    """
    facts: List[PersonalFact]
    extraction_confidence: float
    processing_time_ms: float
    llm_model_used: str
    parsing_strategy: str
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


# Type aliases for common use cases
FactList = List[PersonalFact]
ResultList = List[SemanticResult]
QueryFilters = Dict[str, Any]

# Schema version for compatibility tracking
SEMANTIC_SCHEMA_VERSION = "1.0.0"
