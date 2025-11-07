"""
Temporal Evolution Tracking

Tracks how preferences and behaviors evolve over time in AICO's memory system.
Provides trend analysis, preference shift detection, and future prediction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np

from .metadata import EvolutionRecord, PreferenceSnapshot, ChangeType
from aico.core.logging import get_logger

logger = get_logger("shared", "memory.temporal.evolution")


class TrendDirection(Enum):
    """Direction of a detected trend."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class TrendAnalysis:
    """
    Analysis of a temporal trend in preferences or behavior.
    
    Attributes:
        dimension_name: Name of the dimension being analyzed
        direction: Trend direction (increasing, decreasing, stable, volatile)
        magnitude: Magnitude of change (0.0 to 1.0)
        confidence: Confidence in this trend analysis
        start_value: Value at start of analysis period
        end_value: Value at end of analysis period
        sample_count: Number of data points analyzed
        timespan_days: Number of days covered by analysis
    """
    dimension_name: str
    direction: TrendDirection
    magnitude: float
    confidence: float
    start_value: float
    end_value: float
    sample_count: int
    timespan_days: int
    
    def is_significant(self, threshold: float = 0.2) -> bool:
        """
        Determine if this trend is significant.
        
        Args:
            threshold: Minimum magnitude to be considered significant
            
        Returns:
            True if trend is significant
        """
        return self.magnitude >= threshold and self.confidence >= 0.7


@dataclass
class PreferenceEvolution:
    """
    Complete evolution history of user preferences in a context.
    
    Tracks how preferences change over time, enabling the system to
    understand preference shifts and adapt accordingly.
    
    Attributes:
        user_id: User this evolution applies to
        context_bucket: Context bucket (hash of intent + sentiment + time_of_day)
        snapshots: Chronological list of preference snapshots
        trends: Detected trends per dimension
        last_analyzed: When trend analysis was last performed
    """
    user_id: str
    context_bucket: int
    snapshots: List[PreferenceSnapshot] = field(default_factory=list)
    trends: Dict[str, TrendAnalysis] = field(default_factory=dict)
    last_analyzed: Optional[datetime] = None
    
    def add_snapshot(self, snapshot: PreferenceSnapshot) -> None:
        """Add a new preference snapshot."""
        self.snapshots.append(snapshot)
        # Keep snapshots sorted by timestamp
        self.snapshots.sort(key=lambda s: s.timestamp)
    
    def get_current_preferences(self) -> Optional[PreferenceSnapshot]:
        """Get the most recent preference snapshot."""
        return self.snapshots[-1] if self.snapshots else None
    
    def get_preferences_at_time(self, timestamp: datetime) -> Optional[PreferenceSnapshot]:
        """
        Get preferences as they were at a specific time.
        
        Args:
            timestamp: Point in time to query
            
        Returns:
            Preference snapshot at or before the given time, or None
        """
        # Find the most recent snapshot before or at the given time
        for snapshot in reversed(self.snapshots):
            if snapshot.timestamp <= timestamp:
                return snapshot
        return None
    
    def detect_preference_shift(
        self,
        lookback_days: int = 30,
        threshold: float = 0.3
    ) -> List[Tuple[int, float]]:
        """
        Detect significant preference shifts in recent history.
        
        Args:
            lookback_days: Number of days to look back
            threshold: Minimum change to be considered a shift
            
        Returns:
            List of (dimension_index, change_magnitude) tuples for shifted dimensions
        """
        if len(self.snapshots) < 2:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(days=lookback_days)
        recent_snapshots = [s for s in self.snapshots if s.timestamp >= cutoff_time]
        
        if len(recent_snapshots) < 2:
            return []
        
        # Compare first and last snapshots in the period
        first = recent_snapshots[0]
        last = recent_snapshots[-1]
        
        shifts = []
        for i in range(len(first.preference_vector)):
            change = abs(last.preference_vector[i] - first.preference_vector[i])
            if change >= threshold:
                shifts.append((i, change))
        
        return shifts


