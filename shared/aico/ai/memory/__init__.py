"""
AICO Memory System

A modular, privacy-preserving memory system for conversational AI that provides
contextual awareness, thread resolution, and adaptive learning capabilities.

The memory system implements a four-tier architecture:
- Working Memory: Active session context (RocksDB)
- Episodic Memory: Conversation history (encrypted libSQL)
- Semantic Memory: Knowledge base with embeddings (ChromaDB)
- Procedural Memory: User patterns and behaviors (libSQL)

All components follow AICO's local-first, privacy-by-design principles with
message bus integration for loose coupling and extensibility.
"""

from .manager import MemoryManager
from .working import WorkingMemoryStore
from .episodic import EpisodicMemoryStore
from .semantic import SemanticMemoryStore
from .procedural import ProceduralMemoryStore
from .context import ContextAssembler
from .consolidation import MemoryConsolidator

__all__ = [
    "MemoryManager",
    "WorkingMemoryStore", 
    "EpisodicMemoryStore",
    "SemanticMemoryStore",
    "ProceduralMemoryStore",
    "ContextAssembler",
    "MemoryConsolidator"
]
