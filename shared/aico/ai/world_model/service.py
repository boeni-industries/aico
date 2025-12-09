"""
World Model Service

Unified API for querying knowledge graph and semantic memory.
Provides contextual awareness for agency, planning, and curiosity systems.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from aico.core.logging import get_logger
from aico.ai.knowledge_graph import PropertyGraphStorage
from aico.ai.memory import SemanticMemoryStore, MemoryManager

from .models import (
    UserContext,
    OpenLoop,
    WorldContext,
    Entity,
    Project,
    Context,
    UncertainArea,
)


logger = get_logger("shared", "world_model.service")


class WorldModelService:
    """
    World Model Service provides unified access to knowledge graph and memory.
    
    Phase 2: Basic queries for entities, projects, open loops, and contexts.
    Later phases: Advanced reasoning, hypothesis testing, drift detection.
    """
    
    def __init__(
        self,
        kg_storage: PropertyGraphStorage,
        semantic_memory: SemanticMemoryStore,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """Initialize world model service.
        
        Args:
            kg_storage: Knowledge graph storage
            semantic_memory: Semantic memory store
            memory_manager: Optional memory manager for AMS integration
        """
        self.kg = kg_storage
        self.semantic_memory = semantic_memory
        self.memory_manager = memory_manager
        logger.info("[WORLD_MODEL] Service initialized")
    
    async def get_user_context(self, user_id: str) -> UserContext:
        """Get comprehensive user context.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserContext with projects, preferences, and relationship info
        """
        try:
            # Get active projects
            projects = await self.get_active_projects(user_id)
            
            # Get recent topics from semantic memory
            recent_topics = await self._get_recent_topics(user_id, limit=10)
            
            # Get user preferences (placeholder for now)
            preferences = await self._get_user_preferences(user_id)
            
            # Get relationship closeness (placeholder for now)
            relationship_closeness = await self._get_relationship_closeness(user_id)
            
            # Get last interaction time
            last_interaction = await self._get_last_interaction(user_id)
            
            # Get primary language
            primary_language = await self._get_primary_language(user_id)
            
            return UserContext(
                user_id=user_id,
                active_projects=projects,
                preferences=preferences,
                recent_topics=recent_topics,
                relationship_closeness=relationship_closeness,
                last_interaction=last_interaction,
                primary_language=primary_language,
            )
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get user context: {e}")
            # Return minimal context on error
            return UserContext(user_id=user_id)
    
    async def get_entities_around_user(
        self,
        user_id: str,
        limit: int = 20,
        entity_types: Optional[List[str]] = None,
    ) -> List[Entity]:
        """Get entities related to user from knowledge graph.
        
        Args:
            user_id: User identifier
            limit: Maximum number of entities to return
            entity_types: Optional filter for entity types
            
        Returns:
            List of entities related to the user
        """
        try:
            # Query KG for user-related entities using existing get_user_nodes method
            nodes = await self.kg.get_user_nodes(
                user_id=user_id,
                label=None,  # No label filter for now
                limit=limit,
            )
            
            entities = []
            for node in nodes:
                # Filter by entity type if specified
                if entity_types and node.entity_type not in entity_types:
                    continue
                    
                entity = Entity(
                    id=node.id,
                    label=node.label,
                    entity_type=node.entity_type,
                    properties=node.properties,
                    confidence=node.confidence,
                    last_mentioned=node.updated_at,
                )
                entities.append(entity)
                
                if len(entities) >= limit:
                    break
            
            logger.debug(f"[WORLD_MODEL] Found {len(entities)} entities for user {user_id}")
            return entities
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get entities: {e}")
            return []
    
    async def get_active_projects(self, user_id: str) -> List[Project]:
        """Get user's active projects from knowledge graph.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active projects
        """
        try:
            # Query KG for project-type entities using existing method
            project_nodes = await self.kg.get_user_nodes(
                user_id=user_id,
                label=None,
                limit=50,  # Get more to filter
            )
            
            projects = []
            for node in project_nodes:
                # Filter for project-type entities
                if node.entity_type not in ["project", "goal", "task"]:
                    continue
                
                # Check if project is still active (heuristic: mentioned recently)
                is_active = (
                    node.updated_at and
                    (datetime.utcnow() - node.updated_at).days < 30
                )
                
                if is_active and len(projects) < 10:
                    project = Project(
                        id=node.id,
                        name=node.label,
                        description=node.properties.get("description"),
                        status="active",
                        related_entities=await self._get_related_entity_ids(node.id),
                        created_at=node.created_at,
                        updated_at=node.updated_at,
                    )
                    projects.append(project)
            
            logger.debug(f"[WORLD_MODEL] Found {len(projects)} active projects for user {user_id}")
            return projects
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get active projects: {e}")
            return []
    
    async def get_open_loops(self, user_id: str, limit: int = 10) -> List[OpenLoop]:
        """Get open loops (unresolved topics) from AMS.
        
        Args:
            user_id: User identifier
            limit: Maximum number of open loops to return
            
        Returns:
            List of open loops
        """
        try:
            # Phase 2: Placeholder - will integrate with AMS consolidation
            # For now, return empty list
            # TODO: Query AMS for open loops once consolidation API is ready
            
            logger.debug(f"[WORLD_MODEL] Open loops query for user {user_id} (Phase 2 placeholder)")
            return []
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get open loops: {e}")
            return []
    
    async def get_recurring_contexts(self, user_id: str) -> List[Context]:
        """Get recurring contexts or situations.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of recurring contexts
        """
        try:
            # Phase 2: Placeholder - will analyze temporal patterns
            # TODO: Implement temporal pattern detection
            
            logger.debug(f"[WORLD_MODEL] Recurring contexts query for user {user_id} (Phase 2 placeholder)")
            return []
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get recurring contexts: {e}")
            return []
    
    async def query_uncertain_areas(self, user_id: str) -> List[UncertainArea]:
        """Identify areas of uncertainty or incomplete knowledge.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of uncertain areas
        """
        try:
            # Phase 2: Placeholder - will analyze confidence gaps in KG
            # TODO: Implement uncertainty detection
            
            logger.debug(f"[WORLD_MODEL] Uncertain areas query for user {user_id} (Phase 2 placeholder)")
            return []
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to query uncertain areas: {e}")
            return []
    
    async def get_world_context(
        self,
        user_id: str,
        include_entities: bool = True,
        include_projects: bool = True,
        include_open_loops: bool = True,
        include_contexts: bool = False,
        include_uncertain_areas: bool = False,
    ) -> WorldContext:
        """Get complete world context for a user.
        
        Args:
            user_id: User identifier
            include_entities: Include related entities
            include_projects: Include active projects
            include_open_loops: Include open loops
            include_contexts: Include recurring contexts
            include_uncertain_areas: Include uncertain areas
            
        Returns:
            Complete world context
        """
        try:
            context = WorldContext(user_id=user_id)
            
            if include_entities:
                context.entities = await self.get_entities_around_user(user_id)
            
            if include_projects:
                context.projects = await self.get_active_projects(user_id)
            
            if include_open_loops:
                context.open_loops = await self.get_open_loops(user_id)
            
            if include_contexts:
                context.recurring_contexts = await self.get_recurring_contexts(user_id)
            
            if include_uncertain_areas:
                context.uncertain_areas = await self.query_uncertain_areas(user_id)
            
            logger.info(
                f"[WORLD_MODEL] Retrieved world context for user {user_id}: "
                f"{len(context.entities)} entities, {len(context.projects)} projects"
            )
            return context
            
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to get world context: {e}")
            return WorldContext(user_id=user_id)
    
    # Private helper methods
    
    async def _get_recent_topics(self, user_id: str, limit: int = 10) -> List[str]:
        """Get recent conversation topics."""
        # Phase 2: Placeholder
        return []
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        # Phase 2: Placeholder
        return {}
    
    async def _get_relationship_closeness(self, user_id: str) -> float:
        """Get relationship closeness score."""
        # Phase 2: Placeholder - return neutral value
        return 0.5
    
    async def _get_last_interaction(self, user_id: str) -> Optional[datetime]:
        """Get last interaction timestamp."""
        # Phase 2: Placeholder
        return None
    
    async def _get_primary_language(self, user_id: str) -> str:
        """Get user's primary language."""
        # Phase 2: Placeholder
        return "en"
    
    async def _get_related_entity_ids(self, entity_id: str) -> List[str]:
        """Get IDs of entities related to given entity."""
        # Phase 2: Placeholder
        return []
