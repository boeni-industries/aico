"""
Memory Consolidation Module

Implements brain-inspired memory consolidation for AICO's Adaptive Memory System.
Transfers experiences from working memory to semantic memory during idle periods,
similar to how the mammalian brain consolidates memories during sleep.

This module provides:
- Idle detection and consolidation scheduling
- Experience replay with prioritization
- Memory reconsolidation (updating existing memories)
- Consolidation state tracking
"""

from .scheduler import (
    ConsolidationScheduler,
    IdleDetector,
    ConsolidationJob
)
from .replay import (
    ExperienceReplay,
    ReplaySequence,
    ExperiencePriority
)
from .reconsolidation import (
    MemoryReconsolidator,
    ConflictResolution,
    VariantManager
)
from .state import (
    ConsolidationState,
    ConsolidationStatus,
    ConsolidationProgress
)

__all__ = [
    # Scheduling
    "ConsolidationScheduler",
    "IdleDetector",
    "ConsolidationJob",
    # Replay
    "ExperienceReplay",
    "ReplaySequence",
    "ExperiencePriority",
    # Reconsolidation
    "MemoryReconsolidator",
    "ConflictResolution",
    "VariantManager",
    # State tracking
    "ConsolidationState",
    "ConsolidationStatus",
    "ConsolidationProgress",
]
