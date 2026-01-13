"""
Knowledge Graph Data Models

Dataclasses for knowledge graph entities (nodes and edges).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class KGNode:
    """Knowledge graph node model."""
    id: str
    user_id: str
    label: str
    properties: Dict[str, Any]
    confidence: float
    source_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    language: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_current: bool = True
    canonical_id: Optional[str] = None
    aliases_json: Optional[Dict[str, Any]] = None


@dataclass
class KGEdge:
    """Knowledge graph edge model."""
    id: str
    user_id: str
    source_id: str
    target_id: str
    relation_type: str
    source_text: str
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_current: bool = True
