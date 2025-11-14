"""
Temporal Memory Module

Provides temporal metadata tracking, preference evolution, and time-aware queries
for AICO's Adaptive Memory System (AMS).

This module implements temporal intelligence for memory consolidation and
behavioral learning, enabling the system to understand how preferences and
behaviors evolve over time.
"""

from .metadata import (
    TemporalMetadata,
    EvolutionRecord,
    HistoricalState,
    PreferenceSnapshot
)
from .evolution import (
    EvolutionTracker,
    PreferenceEvolution,
    TrendAnalysis
)
from .queries import (
    TemporalQueryBuilder,
    TimeRange,
    EvolutionQuery
)

__all__ = [
    # Metadata structures
    "TemporalMetadata",
    "EvolutionRecord",
    "HistoricalState",
    "PreferenceSnapshot",
    # Evolution tracking
    "EvolutionTracker",
    "PreferenceEvolution",
    "TrendAnalysis",
    # Query support
    "TemporalQueryBuilder",
    "TimeRange",
    "EvolutionQuery",
]
