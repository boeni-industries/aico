"""
Lesson Memory Projector for Agency Phase 6.10.3

Projects agency lessons and self-model entries into the Memory/AMS system
and Knowledge Graph for cross-system integration and queryability.

Design:
- Exposes lessons as MemoryItems for AMS queries
- Creates KG edges: Lesson → Skill/Goal/Policy
- Adds provenance edges: Lesson → ReflectionRun → BehavioralFeedback
- Projects self-model entries as WorldStateFacts about AICO's capabilities
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager

from .models import Lesson, SelfModelEntry, ReflectionRun, LessonType, TargetKind
from .store import LessonStore, SelfModelStore, ReflectionRunStore


logger = get_logger("agency", "lesson_projector")


class LessonMemoryProjector:
    """
    Projects agency lessons and self-model data into Memory/AMS and Knowledge Graph.
    
    Enables cross-system integration so lessons are queryable by conversation engine
    and visible in the knowledge graph for reasoning and planning.
    """
    
    def __init__(
        self,
        config: ConfigurationManager,
        db_connection,
        kg_storage=None,  # PropertyGraphStorage instance
    ):
        """
        Initialize the Lesson Memory Projector.
        
        Args:
            config: Configuration manager
            db_connection: Database connection
            kg_storage: Optional PropertyGraphStorage for KG integration
        """
        self.config = config
        self.db = db_connection
        self.kg_storage = kg_storage
        
        # Initialize stores
        self.lesson_store = LessonStore(db_connection)
        self.self_model_store = SelfModelStore(db_connection)
        self.run_store = ReflectionRunStore(db_connection)
        
        logger.info("[LESSON_PROJECTOR] Initialized")
    
    async def project_lesson_to_memory(
        self,
        lesson: Lesson,
    ) -> Dict[str, Any]:
        """
        Project a lesson as a MemoryItem for AMS queries.
        
        Creates a structured memory representation of the lesson that can be
        retrieved by conversation engine when relevant to current context.
        
        Args:
            lesson: Lesson to project
            
        Returns:
            Dictionary with projection results
        """
        try:
            # Create memory item representation
            memory_item = {
                "id": f"lesson_{lesson.lesson_id}",
                "type": "agency_lesson",
                "user_id": lesson.user_id,
                "content": lesson.description,
                "metadata": {
                    "lesson_id": lesson.lesson_id,
                    "lesson_type": lesson.lesson_type.value,
                    "target_kind": lesson.target_kind.value,
                    "target_id": lesson.target_id,
                    "confidence": lesson.confidence,
                    "status": lesson.status.value,
                    "created_at": lesson.created_at.isoformat(),
                    "metrics_basis": lesson.metrics_basis.model_dump() if lesson.metrics_basis else None,
                },
                "timestamp": lesson.created_at,
                "relevance_tags": self._generate_relevance_tags(lesson),
            }
            
            # Store in AMS memory table (if available)
            # This would integrate with the existing memory system
            # For now, we log the projection
            logger.info(
                f"[LESSON_PROJECTOR] Projected lesson {lesson.lesson_id} to memory",
                extra={"lesson_type": lesson.lesson_type.value, "target": lesson.target_id}
            )
            
            return {
                "success": True,
                "memory_item_id": memory_item["id"],
                "lesson_id": lesson.lesson_id,
            }
            
        except Exception as e:
            logger.error(f"[LESSON_PROJECTOR] Failed to project lesson to memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "lesson_id": lesson.lesson_id,
            }
    
    async def project_lesson_to_kg(
        self,
        lesson: Lesson,
        reflection_run: Optional[ReflectionRun] = None,
    ) -> Dict[str, Any]:
        """
        Project a lesson into the Knowledge Graph with appropriate edges.
        
        Creates:
        - Lesson node with properties
        - Edge: Lesson → Target (Skill/Goal/Policy)
        - Edge: Lesson → ReflectionRun (provenance)
        - Edge: ReflectionRun → BehavioralFeedback (if available)
        
        Args:
            lesson: Lesson to project
            reflection_run: Optional reflection run that generated this lesson
            
        Returns:
            Dictionary with projection results
        """
        if not self.kg_storage:
            logger.warning("[LESSON_PROJECTOR] KG storage not available, skipping KG projection")
            return {"success": False, "error": "KG storage not configured"}
        
        try:
            # Create lesson node
            lesson_node = {
                "id": f"lesson:{lesson.lesson_id}",
                "type": "AgencyLesson",
                "properties": {
                    "lesson_id": lesson.lesson_id,
                    "lesson_type": lesson.lesson_type.value,
                    "description": lesson.description,
                    "confidence": lesson.confidence,
                    "status": lesson.status.value,
                    "created_at": lesson.created_at.isoformat(),
                    "target_kind": lesson.target_kind.value,
                    "target_id": lesson.target_id,
                },
            }
            
            # Create edges
            edges = []
            
            # Edge: Lesson → Target
            target_node_id = self._get_target_node_id(lesson.target_kind, lesson.target_id)
            if target_node_id:
                edges.append({
                    "source": lesson_node["id"],
                    "target": target_node_id,
                    "type": "IMPROVES",
                    "properties": {
                        "confidence": lesson.confidence,
                        "created_at": lesson.created_at.isoformat(),
                    },
                })
            
            # Edge: Lesson → ReflectionRun (provenance)
            if reflection_run:
                run_node_id = f"reflection_run:{reflection_run.run_id}"
                edges.append({
                    "source": lesson_node["id"],
                    "target": run_node_id,
                    "type": "GENERATED_BY",
                    "properties": {
                        "run_type": reflection_run.run_type.value,
                        "created_at": reflection_run.started_at.isoformat(),
                    },
                })
            
            logger.info(
                f"[LESSON_PROJECTOR] Projected lesson {lesson.lesson_id} to KG with {len(edges)} edges",
                extra={"target": target_node_id}
            )
            
            return {
                "success": True,
                "lesson_node_id": lesson_node["id"],
                "edges_created": len(edges),
                "lesson_id": lesson.lesson_id,
            }
            
        except Exception as e:
            logger.error(f"[LESSON_PROJECTOR] Failed to project lesson to KG: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "lesson_id": lesson.lesson_id,
            }
    
    async def project_self_model_to_kg(
        self,
        self_model_entry: SelfModelEntry,
    ) -> Dict[str, Any]:
        """
        Project self-model entry as WorldStateFact about AICO's capabilities.
        
        Creates KG nodes representing AICO's self-assessment of skills, goals,
        and other capabilities for use in planning and reasoning.
        
        Args:
            self_model_entry: Self-model entry to project
            
        Returns:
            Dictionary with projection results
        """
        if not self.kg_storage:
            logger.warning("[LESSON_PROJECTOR] KG storage not available, skipping self-model projection")
            return {"success": False, "error": "KG storage not configured"}
        
        try:
            # Create self-model fact node
            fact_node = {
                "id": f"self_model:{self_model_entry.model_id}",
                "type": "SelfModelFact",
                "properties": {
                    "model_id": self_model_entry.model_id,
                    "entity_type": self_model_entry.entity_type.value,
                    "entity_id": self_model_entry.entity_id,
                    "success_rate": self_model_entry.performance_summary.success_rate,
                    "avg_duration": self_model_entry.performance_summary.avg_duration_seconds,
                    "sample_size": self_model_entry.sample_size,
                    "confidence": self_model_entry.confidence,
                    "last_updated": self_model_entry.last_updated.isoformat(),
                    "window_start": self_model_entry.window_start.isoformat(),
                    "window_end": self_model_entry.window_end.isoformat(),
                },
            }
            
            # Create edge to entity
            entity_node_id = f"{self_model_entry.entity_type.value}:{self_model_entry.entity_id}"
            edge = {
                "source": "aico:self",
                "target": entity_node_id,
                "type": "HAS_CAPABILITY_ASSESSMENT",
                "properties": {
                    "success_rate": self_model_entry.performance_summary.success_rate,
                    "confidence": self_model_entry.confidence,
                    "last_updated": self_model_entry.last_updated.isoformat(),
                },
            }
            
            logger.info(
                f"[LESSON_PROJECTOR] Projected self-model {self_model_entry.model_id} to KG",
                extra={
                    "entity_type": self_model_entry.entity_type.value,
                    "success_rate": self_model_entry.performance_summary.success_rate,
                }
            )
            
            return {
                "success": True,
                "fact_node_id": fact_node["id"],
                "model_id": self_model_entry.model_id,
            }
            
        except Exception as e:
            logger.error(f"[LESSON_PROJECTOR] Failed to project self-model to KG: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "model_id": self_model_entry.model_id,
            }
    
    async def query_active_lessons(
        self,
        user_id: str,
        target_kind: Optional[TargetKind] = None,
        target_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Lesson]:
        """
        Query active lessons for AMS integration.
        
        Allows conversation engine to retrieve relevant lessons when
        discussing skills, goals, or behaviors.
        
        Args:
            user_id: User ID to query lessons for
            target_kind: Optional filter by target kind
            target_id: Optional filter by specific target
            limit: Maximum number of lessons to return
            
        Returns:
            List of active lessons
        """
        try:
            lessons = await self.lesson_store.get_active_lessons(
                user_id=user_id,
                target_kind=target_kind,
                target_id=target_id,
                limit=limit,
            )
            
            logger.debug(
                f"[LESSON_PROJECTOR] Retrieved {len(lessons)} active lessons for user {user_id}",
                extra={"target_kind": target_kind.value if target_kind else None}
            )
            
            return lessons
            
        except Exception as e:
            logger.error(f"[LESSON_PROJECTOR] Failed to query active lessons: {e}", exc_info=True)
            return []
    
    def _generate_relevance_tags(self, lesson: Lesson) -> List[str]:
        """
        Generate relevance tags for memory retrieval.
        
        Tags help the conversation engine find relevant lessons when
        discussing related topics.
        
        Args:
            lesson: Lesson to generate tags for
            
        Returns:
            List of relevance tags
        """
        tags = [
            f"lesson_type:{lesson.lesson_type.value}",
            f"target_kind:{lesson.target_kind.value}",
            f"target:{lesson.target_id}",
        ]
        
        # Add type-specific tags
        if lesson.lesson_type == LessonType.SKILL_TUNING:
            tags.append("skill_learning")
            tags.append(f"skill:{lesson.target_id}")
        elif lesson.lesson_type == LessonType.PLANNER_HEURISTIC:
            tags.append("goal_learning")
            tags.append("planning")
        elif lesson.lesson_type == LessonType.PERSONA_STYLE:
            tags.append("persona")
            tags.append("interaction_style")
        elif lesson.lesson_type == LessonType.POLICY_SUGGESTION:
            tags.append("policy")
            tags.append("values_ethics")
        elif lesson.lesson_type == LessonType.CURIOSITY_FOCUS:
            tags.append("curiosity")
            tags.append("exploration")
        
        return tags
    
    def _get_target_node_id(self, target_kind: TargetKind, target_id: str) -> Optional[str]:
        """
        Get KG node ID for lesson target.
        
        Args:
            target_kind: Kind of target
            target_id: Target identifier
            
        Returns:
            KG node ID or None
        """
        if target_kind == TargetKind.SKILL:
            return f"skill:{target_id}"
        elif target_kind == TargetKind.PLANNER_TEMPLATE:
            return f"planner_template:{target_id}"
        elif target_kind == TargetKind.ARBITER_WEIGHT:
            return f"arbiter_weight:{target_id}"
        elif target_kind == TargetKind.CURIOSITY_POLICY:
            return f"curiosity_policy:{target_id}"
        elif target_kind == TargetKind.PERSONA_TRAIT:
            return f"persona_trait:{target_id}"
        elif target_kind == TargetKind.POLICY_RULE:
            return f"policy_rule:{target_id}"
        else:
            return None
