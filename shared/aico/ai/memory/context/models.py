"""
Context Data Models

Defines data structures for context assembly.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class ContextItem:
    """Individual context item with metadata"""
    content: str
    source_tier: str  # working, episodic, semantic, behavioral
    relevance_score: float
    timestamp: datetime
    metadata: Dict[str, Any]
    item_type: str  # message, knowledge, pattern, preference
