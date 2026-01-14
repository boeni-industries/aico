from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, field_validator


class KGNode(BaseModel):
    """Knowledge Graph Node (Persistence Model)."""
    id: str
    user_id: str
    label: str
    properties: Union[str, Dict[str, Any]]
    confidence: float = 1.0
    source_text: Optional[str] = None

    created_at: Optional[Union[str, datetime]] = None
    updated_at: Optional[Union[str, datetime]] = None

    language: Optional[str] = None
    valid_from: Optional[Union[str, datetime]] = None
    valid_until: Optional[Union[str, datetime]] = None

    is_current: bool = True
    canonical_id: Optional[str] = None
    aliases_json: Optional[str] = None
    reason: Optional[str] = None

    @field_validator('properties', 'aliases_json', mode='before')
    @classmethod
    def serialize_dict(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v

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

    properties: Optional[Union[str, Dict[str, Any]]] = None
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
    def serialize_dict(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v

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
