"""
World Model Service

Unified API for querying knowledge graph and semantic memory.
Provides contextual awareness for agency, planning, and curiosity systems.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, UTC

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
    # Phase 6.4
    Schema,
    Hypothesis,
    DriftReport,
    Contradiction,
)
from .schema_learner import SchemaLearner
from .hypothesis_manager import HypothesisManager
from .drift_detector import DriftDetector


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
        
        # Phase 6.4: Initialize advanced components
        self.schema_learner = SchemaLearner()
        self.hypothesis_manager = HypothesisManager()
        self.drift_detector = DriftDetector()
        
        logger.info("[WORLD_MODEL] Service initialized (Phase 6.4: Schema, Hypothesis, Drift)")
    
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
                    (datetime.now(UTC) - node.updated_at).days < 30
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
        
        Phase 6.4: Uses drift detection and hypothesis tracking.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of uncertain areas
        """
        try:
            uncertain_areas = []
            
            # Get open hypotheses (areas under investigation)
            open_hypotheses = self.hypothesis_manager.get_open_hypotheses(user_id)
            
            for hypothesis in open_hypotheses:
                # Convert hypothesis to uncertain area
                area = UncertainArea(
                    id=hypothesis.hypothesis_id,
                    topic=hypothesis.description,
                    description=f"Hypothesis: {hypothesis.description}",
                    confidence_gap=1.0 - hypothesis.confidence,  # Higher gap = more uncertain
                    related_entities=hypothesis.affected_entities,
                    questions=[f"Is this hypothesis correct: {hypothesis.description}?"],
                )
                uncertain_areas.append(area)
            
            logger.debug(f"[WORLD_MODEL] Found {len(uncertain_areas)} uncertain areas for user {user_id}")
            return uncertain_areas
            
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
    
    # Phase 6.4: Schema Learning, Hypothesis, and Drift Detection Methods
    
    async def learn_schema(
        self,
        entity_type: str,
        samples: List[Dict[str, Any]]
    ) -> Schema:
        """Learn schema from data samples.
        
        Args:
            entity_type: Type of entity
            samples: Sample data
            
        Returns:
            Learned Schema
        """
        return self.schema_learner.extract_schema(entity_type, samples)
    
    async def validate_data(
        self,
        schema: Schema,
        data: Dict[str, Any]
    ):
        """Validate data against schema.
        
        Args:
            schema: Schema to validate against
            data: Data to validate
            
        Returns:
            ValidationResult
        """
        return self.schema_learner.validate_schema(schema, data)
    
    async def generate_hypothesis(
        self,
        user_id: str,
        description: str,
        hypothesis_type: str,
        affected_entities: List[str],
        initial_evidence: Optional[List[str]] = None
    ) -> Hypothesis:
        """Generate new hypothesis.
        
        Args:
            user_id: User ID
            description: Description
            hypothesis_type: Type
            affected_entities: Affected entities
            initial_evidence: Optional initial evidence
            
        Returns:
            New Hypothesis
        """
        return self.hypothesis_manager.generate_hypothesis(
            user_id=user_id,
            description=description,
            hypothesis_type=hypothesis_type,
            affected_entities=affected_entities,
            initial_evidence=initial_evidence,
        )
    
    async def test_hypothesis(
        self,
        hypothesis_id: str,
        test_type: str,
        supports_hypothesis: bool,
        evidence_ids: Optional[List[str]] = None
    ):
        """Test hypothesis with new evidence.
        
        Args:
            hypothesis_id: Hypothesis ID
            test_type: Test type
            supports_hypothesis: Whether evidence supports hypothesis
            evidence_ids: Optional evidence IDs
            
        Returns:
            HypothesisTestResult
        """
        return self.hypothesis_manager.test_hypothesis(
            hypothesis_id=hypothesis_id,
            test_type=test_type,
            supports_hypothesis=supports_hypothesis,
            evidence_ids=evidence_ids,
        )
    
    async def get_hypotheses(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Hypothesis]:
        """Get hypotheses for user.
        
        Args:
            user_id: User ID
            status: Optional status filter
            
        Returns:
            List of Hypotheses
        """
        return self.hypothesis_manager.get_hypotheses_for_user(user_id, status=status)
    
    async def detect_drift(
        self,
        entity_id: str,
        entity_type: str,
        historical_states: List[Dict[str, Any]],
        window_days: int = 30
    ) -> Optional[DriftReport]:
        """Detect drift in entity state.
        
        Args:
            entity_id: Entity ID
            entity_type: Entity type
            historical_states: Historical states
            window_days: Window size
            
        Returns:
            DriftReport if drift detected
        """
        return self.drift_detector.detect_drift(
            entity_id=entity_id,
            entity_type=entity_type,
            historical_states=historical_states,
            window_days=window_days,
        )
    
    async def detect_anomalies(self, user_id: str) -> List[Dict[str, Any]]:
        """Detect anomalies in user data.
        
        Phase 6.4: Returns contradictions and drift reports.
        
        Args:
            user_id: User ID
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        # Get contradictions (would need to query facts from KG)
        # For now, return empty list
        # TODO: Integrate with actual fact storage
        
        logger.debug(f"[WORLD_MODEL] Anomaly detection for user {user_id}")
        return anomalies
    
    async def detect_contradictions(
        self,
        facts: List[Dict[str, Any]]
    ) -> List[Contradiction]:
        """Detect contradictions in facts.
        
        Args:
            facts: List of facts
            
        Returns:
            List of Contradictions
        """
        return self.drift_detector.detect_contradictions(facts)
    
    async def query_aico_self_assessment(
        self,
        entity_type: str,
        entity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query AICO's self-assessment for capabilities and performance.
        
        Retrieves self-model entries projected into the World Model,
        enabling planning and reasoning about AICO's own capabilities.
        
        Args:
            entity_type: Type of entity (skill, goal_type, etc.)
            entity_id: Optional specific entity ID
            
        Returns:
            List of self-assessment facts
        """
        # Query KG for self-model facts
        # These are projected by LessonMemoryProjector.project_self_model_to_kg()
        
        # For now, return placeholder
        # TODO: Implement actual KG query once PropertyGraphStorage supports it
        logger.debug(
            f"[WORLD_MODEL] Querying self-assessment for {entity_type}",
            extra={"entity_id": entity_id}
        )
        return []
    
    async def link_lesson_to_hypothesis(
        self,
        lesson_id: str,
        hypothesis_id: str,
        relationship: str = "VALIDATES",
    ) -> bool:
        """
        Link a reflection lesson to a World Model hypothesis.
        
        Enables bidirectional integration where reflection insights
        validate or invalidate hypotheses about the world.
        
        Args:
            lesson_id: Lesson identifier
            hypothesis_id: Hypothesis identifier
            relationship: Type of relationship (VALIDATES, INVALIDATES, REFINES)
            
        Returns:
            True if link created successfully
        """
        try:
            # This would create a KG edge: Lesson → Hypothesis
            # For now, log the intent
            logger.info(
                f"[WORLD_MODEL] Linking lesson {lesson_id} to hypothesis {hypothesis_id}",
                extra={"relationship": relationship}
            )
            return True
        except Exception as e:
            logger.error(f"[WORLD_MODEL] Failed to link lesson to hypothesis: {e}")
            return False
