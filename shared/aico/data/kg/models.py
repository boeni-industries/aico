from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, field_validator


class KGNode(BaseModel):
    """Knowledge Graph Node (Persistence Model)."""
    id: str
    user_id: str
    label: str
    # IMPORTANT: Persist as a structured JSON object in Postgres (jsonb), not as a JSON-encoded string.
    # We still accept legacy string inputs (from older rows / callers) and parse them.
    properties: Dict[str, Any]
    confidence: float = 1.0
    source_text: Optional[str] = None

    created_at: Optional[Union[str, datetime]] = None
    updated_at: Optional[Union[str, datetime]] = None

    language: Optional[str] = None
    valid_from: Optional[Union[str, datetime]] = None
    valid_until: Optional[Union[str, datetime]] = None

    is_current: bool = True
    canonical_id: Optional[str] = None
    # Stored as jsonb in Postgres; keep structured type in Python.
    aliases_json: Optional[Union[List[str], Dict[str, Any]]] = None
    reason: Optional[str] = None
    embedding: Optional[list] = None  # Cached embedding for entity resolution

    @field_validator('properties', mode='before')
    @classmethod
    def parse_properties(cls, v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    @field_validator('aliases_json', mode='before')
    @classmethod
    def parse_aliases_json(cls, v):
        if v is None:
            return None
        if isinstance(v, (list, dict)):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (list, dict)):
                    return parsed
            except Exception:
                return None
        return None

    @field_validator('created_at', 'updated_at', 'valid_from', 'valid_until', mode='before')
    @classmethod
    def serialize_datetime(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class KGEdge(BaseModel):
    id: str
    user_id: str
    source_id: str
    target_id: str
    relation_type: str

    # Same rule as nodes: keep structured JSON in Python and Postgres.
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    source_text: Optional[str] = None

    created_at: Optional[Union[str, datetime]] = None
    updated_at: Optional[Union[str, datetime]] = None

    valid_from: Optional[Union[str, datetime]] = None
    valid_until: Optional[Union[str, datetime]] = None

    is_current: bool = True
    reason: Optional[str] = None
    reason: Optional[str] = None

    @field_validator('properties', mode='before')
    @classmethod
    def parse_properties(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None
        return None

    @field_validator('created_at', 'updated_at', 'valid_from', 'valid_until', mode='before')
    @classmethod
    def serialize_datetime(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class KGNodeProperty(BaseModel):
    node_id: str
    key: str
    value: str
    value_type: str = "string"


class KGEdgeProperty(BaseModel):
    edge_id: str
    key: str
    value: str
    value_type: str = "string"
