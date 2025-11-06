"""
AICO Memory System (V2)

Fact-centric, privacy-preserving memory system for conversational AI providing
contextual awareness and simple, robust integration.

This V2 architecture uses TWO tiers only:
- Working Memory: Active session context (LMDB)
- Semantic/Knowledge Memory: Fact store with embeddings (ChromaDB)

All components follow AICO's local-first, privacy-by-design principles with
message bus integration for loose coupling and extensibility.
"""

from .manager import MemoryManager
from .working import WorkingMemoryStore
from .semantic import SemanticMemoryStore
from .context import ContextAssembler  # Uses context/ subdirectory

__all__ = [
    "MemoryManager",
    "WorkingMemoryStore", 
    "SemanticMemoryStore",
    "ContextAssembler",
]
