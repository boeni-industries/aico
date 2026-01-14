"""
KG Property Data Models

Dataclasses for knowledge graph property entities.
"""

from dataclasses import dataclass


@dataclass
class KGNodeProperty:
    """KG node property model - matches kg_node_properties table."""
    node_id: str
    key: str
    value: str


@dataclass
class KGEdgeProperty:
    """KG edge property model - matches kg_edge_properties table."""
    edge_id: str
    key: str
    value: str
