"""
Temporal Query Support

Provides time-aware query builders for AICO's memory system.
Enables point-in-time queries, time-range queries, and evolution queries.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from aico.core.logging import get_logger

logger = get_logger("shared", "memory.temporal.queries")


class TimeRangeType(Enum):
    """Types of time ranges for queries."""
    ABSOLUTE = "absolute"  # Specific start and end times
    RELATIVE = "relative"  # Relative to current time (e.g., last 7 days)
    POINT_IN_TIME = "point_in_time"  # Specific point in time


@dataclass
class TimeRange:
    """
    Time range specification for temporal queries.
    
    Supports both absolute (specific dates) and relative (last N days) ranges.
    
    Attributes:
        range_type: Type of time range
        start_time: Start of range (for absolute ranges)
        end_time: End of range (for absolute ranges)
        relative_days: Number of days back (for relative ranges)
        point_in_time: Specific point in time (for point-in-time queries)
    """
    range_type: TimeRangeType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    relative_days: Optional[int] = None
    point_in_time: Optional[datetime] = None
    
    @classmethod
    def absolute(cls, start: datetime, end: datetime) -> "TimeRange":
        """Create an absolute time range."""
        return cls(
            range_type=TimeRangeType.ABSOLUTE,
            start_time=start,
            end_time=end
        )
    
    @classmethod
    def relative(cls, days: int) -> "TimeRange":
        """Create a relative time range (last N days)."""
        return cls(
            range_type=TimeRangeType.RELATIVE,
            relative_days=days
        )
    
    @classmethod
    def point(cls, timestamp: datetime) -> "TimeRange":
        """Create a point-in-time query."""
        return cls(
            range_type=TimeRangeType.POINT_IN_TIME,
            point_in_time=timestamp
        )
    
    def get_bounds(self) -> Tuple[datetime, datetime]:
        """
        Get the actual start and end times for this range.
        
        Returns:
            Tuple of (start_time, end_time)
        """
        if self.range_type == TimeRangeType.ABSOLUTE:
            return self.start_time, self.end_time
        
        elif self.range_type == TimeRangeType.RELATIVE:
            end = datetime.utcnow()
            start = end - timedelta(days=self.relative_days)
            return start, end
        
        elif self.range_type == TimeRangeType.POINT_IN_TIME:
            # For point-in-time, return same time for both bounds
            return self.point_in_time, self.point_in_time
        
        else:
            raise ValueError(f"Unknown time range type: {self.range_type}")
    
    def contains(self, timestamp: datetime) -> bool:
        """
        Check if a timestamp falls within this range.
        
        Args:
            timestamp: Timestamp to check
            
        Returns:
            True if timestamp is within range
        """
        start, end = self.get_bounds()
        
        if self.range_type == TimeRangeType.POINT_IN_TIME:
            # For point-in-time, check if timestamp is before or at the point
            return timestamp <= self.point_in_time
        
        return start <= timestamp <= end


@dataclass
class EvolutionQuery:
    """
    Query for preference or behavior evolution over time.
    
    Attributes:
        user_id: User to query
        context_bucket: Context bucket (optional, None for all contexts)
        time_range: Time range to query
        dimension_filter: Specific dimensions to include (None for all)
        min_confidence: Minimum confidence threshold
        include_trends: Whether to include trend analysis
    """
    user_id: str
    context_bucket: Optional[int] = None
    time_range: Optional[TimeRange] = None
    dimension_filter: Optional[List[str]] = None
    min_confidence: float = 0.0
    include_trends: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "user_id": self.user_id,
            "context_bucket": self.context_bucket,
            "dimension_filter": self.dimension_filter,
            "min_confidence": self.min_confidence,
            "include_trends": self.include_trends
        }
        
        if self.time_range:
            start, end = self.time_range.get_bounds()
            result["time_range"] = {
                "type": self.time_range.range_type.value,
                "start": start.isoformat(),
                "end": end.isoformat()
            }
        
        return result


class TemporalQueryBuilder:
    """
    Builder for constructing temporal queries.
    
    Provides a fluent interface for building complex temporal queries
    with filters, time ranges, and confidence thresholds.
    """
    
    def __init__(self):
        """Initialize the query builder."""
        self._user_id: Optional[str] = None
        self._context_bucket: Optional[int] = None
        self._time_range: Optional[TimeRange] = None
        self._dimension_filter: Optional[List[str]] = None
        self._min_confidence: float = 0.0
        self._include_trends: bool = False
        self._min_access_count: Optional[int] = None
        self._superseded_filter: Optional[bool] = None
    
    def for_user(self, user_id: str) -> "TemporalQueryBuilder":
        """Filter by user ID."""
        self._user_id = user_id
        return self
    
    def in_context(self, context_bucket: int) -> "TemporalQueryBuilder":
        """Filter by context bucket."""
        self._context_bucket = context_bucket
        return self
    
    def in_time_range(self, time_range: TimeRange) -> "TemporalQueryBuilder":
        """Filter by time range."""
        self._time_range = time_range
        return self
    
    def last_n_days(self, days: int) -> "TemporalQueryBuilder":
        """Filter to last N days."""
        self._time_range = TimeRange.relative(days)
        return self
    
    def at_time(self, timestamp: datetime) -> "TemporalQueryBuilder":
        """Query state at a specific point in time."""
        self._time_range = TimeRange.point(timestamp)
        return self
    
    def between(self, start: datetime, end: datetime) -> "TemporalQueryBuilder":
        """Filter to specific date range."""
        self._time_range = TimeRange.absolute(start, end)
        return self
    
    def with_dimensions(self, dimensions: List[str]) -> "TemporalQueryBuilder":
        """Filter to specific preference dimensions."""
        self._dimension_filter = dimensions
        return self
    
    def min_confidence(self, confidence: float) -> "TemporalQueryBuilder":
        """Filter by minimum confidence threshold."""
        self._min_confidence = confidence
        return self
    
    def min_access_count(self, count: int) -> "TemporalQueryBuilder":
        """Filter by minimum access count."""
        self._min_access_count = count
        return self
    
    def exclude_superseded(self) -> "TemporalQueryBuilder":
        """Exclude superseded memories."""
        self._superseded_filter = False
        return self
    
    def only_superseded(self) -> "TemporalQueryBuilder":
        """Include only superseded memories."""
        self._superseded_filter = True
        return self
    
    def include_trends(self) -> "TemporalQueryBuilder":
        """Include trend analysis in results."""
        self._include_trends = True
        return self
    
    def build_evolution_query(self) -> EvolutionQuery:
        """
        Build an evolution query.
        
        Returns:
            EvolutionQuery object
        """
        if not self._user_id:
            raise ValueError("User ID is required for evolution queries")
        
        return EvolutionQuery(
            user_id=self._user_id,
            context_bucket=self._context_bucket,
            time_range=self._time_range,
            dimension_filter=self._dimension_filter,
            min_confidence=self._min_confidence,
            include_trends=self._include_trends
        )
    
    def build_sql_filter(self, table_alias: str = "t") -> Tuple[str, List[Any]]:
        """
        Build SQL WHERE clause and parameters for this query.
        
        Args:
            table_alias: Table alias to use in SQL
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        conditions = []
        params = []
        
        # User filter
        if self._user_id:
            conditions.append(f"{table_alias}.user_id = ?")
            params.append(self._user_id)
        
        # Context filter
        if self._context_bucket is not None:
            conditions.append(f"{table_alias}.context_bucket = ?")
            params.append(self._context_bucket)
        
        # Time range filter
        if self._time_range:
            start, end = self._time_range.get_bounds()
            
            if self._time_range.range_type == TimeRangeType.POINT_IN_TIME:
                # For point-in-time, get records at or before the point
                conditions.append(f"{table_alias}.timestamp <= ?")
                params.append(start.isoformat())
            else:
                # For ranges, get records within the range
                conditions.append(f"{table_alias}.timestamp >= ?")
                conditions.append(f"{table_alias}.timestamp <= ?")
                params.append(start.isoformat())
                params.append(end.isoformat())
        
        # Confidence filter
        if self._min_confidence > 0:
            conditions.append(f"{table_alias}.confidence >= ?")
            params.append(self._min_confidence)
        
        # Access count filter
        if self._min_access_count is not None:
            conditions.append(f"{table_alias}.access_count >= ?")
            params.append(self._min_access_count)
        
        # Superseded filter
        if self._superseded_filter is not None:
            if self._superseded_filter:
                conditions.append(f"{table_alias}.superseded_by IS NOT NULL")
            else:
                conditions.append(f"{table_alias}.superseded_by IS NULL")
        
        # Build WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        return where_clause, params
    
    def build_chromadb_filter(self) -> Dict[str, Any]:
        """
        Build ChromaDB metadata filter for this query.
        
        Returns:
            Dictionary of metadata filters for ChromaDB
        """
        filters = {}
        
        # User filter
        if self._user_id:
            filters["user_id"] = self._user_id
        
        # Time range filter (ChromaDB supports comparison operators)
        if self._time_range:
            start, end = self._time_range.get_bounds()
            
            if self._time_range.range_type == TimeRangeType.POINT_IN_TIME:
                filters["created_at"] = {"$lte": start.isoformat()}
            else:
                filters["created_at"] = {
                    "$gte": start.isoformat(),
                    "$lte": end.isoformat()
                }
        
        # Confidence filter
        if self._min_confidence > 0:
            filters["confidence"] = {"$gte": self._min_confidence}
        
        return filters
    
    def reset(self) -> "TemporalQueryBuilder":
        """Reset the builder to initial state."""
        self.__init__()
        return self
