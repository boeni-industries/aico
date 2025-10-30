"""
AICO Memory Context Assembly

Intelligent cross-tier memory context assembly for AI processing.

This module provides context assembly from multiple memory tiers:
- Working memory: Recent conversation context
- Episodic memory: Historical conversations
- Semantic memory: Knowledge base
- Procedural memory: User patterns and preferences

Public API:
    - ContextItem: Data model for context items
    - ContextAssembler: Main orchestrator for context assembly
"""

from .models import ContextItem
from .assembler import ContextAssembler

__all__ = [
    "ContextItem",
    "ContextAssembler",
]