class EvolutionTracker:
    """
    Tracks and analyzes preference evolution over time.
    
    Provides methods for recording preference changes, analyzing trends,
    and predicting future preferences based on historical patterns.
    """
    
    # Dimension names for preference vectors (16 dimensions)
    DIMENSION_NAMES = [
        "verbosity",
        "formality",
        "technical_depth",
        "proactivity",
        "emotional_expression",
        "structure",
        "explanation_depth",
        "example_usage",
        "question_asking",
        "reassurance_level",
        "directness",
        "enthusiasm",
        "patience",
        "creativity",
        "reserved_1",
        "reserved_2"
    ]
    
    def __init__(self):
        """Initialize the evolution tracker."""
        self.evolutions: Dict[Tuple[str, int], PreferenceEvolution] = {}
    
    def track_evolution(
        self,
        user_id: str,
        context_bucket: int,
        preference_vector: List[float],
        confidence: float,
        sample_count: int
    ) -> None:
        """
        Record a preference snapshot for evolution tracking.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            preference_vector: 16-dimensional preference vector
            confidence: Confidence in these preferences
            sample_count: Number of interactions that informed these preferences
        """
        key = (user_id, context_bucket)
        
        if key not in self.evolutions:
            self.evolutions[key] = PreferenceEvolution(
                user_id=user_id,
                context_bucket=context_bucket
            )
        
        snapshot = PreferenceSnapshot(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            context_bucket=context_bucket,
            preference_vector=preference_vector,
            confidence=confidence,
            sample_count=sample_count
        )
        
        self.evolutions[key].add_snapshot(snapshot)
        
        logger.debug("Preference snapshot recorded", extra={
            "user_id": user_id,
            "context_bucket": context_bucket,
            "confidence": confidence,
            "sample_count": sample_count
        })
    
    def analyze_trends(
        self,
        user_id: str,
        context_bucket: int,
        lookback_days: int = 30
    ) -> Dict[str, TrendAnalysis]:
        """
        Analyze preference trends over a time period.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            lookback_days: Number of days to analyze
            
        Returns:
            Dictionary mapping dimension names to trend analyses
        """
        key = (user_id, context_bucket)
        
        if key not in self.evolutions:
            return {}
        
        evolution = self.evolutions[key]
        cutoff_time = datetime.utcnow() - timedelta(days=lookback_days)
        recent_snapshots = [s for s in evolution.snapshots if s.timestamp >= cutoff_time]
        
        if len(recent_snapshots) < 2:
            return {}
        
        trends = {}
        
        for dim_idx, dim_name in enumerate(self.DIMENSION_NAMES):
            trend = self._analyze_dimension_trend(recent_snapshots, dim_idx, dim_name)
            if trend:
                trends[dim_name] = trend
        
        evolution.trends = trends
        evolution.last_analyzed = datetime.utcnow()
        
        logger.info("Trend analysis complete", extra={
            "user_id": user_id,
            "context_bucket": context_bucket,
            "trends_detected": len(trends),
            "lookback_days": lookback_days
        })
        
        return trends
    
    def _analyze_dimension_trend(
        self,
        snapshots: List[PreferenceSnapshot],
        dimension_index: int,
        dimension_name: str
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trend for a single dimension.
        
        Args:
            snapshots: List of preference snapshots
            dimension_index: Index of dimension to analyze
            dimension_name: Name of dimension
            
        Returns:
            TrendAnalysis or None if insufficient data
        """
        if len(snapshots) < 2:
            return None
        
        values = [s.preference_vector[dimension_index] for s in snapshots]
        start_value = values[0]
        end_value = values[-1]
        
        # Calculate linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple linear regression
        slope = np.polyfit(x, y, 1)[0]
        
        # Calculate variance to detect volatility
        variance = np.var(values)
        
        # Determine direction
        if variance > 0.1:  # High variance indicates volatility
            direction = TrendDirection.VOLATILE
        elif abs(slope) < 0.01:  # Minimal change
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
        
        # Calculate magnitude and confidence
        magnitude = abs(end_value - start_value)
        confidence = min(1.0, len(snapshots) / 10.0)  # More samples = higher confidence
        
        timespan_days = (snapshots[-1].timestamp - snapshots[0].timestamp).days
        
        return TrendAnalysis(
            dimension_name=dimension_name,
            direction=direction,
            magnitude=magnitude,
            confidence=confidence,
            start_value=start_value,
            end_value=end_value,
            sample_count=len(snapshots),
            timespan_days=timespan_days
        )
    
    def predict_future_preferences(
        self,
        user_id: str,
        context_bucket: int,
        days_ahead: int = 7
    ) -> Optional[List[float]]:
        """
        Predict future preferences based on historical trends.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            days_ahead: Number of days to predict ahead
            
        Returns:
            Predicted 16-dimensional preference vector, or None if insufficient data
        """
        key = (user_id, context_bucket)
        
        if key not in self.evolutions:
            return None
        
        evolution = self.evolutions[key]
        current = evolution.get_current_preferences()
        
        if not current or len(evolution.snapshots) < 3:
            return None  # Need at least 3 snapshots for prediction
        
        # Use recent snapshots for prediction
        recent = evolution.snapshots[-5:]  # Last 5 snapshots
        
        predicted = []
        for dim_idx in range(16):
            values = [s.preference_vector[dim_idx] for s in recent]
            
            # Simple linear extrapolation
            x = np.arange(len(values))
            y = np.array(values)
            slope, intercept = np.polyfit(x, y, 1)
            
            # Predict value at days_ahead
            future_x = len(values) + (days_ahead / 7.0)  # Normalize to snapshot intervals
            predicted_value = slope * future_x + intercept
            
            # Clamp to [0, 1] range
            predicted_value = max(0.0, min(1.0, predicted_value))
            predicted.append(predicted_value)
        
        logger.debug("Future preferences predicted", extra={
            "user_id": user_id,
            "context_bucket": context_bucket,
            "days_ahead": days_ahead
        })
        
        return predicted
    
    def get_evolution_history(
        self,
        user_id: str,
        context_bucket: int
    ) -> Optional[PreferenceEvolution]:
        """
        Get complete evolution history for a user in a context.
        
        Args:
            user_id: User ID
            context_bucket: Context bucket
            
        Returns:
            PreferenceEvolution or None if no history exists
        """
        key = (user_id, context_bucket)
        return self.evolutions.get(key)
