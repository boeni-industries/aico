from __future__ import annotations

from pydantic import BaseModel


class KGNodeProperty(BaseModel):
    node_id: str
    key: str
    value: str


class KGEdgeProperty(BaseModel):
    edge_id: str
    key: str
    value: str
