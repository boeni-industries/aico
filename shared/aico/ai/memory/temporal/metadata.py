"""
Temporal Metadata Structures

Data structures for tracking temporal information in AICO's memory system.
Supports preference evolution, confidence decay, and historical state tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class ChangeType(Enum):
    """Types of changes that can occur in memory."""
    CREATED = "created"
    UPDATED = "updated"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    CONFIDENCE_DECAY = "confidence_decay"
    PREFERENCE_SHIFT = "preference_shift"


@dataclass
class TemporalMetadata:
    """
    Base temporal metadata for memory items.
    
    Tracks creation, updates, access patterns, and confidence evolution.
    Stored as JSON in database columns for efficient temporal queries.
    
    Attributes:
        created_at: When the memory was first created
        last_updated: When the memory was last modified
        last_accessed: When the memory was last retrieved
        access_count: Number of times memory has been accessed
        confidence: Current confidence score (decays over time)
        version: Version number (increments on updates)
        superseded_by: ID of memory that supersedes this one (if any)
    """
    created_at: datetime
    last_updated: datetime
    last_accessed: datetime
    access_count: int = 0
    confidence: float = 1.0
    version: int = 1
    superseded_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "confidence": self.confidence,
            "version": self.version,
            "superseded_by": self.superseded_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalMetadata":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            confidence=data.get("confidence", 1.0),
            version=data.get("version", 1),
            superseded_by=data.get("superseded_by")
        )
    
    def apply_confidence_decay(self, decay_rate: float, days_since_access: int) -> float:
        """
        Apply confidence decay based on time since last access.
        
        Args:
            decay_rate: Decay rate per day (e.g., 0.001 = 0.1% per day)
            days_since_access: Days since last access
            
        Returns:
            New confidence score
        """
        decay_factor = (1 - decay_rate) ** days_since_access
        self.confidence *= decay_factor
        return self.confidence
    
    def record_access(self) -> None:
        """Record that this memory was accessed."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def record_update(self) -> None:
        """Record that this memory was updated."""
        self.last_updated = datetime.utcnow()
        self.version += 1


@dataclass
class EvolutionRecord:
    """
    Record of a preference or behavior evolution event.
    
    Tracks how user preferences change over time, enabling the system
    to understand preference shifts and adapt accordingly.
    
    Attributes:
        timestamp: When the change occurred
        change_type: Type of change (created, updated, preference_shift, etc.)
        old_value: Previous value (if applicable)
        new_value: New value
        confidence: Confidence in this change
        context: Additional context about the change
        user_id: User this change applies to
    """
    timestamp: datetime
    change_type: ChangeType
    old_value: Optional[Any]
    new_value: Any
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "confidence": self.confidence,
            "context": self.context,
            "user_id": self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionRecord":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            change_type=ChangeType(data["change_type"]),
            old_value=data.get("old_value"),
            new_value=data["new_value"],
            confidence=data["confidence"],
            context=data.get("context", {}),
            user_id=data.get("user_id")
        )
    
    def is_significant_change(self, threshold: float = 0.2) -> bool:
        """
        Determine if this represents a significant change.
        
        Args:
            threshold: Minimum change magnitude to be considered significant
            
        Returns:
            True if change is significant
        """
        if self.old_value is None:
            return True  # New values are always significant
        
        # For numeric values, check magnitude of change
        if isinstance(self.old_value, (int, float)) and isinstance(self.new_value, (int, float)):
            change_magnitude = abs(self.new_value - self.old_value)
            return change_magnitude >= threshold
        
        # For other types, any change is significant
        return self.old_value != self.new_value


@dataclass
class HistoricalState:
    """
    Point-in-time snapshot of memory state.
    
    Enables temporal queries like "What did the system know at time T?"
    Used for debugging, auditing, and understanding system evolution.
    
    Attributes:
        timestamp: When this snapshot was taken
        memory_id: ID of the memory item
        state: Complete state at this point in time
        metadata: Temporal metadata at this point
        tags: Tags for categorization and retrieval
    """
    timestamp: datetime
    memory_id: str
    state: Dict[str, Any]
    metadata: TemporalMetadata
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_id": self.memory_id,
            "state": self.state,
            "metadata": self.metadata.to_dict(),
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoricalState":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            memory_id=data["memory_id"],
            state=data["state"],
            metadata=TemporalMetadata.from_dict(data["metadata"]),
            tags=data.get("tags", [])
        )


@dataclass
class PreferenceSnapshot:
    """
    Snapshot of user preferences at a specific time.
    
    Used for tracking preference evolution and understanding how
    user interaction styles change over time.
    
    Attributes:
        timestamp: When this snapshot was taken
        user_id: User this snapshot applies to
        context_bucket: Context bucket (hash of intent + sentiment + time_of_day)
        preference_vector: 16-dimensional explicit preference vector
        confidence: Confidence in these preferences
        sample_count: Number of interactions that informed these preferences
    """
    timestamp: datetime
    user_id: str
    context_bucket: int
    preference_vector: List[float]  # 16 dimensions
    confidence: float
    sample_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "context_bucket": self.context_bucket,
            "preference_vector": self.preference_vector,
            "confidence": self.confidence,
            "sample_count": self.sample_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceSnapshot":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data["user_id"],
            context_bucket=data["context_bucket"],
            preference_vector=data["preference_vector"],
            confidence=data["confidence"],
            sample_count=data["sample_count"]
        )
    
    def vector_distance(self, other: "PreferenceSnapshot") -> float:
        """
        Calculate Euclidean distance to another preference snapshot.
        
        Args:
            other: Another preference snapshot
            
        Returns:
            Euclidean distance between preference vectors
        """
        import numpy as np
        return float(np.linalg.norm(
            np.array(self.preference_vector) - np.array(other.preference_vector)
        ))
