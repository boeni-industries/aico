"""
Knowledge Graph Module

Property graph implementation for structured memory and relationship intelligence.
Provides entity extraction, deduplication, and graph-based reasoning.

Public API:
    - PropertyGraph, Node, Edge: Core data models
    - PropertyGraphStorage: Hybrid ChromaDB + libSQL storage
    - MultiPassExtractor: Multi-pass extraction with gleanings
    - EntityResolver: Semantic entity resolution
    - GraphFusion: Graph fusion with conflict resolution

Usage Example:
    ```python
    from aico.ai.knowledge_graph import (
        PropertyGraphStorage,
        MultiPassExtractor,
        EntityResolver,
        GraphFusion
    )
    
    # Initialize components
    storage = PropertyGraphStorage(db_connection, chromadb_client)
    extractor = MultiPassExtractor(modelservice, config)
    resolver = EntityResolver(modelservice, config)
    fusion = GraphFusion(modelservice, config)
    
    # Extract knowledge from text
    new_graph = await extractor.extract(text, user_id)
    
    # Resolve entities (deduplicate)
    existing_nodes = await storage.get_user_nodes(user_id)
    resolved_graph = await resolver.resolve(new_graph, user_id, existing_nodes)
    
    # Fuse with existing graph
    existing_graph = await storage.get_user_graph(user_id)
    fused_graph = await fusion.fuse(resolved_graph, existing_graph)
    
    # Save to storage
    await storage.save_graph(fused_graph)
    ```
"""

from .models import Node, Edge, PropertyGraph
from .storage import PropertyGraphStorage
from .extractor import MultiPassExtractor
from .entity_resolution import EntityResolver
from .fusion import GraphFusion

__all__ = [
    # Data models
    "Node",
    "Edge", 
    "PropertyGraph",
    
    # Core components
    "PropertyGraphStorage",
    "MultiPassExtractor",
    "EntityResolver",
    "GraphFusion",
]
