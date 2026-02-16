"""
Coreference Resolution for Knowledge Graph

Resolves pronoun references to stable canonical entities:
- User pronouns (I, me, my) → user's PERSON entity
- AI pronouns (you, your) → AICO AI_SYSTEM entity

This ensures consistent entity representation across conversations.
"""

from typing import Dict, Optional, Set
from datetime import datetime, UTC
import uuid

from aico.core.logging import get_logger
from .models import Node, Edge, PropertyGraph

logger = get_logger("shared.ai.knowledge_graph.coreference")


# Multilingual pronoun patterns for user reference
USER_PRONOUNS = {
    # English
    "i", "me", "my", "mine", "myself",
    # German
    "ich", "mich", "mir", "mein", "meine",
    # French
    "je", "moi", "mon", "ma", "mes",
    # Spanish
    "yo", "mi", "mis",
    # Italian
    "io", "mi", "mio", "mia", "miei", "mie"
}

# Multilingual pronoun patterns for AI reference
AI_PRONOUNS = {
    # English
    "you", "your", "yours", "yourself",
    # German
    "du", "dich", "dir", "dein", "deine",
    # French
    "tu", "toi", "ton", "ta", "tes", "vous", "votre", "vos",
    # Spanish
    "tú", "tu", "tus",
    # Italian
    "tu", "ti", "tuo", "tua", "tuoi", "tue"
}


async def resolve_coreferences(
    graph: PropertyGraph,
    user_id: str,
    user_name: Optional[str],
    uow_factory
) -> PropertyGraph:
    """
    Resolve pronoun coreferences in graph to canonical entities.
    
    Args:
        graph: Input graph with potential pronouns
        user_id: User ID
        user_name: User's name (if known)
        uow_factory: UnitOfWork factory for DB access
        
    Returns:
        Graph with pronouns resolved to canonical entities
    """
    # Get or create canonical entities
    user_entity = await _get_or_create_user_entity(user_id, user_name, uow_factory)
    aico_entity = await _get_or_create_aico_entity(user_id, uow_factory)
    
    # Build pronoun mapping
    pronoun_to_entity = {}
    for pronoun in USER_PRONOUNS:
        pronoun_to_entity[pronoun] = user_entity.id
    for pronoun in AI_PRONOUNS:
        pronoun_to_entity[pronoun] = aico_entity.id
    
    # Replace pronoun nodes with entity references
    resolved_nodes = []
    node_id_mapping = {}  # old_id → new_id
    
    for node in graph.nodes:
        name = node.properties.get("name", "").strip().lower()
        
        if name in pronoun_to_entity:
            # Map to canonical entity
            target_id = pronoun_to_entity[name]
            node_id_mapping[node.id] = target_id
            logger.debug(f"Resolved pronoun '{name}' → entity {target_id}")
        else:
            # Keep original node
            resolved_nodes.append(node)
            node_id_mapping[node.id] = node.id
    
    # Update edge references
    resolved_edges = []
    for edge in graph.edges:
        new_source = node_id_mapping.get(edge.source_id, edge.source_id)
        new_target = node_id_mapping.get(edge.target_id, edge.target_id)
        
        # Skip self-loops
        if new_source == new_target:
            continue
        
        edge.source_id = new_source
        edge.target_id = new_target
        resolved_edges.append(edge)
    
    # Add canonical entities to graph if referenced
    referenced_ids = set()
    for edge in resolved_edges:
        referenced_ids.add(edge.source_id)
        referenced_ids.add(edge.target_id)
    
    if user_entity.id in referenced_ids and user_entity.id not in {n.id for n in resolved_nodes}:
        resolved_nodes.append(user_entity)
    
    if aico_entity.id in referenced_ids and aico_entity.id not in {n.id for n in resolved_nodes}:
        resolved_nodes.append(aico_entity)
    
    pronouns_resolved = len(graph.nodes) - len(resolved_nodes)
    if pronouns_resolved > 0:
        logger.info(f"Coreference resolution: {pronouns_resolved} pronouns resolved to canonical entities")
    
    return PropertyGraph(nodes=resolved_nodes, edges=resolved_edges)


async def _get_or_create_user_entity(
    user_id: str,
    user_name: Optional[str],
    uow_factory
) -> Node:
    """Get or create stable user entity."""
    # Try to find existing user entity
    async with uow_factory() as uow:
        nodes = await uow.kg_nodes.list(
            filters={
                "user_id": user_id,
                "label": "PERSON",
                "is_current": True
            },
            limit=100
        )
        
        # Find user's primary entity
        for node in nodes:
            if node.properties.get("is_user", False):
                # Update name if provided and different
                if user_name and node.properties.get("name") != user_name:
                    node.properties["name"] = user_name
                    node.updated_at = datetime.now(UTC).isoformat()
                    await uow.kg_nodes.update(node)
                    await uow.commit()
                    logger.info(f"Updated user entity name: {user_name}")
                return node
    
    # Create new user entity
    now = datetime.now(UTC).isoformat()
    user_entity = Node(
        id=f"user_{user_id}_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        label="PERSON",
        properties={
            "name": user_name or "User",
            "is_user": True,
            "description": "The user of this system"
        },
        confidence=1.0,
        source_text="System-generated user entity for coreference resolution",
        created_at=now,
        updated_at=now,
        is_current=1,
        canonical_id=None,
        aliases=[],
        language="en"
    )
    
    # Save to database
    async with uow_factory() as uow:
        await uow.kg_nodes.create(user_entity)
        await uow.commit()
    
    logger.info(f"Created user entity: {user_entity.id} (name={user_name})")
    return user_entity


async def _get_or_create_aico_entity(
    user_id: str,
    uow_factory
) -> Node:
    """Get or create stable AICO system entity."""
    # Try to find existing AICO entity
    async with uow_factory() as uow:
        nodes = await uow.kg_nodes.list(
            filters={
                "user_id": user_id,
                "label": "AI_SYSTEM",
                "is_current": True
            },
            limit=10
        )
        
        for node in nodes:
            if node.properties.get("is_ai", False):
                return node
    
    # Create new AICO entity
    now = datetime.now(UTC).isoformat()
    aico_entity = Node(
        id=f"aico_system_{user_id}_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        label="AI_SYSTEM",
        properties={
            "name": "AICO",
            "is_ai": True,
            "description": "AICO AI assistant system"
        },
        confidence=1.0,
        source_text="System-generated AI entity for coreference resolution",
        created_at=now,
        updated_at=now,
        is_current=1,
        canonical_id=None,
        aliases=["you", "AICO", "assistant"],
        language="en"
    )
    
    # Save to database
    async with uow_factory() as uow:
        await uow.kg_nodes.create(aico_entity)
        await uow.commit()
    
    logger.info(f"Created AICO entity: {aico_entity.id}")
    return aico_entity
