"""
Unified Memory Module

Provides unified indexing and retrieval across all memory tiers (L0/L1/L2).
Enables seamless memory access regardless of storage location.

This module provides:
- Cross-layer indexing (raw data, structured memory, parameterized memory)
- Unified retrieval interface
- Memory lifecycle management
- Tier transitions (working → semantic → archived)
"""

from .index import (
    UnifiedIndex,
    MemoryLayer,
    IndexEntry
)
from .lifecycle import (
    MemoryLifecycleManager,
    LifecycleStage,
    TransitionPolicy
)
from .retrieval import (
    UnifiedRetriever,
    RetrievalQuery,
    RetrievalResult
)

__all__ = [
    # Indexing
    "UnifiedIndex",
    "MemoryLayer",
    "IndexEntry",
    # Lifecycle
    "MemoryLifecycleManager",
    "LifecycleStage",
    "TransitionPolicy",
    # Retrieval
    "UnifiedRetriever",
    "RetrievalQuery",
    "RetrievalResult",
]
