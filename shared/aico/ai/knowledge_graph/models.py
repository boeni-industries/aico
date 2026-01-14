"""
Property Graph Data Models

Core data structures for property graphs with temporal support.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
import json


@dataclass
class Node:
    """
    Property graph node (entity) with typed properties.
    
    Attributes:
        id: Unique node identifier (UUID)
        user_id: Owner user ID
        label: Node type (PERSON, EVENT, PROJECT, GOAL, etc.)
        properties: Arbitrary key-value properties (JSON-serializable)
        confidence: Extraction confidence (0-1)
        source_text: Original text this node was extracted from
        created_at: When node was created (ISO 8601)
        updated_at: When node was last updated (ISO 8601)
        language: Optional ISO/BCP-47 language code
        valid_from: When fact became true (event time, ISO 8601)
        valid_until: When fact stopped being true (event time, ISO 8601, None = current)
        is_current: Whether fact is currently valid (1 = current, 0 = historical)
        canonical_id: Stable ID across entity merges
        aliases: Known name variations
        aliases_json: JSON-serialized aliases for persistence layer compatibility
        reason: Optional reason for node creation/update
        embedding: Cached embedding from resolution
    """
    id: str
    user_id: str
    label: str
    properties: Dict[str, Any]
    confidence: float
    source_text: str
    created_at: str
    updated_at: str
    language: Optional[str] = None  # ISO/BCP-47 language code
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    is_current: int = 1
    canonical_id: Optional[str] = None
    aliases: Optional[List[str]] = None
    aliases_json: Optional[str] = None
    reason: Optional[str] = None
    embedding: Optional[List[float]] = None  # Cached embedding from resolution
    
    @classmethod
    def create(
        cls,
        user_id: str,
        label: str,
        properties: Dict[str, Any],
        confidence: float,
        source_text: str,
        language: Optional[str] = "en",
        valid_from: Optional[str] = None,
        canonical_id: Optional[str] = None,
        aliases: Optional[List[str]] = None
    ) -> 'Node':
        """Create new node with auto-generated ID and timestamps."""
        now = datetime.now(timezone.utc).isoformat()
        node_id = str(uuid.uuid4())
        
        return cls(
            id=node_id,
            user_id=user_id,
            label=label,
            properties=properties,
            confidence=confidence,
            source_text=source_text,
            created_at=now,
            updated_at=now,
            language=language,
            valid_from=valid_from or now,
            valid_until=None,
            is_current=1,
            canonical_id=canonical_id or node_id,
            aliases=aliases or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_chromadb_document(self) -> Dict[str, Any]:
        """Convert to ChromaDB document format."""
        # Combine all text fields for embedding
        text_content = f"{self.label}: {json.dumps(self.properties, sort_keys=True)} | {self.source_text}"
        
        return {
            "id": self.id,
            "document": text_content,
            "metadata": {
                "user_id": self.user_id,
                "label": self.label,
                "confidence": self.confidence,
                "created_at": self.created_at,
                "is_current": int(self.is_current),
                "canonical_id": self.canonical_id or self.id
            }
        }
    
    def to_postgres_tuple(self) -> tuple:
        """Convert to tuple for libSQL insertion."""
        return (
            self.id,
            self.user_id,
            self.label,
            json.dumps(self.properties, sort_keys=True),
            self.confidence,
            self.source_text,
            self.created_at,
            self.updated_at,
            self.language,
            self.valid_from,
            self.valid_until,
            self.is_current,
            self.canonical_id,
            json.dumps(self.aliases, sort_keys=True) if self.aliases else None
        )


@dataclass
class Edge:
    """
    Property graph edge (relationship) with typed properties.
    
    Attributes:
        id: Unique edge identifier (UUID)
        user_id: Owner user ID
        source_id: Source node ID
        target_id: Target node ID
        relation_type: Relationship type (HAS_SKILL, WORKS_ON, etc.)
        properties: Arbitrary key-value properties (JSON-serializable)
        confidence: Extraction confidence (0-1)
        source_text: Original text this edge was extracted from
        created_at: When edge was created (ISO 8601)
        updated_at: When edge was last updated (ISO 8601)
        valid_from: When relationship started (event time, ISO 8601)
        valid_until: When relationship ended (event time, ISO 8601, None = current)
        is_current: Whether relationship is currently valid (1 = current, 0 = historical)
        reason: Optional reason for edge creation/update
    """
    id: str
    user_id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any]
    confidence: float
    source_text: str
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    is_current: int = 1
    reason: Optional[str] = None
    embedding: Optional[List[float]] = None  # Cached embedding from resolution
    
    @classmethod
    def create(
        cls,
        user_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Dict[str, Any],
        confidence: float,
        source_text: str,
        valid_from: Optional[str] = None
    ) -> 'Edge':
        """Create new edge with auto-generated ID and timestamps."""
        now = datetime.now(timezone.utc).isoformat()
        edge_id = str(uuid.uuid4())
        
        return cls(
            id=edge_id,
            user_id=user_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties,
            confidence=confidence,
            source_text=source_text,
            created_at=now,
            updated_at=now,
            valid_from=valid_from or now,
            valid_until=None,
            is_current=1
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_chromadb_document(self) -> Dict[str, Any]:
        """Convert to ChromaDB document format."""
        # Combine all text fields for embedding
        text_content = f"{self.relation_type}: {json.dumps(self.properties, sort_keys=True)} | {self.source_text}"
        
        return {
            "id": self.id,
            "document": text_content,
            "metadata": {
                "user_id": self.user_id,
                "source_id": self.source_id,
                "target_id": self.target_id,
                "relation_type": self.relation_type,
                "confidence": self.confidence,
                "created_at": self.created_at,
                "is_current": int(self.is_current)
            }
        }
    
    def to_postgres_tuple(self) -> tuple:
        """Convert to tuple for libSQL insertion."""
        return (
            self.id,
            self.user_id,
            self.source_id,
            self.target_id,
            self.relation_type,
            json.dumps(self.properties, sort_keys=True),
            self.confidence,
            self.source_text,
            self.created_at,
            self.updated_at,
            self.valid_from,
            self.valid_until,
            self.is_current
        )


@dataclass
class PropertyGraph:
    """
    Property graph containing nodes and edges.
    
    Attributes:
        nodes: List of nodes in the graph
        edges: List of edges in the graph
    """
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    
    def add_node(self, node: Node) -> None:
        """Add node to graph with duplicate prevention."""
        # Check for duplicate by (label, properties)
        node_key = (node.label, json.dumps(node.properties, sort_keys=True))
        for existing_node in self.nodes:
            existing_key = (existing_node.label, json.dumps(existing_node.properties, sort_keys=True))
            if node_key == existing_key:
                # Duplicate found - keep the one with higher confidence
                if node.confidence > existing_node.confidence:
                    self.nodes.remove(existing_node)
                    self.nodes.append(node)
                return
        # Not a duplicate - add it
        self.nodes.append(node)
    
    def add_edge(self, edge: Edge) -> None:
        """Add edge to graph with duplicate prevention."""
        # Check for duplicate by (source_id, target_id, relation_type)
        edge_key = (edge.source_id, edge.target_id, edge.relation_type)
        for existing_edge in self.edges:
            existing_key = (existing_edge.source_id, existing_edge.target_id, existing_edge.relation_type)
            if edge_key == existing_key:
                # Duplicate found - keep the one with higher confidence
                if edge.confidence > existing_edge.confidence:
                    self.edges.remove(existing_edge)
                    self.edges.append(edge)
                return
        # Not a duplicate - add it
        self.edges.append(edge)
    
    def merge(self, other: 'PropertyGraph') -> None:
        """Merge another graph into this one with deduplication."""
        # Use add_node/add_edge to ensure deduplication
        for node in other.nodes:
            self.add_node(node)
        for edge in other.edges:
            self.add_edge(edge)
    
    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_nodes_by_label(self, label: str) -> List[Node]:
        """Get all nodes with specific label."""
        return [node for node in self.nodes if node.label == label]
    
    def get_edges_by_type(self, relation_type: str) -> List[Edge]:
        """Get all edges with specific relation type."""
        return [edge for edge in self.edges if edge.relation_type == relation_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges]
        }
    
    def __len__(self) -> int:
        """Return total number of nodes and edges."""
        return len(self.nodes) + len(self.edges)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PropertyGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
