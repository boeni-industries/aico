"""
Knowledge Graph Update Skill

Updates the knowledge graph with new entities and relationships.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger
from aico.ai.knowledge_graph.models import Node, PropertyGraph


logger = get_logger("shared.ai.agency.skills.knowledge.graph")


class UpdateKnowledgeGraphSkill(Skill):
    """
    Update knowledge graph with new facts and relationships.
    
    Used for: Knowledge Graph Curation goals
    """
    
    def __init__(self, kg_storage: Optional[Any] = None):
        self.kg_storage = kg_storage
    
    @property
    def skill_id(self) -> str:
        return "update_knowledge_graph"
    
    @property
    def name(self) -> str:
        return "Update Knowledge Graph"
    
    @property
    def description(self) -> str:
        return "Add or update facts and relationships in the knowledge graph"
    
    @property
    def category(self) -> str:
        return "knowledge"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="entities",
                type=SkillParameterType.ARRAY,
                description="Entities to add/update",
                required=True,
            ),
            SkillParameter(
                name="relationships",
                type=SkillParameterType.ARRAY,
                description="Relationships between entities",
                required=False,
                default=[],
            ),
            SkillParameter(
                name="source",
                type=SkillParameterType.STRING,
                description="Source of the information",
                required=False,
                default="conversation",
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute knowledge graph update."""
        entities = input_data.get("entities", [])
        relationships = input_data.get("relationships", [])
        source = input_data.get("source", "conversation")
        
        logger.info(
            f"📊 [UPDATE_KNOWLEDGE_GRAPH] Updating knowledge graph for user {user_id[:8]}... "
            f"entities={len(entities)} relationships={len(relationships)} source={source}"
        )
        
        try:
            if not self.kg_storage:
                raise RuntimeError("Knowledge graph storage not available")

            now = datetime.now(UTC).isoformat()
            entities_added = 0
            relationships_added = 0

            # Build Node objects for entities
            nodes: List[Node] = []
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get("type", "unknown")
                    entity_value = entity.get("value", "")
                    entity_metadata = entity.get("metadata", {})
                else:
                    entity_type = "unknown"
                    entity_value = str(entity)
                    entity_metadata = {}

                node_id = str(uuid.uuid4())
                properties = {"value": entity_value, **entity_metadata, "source": source}

                node = Node(
                    id=node_id,
                    user_id=user_id,
                    label=entity_type,
                    properties=properties,
                    is_current=True,
                    created_at=now,
                    updated_at=now,
                )
                nodes.append(node)
                entities_added += 1

            # For now, relationships are not fully materialized; they will be
            # handled by higher-level extraction/fusion components.

            graph = PropertyGraph(nodes=nodes, edges=[])

            # Save entire graph via PropertyGraphStorage (dual-write to Postgres + ChromaDB)
            await self.kg_storage.save_graph(graph)
            
            result = {
                "entities_added": entities_added,
                "relationships_added": relationships_added,
                "source": source,
                "entities": entities,
                "relationships": relationships,
                "updated_at": now,
            }
            
            logger.info(
                f"📊 [UPDATE_KNOWLEDGE_GRAPH] Updated: "
                f"{entities_added} entities, "
                f"{relationships_added} relationships"
            )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.now(UTC).isoformat(),
                },
            )
            
        except Exception as e:
            logger.exception(
                f"📊 [UPDATE_KNOWLEDGE_GRAPH] Update failed: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Knowledge graph update failed: {str(e)}",
            )
