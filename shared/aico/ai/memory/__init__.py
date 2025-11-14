"""
AICO Memory System with Adaptive Memory System (AMS)

Fact-centric, privacy-preserving memory system for conversational AI providing
contextual awareness, temporal intelligence, and behavioral learning.

Architecture:
- Working Memory: Active session context (LMDB) with temporal metadata
- Semantic/Knowledge Memory: Fact store with embeddings (ChromaDB) and evolution tracking
- Consolidation: Brain-inspired memory transfer during idle periods
- Behavioral Learning: Skill-based interaction with RLHF
- Unified Indexing: Cross-layer memory access (L0/L1/L2)

All components follow AICO's local-first, privacy-by-design principles with
message bus integration for loose coupling and extensibility.
"""

from .manager import MemoryManager
from .working import WorkingMemoryStore
from .semantic import SemanticMemoryStore
from .context import ContextAssembler  # Uses context/ subdirectory

# AMS modules (Phase 1+)
from . import temporal
from . import consolidation
from . import behavioral
from . import unified

__all__ = [
    # Core memory components
    "MemoryManager",
    "WorkingMemoryStore", 
    "SemanticMemoryStore",
    "ContextAssembler",
    # AMS modules
    "temporal",
    "consolidation",
    "behavioral",
    "unified",
]
