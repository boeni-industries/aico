from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional, Tuple, Awaitable, Union
from datetime import datetime, UTC

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.ai.base import BaseAIProcessor
from aico.data.libsql.connection import LibSQLConnection
from aico.data.libsql.encrypted import EncryptedLibSQLConnection

from .models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    AgencyEvent,
)
from .store import GoalStore, PlanStore, AgencyEventStore, ReflectionStore
from .planner import Planner
from .values_ethics import ValuesEthicsService, PolicyEffect
from .arbiter import GoalArbiter, IntentionSet

# Phase 2: World Model integration
try:
    from aico.ai.world_model import WorldModelService, WorldContext
    WORLD_MODEL_AVAILABLE = True
except ImportError:
    WORLD_MODEL_AVAILABLE = False
    WorldModelService = None  # type: ignore
    WorldContext = None  # type: ignore

# Phase 2: Personality integration
try:
    from aico.ai.personality import PersonalityService, PersonalityContext
    PERSONALITY_AVAILABLE = True
except ImportError:
    PERSONALITY_AVAILABLE = False
    PersonalityService = None  # type: ignore
    PersonalityContext = None  # type: ignore


logger = get_logger("shared.ai.agency.engine")


class AgencyEngine(BaseAIProcessor):
    """Central orchestrator for autonomous agency.

    Coordinates goals, plans, events, and (later) proactive behaviours.
    This is the primary entrypoint that the AgencyPlugin should use.
    """

    def __init__(
        self,
        config: ConfigurationManager,
        db_connection: Union[LibSQLConnection, EncryptedLibSQLConnection],
        llm_plan_refiner: Optional[Callable] = None,
        world_model: Optional["WorldModelService"] = None,
        personality_service: Optional["PersonalityService"] = None,
        message_bus: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
    ):
        """Initialize the agency engine.

        Args:
            config: Configuration manager
            db_connection: Database connection (basic or encrypted)
            llm_plan_refiner: Optional callback for LLM-based plan refinement
            world_model: Optional world model service for Phase 2+ context (Phase 2)
            personality_service: Optional personality service for Phase 2+ (Phase 2)
            message_bus: Optional message bus for intention set publishing (Phase 4)
            memory_manager: Optional memory manager for skills that need memory access
        """
        super().__init__(component_name="agency_engine", version="v1")
        self.config = config
        self._db_connection = db_connection
        self._memory_manager = memory_manager

        self.goal_store = GoalStore(db_connection)
        self.event_store = AgencyEventStore(db_connection)
        self.reflection_store = ReflectionStore(db_connection)
        
        # Initialize planner with optional LLM client (will be set later if available)
        # Note: skill_registry will be set after it's initialized below
        self.planner = Planner(
            llm_client=None,  # Set via set_llm_client() if available
            enable_caching=True,
            cache_ttl_seconds=3600,
            skill_registry=None,  # Set after skill_registry is initialized
        )
        
        # Phase 4: Values & Ethics service
        self.values_ethics = ValuesEthicsService(db_connection, logger=logger)
        # Values & Ethics initialized
        
        # Phase 4: Goal Arbiter with configuration
        self.arbiter = GoalArbiter(
            db_connection, 
            config=config,
            message_bus=message_bus, 
            logger=logger
        )
        # Goal Arbiter initialized
        
        # Phase 5: Self-Reflection Engine
        from .reflection import SelfReflectionEngine
        self.self_reflection = SelfReflectionEngine(
            config=config,
            db_connection=db_connection,
            llm_client=None  # Will be set later if available
        )
        # Self-Reflection Engine initialized
        
        # Initialize modelservice client for embeddings (needed for goal deduplication)
        self.modelservice_client = None  # Will be set via set_modelservice_client() if available
        
        # Phase 6.10: Plan Execution Engine
        from .executor import PlanExecutor
        from .skill_invoker import SkillInvoker
        from .skills import (
            SkillRegistry,
            AnalyzeConversationSkill,
            SearchMemorySkill,
            UpdateKnowledgeGraphSkill,
            ReflectOnGoalSkill,
        )
        
        # Initialize skill registry and register all skills with database connection
        self.skill_registry = SkillRegistry()
        
        # Analysis skills
        self.skill_registry.register(AnalyzeConversationSkill(db=db_connection, memory_manager=self._memory_manager))
        
        # Memory skills
        self.skill_registry.register(SearchMemorySkill(db=db_connection))
        
        # Knowledge skills
        self.skill_registry.register(UpdateKnowledgeGraphSkill(db=db_connection))
        
        # Reflection skills
        self.skill_registry.register(ReflectOnGoalSkill(db=db_connection))
        
        # Communication skills (AICO-initiated conversations)
        from .skills import AskUserSkill, InitiateConversationSkill
        self.skill_registry.register(AskUserSkill(db=db_connection, message_bus=message_bus))
        self.skill_registry.register(InitiateConversationSkill(db=db_connection, message_bus=message_bus))
        
        # Skill Registry initialized
        
        # Initialize PlanStore with skill_registry for auto-fixing old plans
        self.plan_store = PlanStore(db_connection, skill_registry=self.skill_registry)
        
        # Now that skill_registry is initialized, set it on the planner
        self.planner.skill_registry = self.skill_registry
        # Initialize SkillMatcher now that registry is available
        # Note: embedding_client will be set after modelservice_client is injected
        from .skills.matcher import SkillMatcher
        self.planner.skill_matcher = SkillMatcher(
            skill_registry=self.skill_registry,
            embedding_client=None,  # Will be updated via update_skill_matcher_embedding_client()
            db_connection=db_connection
        )
        # Planner configured
        
        self.skill_invoker = SkillInvoker(
            db=db_connection,
            skill_registry=self.skill_registry,
            default_timeout=30,
            max_retries=2,
            logger=logger
        )
        
        self.executor = PlanExecutor(
            db=db_connection,
            plan_store=self.plan_store,
            goal_store=self.goal_store,
            skill_invoker=self.skill_invoker,
            logger=logger
        )
        # Plan Executor initialized
        
        # Optional backend hook for LLM-based plan refinement (injected by backend)
        self._llm_plan_refiner: Optional[Callable[[Goal, Plan], Awaitable[Plan]]] = llm_plan_refiner
        
        # Phase 2: World Model integration
        self.world_model = world_model
        if world_model and WORLD_MODEL_AVAILABLE:
            pass  # World Model enabled
        else:
            pass  # No World Model
        
        # Phase 2: Personality integration
        self.personality = personality_service
        if personality_service and PERSONALITY_AVAILABLE:
            pass  # Personality enabled
        else:
            pass  # No Personality

    async def initialize(self) -> None:  # type: ignore[override]
        """Placeholder for future initialization hooks."""
        return
    
    def set_llm_plan_refiner(self, refiner: Callable[[Goal, Plan], Awaitable[Plan]]) -> None:
        """Inject an LLM plan refinement callback from the backend layer.
        
        This allows the backend to provide LLM-enhanced planning without
        introducing backend dependencies into the shared agency code.
        """
        self._llm_plan_refiner = refiner
        # LLM plan refiner injected
    
    def set_llm_client(self, llm_client: Any) -> None:
        """Inject LLM client into Planner for LLM-based plan generation.
        
        Args:
            llm_client: LLM client (e.g., ModelServiceClient) for plan generation
        """
        self.planner.llm_client = llm_client
        # LLM client injected
    
    def update_skill_matcher_embedding_client(self) -> None:
        """Update SkillMatcher's embedding client after modelservice_client is injected.
        
        This should be called after set_modelservice_client() to enable semantic
        similarity matching for skill gap deduplication.
        """
        if self.modelservice_client and self.planner.skill_matcher:
            self.planner.skill_matcher.embedding_client = self.modelservice_client
            pass  # Modelservice client injected
        else:
            logger.warning("[AGENCY_ENGINE] Cannot update SkillMatcher embedding client - modelservice_client or skill_matcher not available")

    # ------------------------------------------------------------------
    # Goal & plan API (Phase 1 core)
    # ------------------------------------------------------------------

    async def create_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        origin: GoalOrigin = GoalOrigin.USER,
        goal_type: str = "project",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Create a new goal and (optionally) generate an initial plan."""

        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=user_id,
            origin=origin,
            goal_type=goal_type,
            title=title,
            description=description,
            status=GoalStatus.PENDING,
            priority=priority,
            metadata=metadata or {},
        )
        
        # Phase 4: Values & Ethics evaluation before storing
        ethics_result = self.values_ethics.evaluate_goal(goal, user_id)
        
        if ethics_result.decision == PolicyEffect.BLOCK:
            logger.warning(f"[AGENCY_ENGINE] Goal blocked by ethics policy: {title}")
            await self.event_store.log_event(
                AgencyEvent(
                    user_id=user_id,
                    event_type="goal_blocked",
                    source="values_ethics",
                    payload={
                        "title": title,
                        "reason_codes": ethics_result.reason_codes,
                        "message": ethics_result.user_message
                    }
                )
            )
            raise ValueError(f"Goal blocked by ethics policy: {ethics_result.user_message}")
        
        # Store ethics evaluation in metadata
        goal.metadata["ethics_evaluation"] = {
            "decision": ethics_result.decision.value,
            "reason_codes": ethics_result.reason_codes,
            "evaluated_at": datetime.now(UTC).isoformat()
        }
        
        if ethics_result.decision == PolicyEffect.ALLOW_WITH_WARNING:
            goal.metadata["ethics_warning"] = ethics_result.user_message
            pass  # Goal allowed with warning

        goal = await self.goal_store.create_goal(goal)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=user_id,
                goal_id=goal.goal_id,
                plan_id=None,
                event_type="goal_created",
                source="agency_engine",
                payload={"title": title, "goal_type": goal_type},
            )
        )

        plan: Optional[Plan] = None
        if auto_plan:
            plan = await self._generate_and_store_plan(goal)

        return goal, plan

    async def create_hobby_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        goal_type: str = "hobby",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Convenience helper for creating agent-self hobby goals.

        Uses origin=HOBBY so these can be distinguished from direct user goals.
        """

        return await self.create_goal_with_optional_plan(
            user_id=user_id,
            title=title,
            description=description,
            origin=GoalOrigin.HOBBY,
            goal_type=goal_type,
            priority=priority,
            metadata=metadata,
            auto_plan=auto_plan,
        )

    async def create_maintenance_goal_with_optional_plan(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        goal_type: str = "maintenance",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Convenience helper for creating system-maintenance goals."""

        return await self.create_goal_with_optional_plan(
            user_id=user_id,
            title=title,
            description=description,
            origin=GoalOrigin.MAINTENANCE,
            goal_type=goal_type,
            priority=priority,
            metadata=metadata,
            auto_plan=auto_plan,
        )

    async def create_goal_with_world_context(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        origin: GoalOrigin = GoalOrigin.USER,
        goal_type: str = "project",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Create a goal enriched with world model context (Phase 2).
        
        This method retrieves user context from the world model and enriches
        the goal metadata with relevant information about active projects,
        open loops, and related entities.
        
        Args:
            user_id: User identifier
            title: Goal title
            description: Optional goal description
            origin: Goal origin (user, hobby, maintenance)
            goal_type: Type of goal
            priority: Goal priority
            metadata: Additional metadata
            auto_plan: Whether to generate an initial plan
            
        Returns:
            Tuple of (created goal, optional plan)
        """
        # If world model not available, fall back to basic creation
        if not self.world_model or not WORLD_MODEL_AVAILABLE:
            pass  # Using basic goal creation
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=metadata,
                auto_plan=auto_plan,
            )
        
        try:
            # Retrieve world context
            logger.debug(f"[AGENCY_ENGINE] Retrieving world context for user {user_id}")
            world_context = await self.world_model.get_world_context(
                user_id=user_id,
                include_entities=True,
                include_projects=True,
                include_open_loops=True,
            )
            
            # Enrich metadata with world context
            enriched_metadata = metadata or {}
            enriched_metadata['world_context'] = {
                'active_projects': [p.id for p in world_context.projects],
                'related_entities': [e.id for e in world_context.entities[:5]],  # Top 5
                'open_loops': [loop.id for loop in world_context.open_loops],
                'retrieved_at': world_context.retrieved_at.isoformat(),
            }
            
            pass  # Enriched goal with world context
            
            # Create goal with enriched metadata
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=enriched_metadata,
                auto_plan=auto_plan,
            )
            
        except Exception as e:
            logger.error(f"[AGENCY_ENGINE] Failed to retrieve world context: {e}, using basic creation")
            # Fall back to basic creation on error
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=metadata,
                auto_plan=auto_plan,
            )

    async def create_goal_with_full_context(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        origin: GoalOrigin = GoalOrigin.USER,
        goal_type: str = "project",
        priority: GoalPriority = GoalPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        auto_plan: bool = True,
    ) -> Tuple[Goal, Optional[Plan]]:
        """Create a goal with full Phase 2 context (world model + personality).
        
        This is the recommended method for Phase 2+ goal creation. It:
        1. Retrieves world model context (entities, projects, open loops)
        2. Gets personality context (traits, relationship)
        3. Adjusts priority based on personality
        4. Enriches metadata with all context
        
        Args:
            user_id: User identifier
            title: Goal title
            description: Optional goal description
            origin: Goal origin (user, hobby, maintenance)
            goal_type: Type of goal
            priority: Base goal priority (will be adjusted by personality)
            metadata: Additional metadata
            auto_plan: Whether to generate an initial plan
            
        Returns:
            Tuple of (created goal, optional plan)
        """
        # If neither world model nor personality available, fall back to basic
        if not self.world_model and not self.personality:
            pass  # Using basic goal creation
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=metadata,
                auto_plan=auto_plan,
            )
        
        try:
            enriched_metadata = metadata or {}
            
            # Step 1: Get personality context and adjust priority
            if self.personality:
                pass  # Retrieving personality context
                personality_context = await self.personality.get_personality_context(user_id)
                
                # Adjust priority based on personality traits
                adjusted_priority_str = self.personality.adjust_priority_for_personality(
                    base_priority=priority.value,
                    personality=personality_context,
                )
                
                # Convert back to enum
                priority_map = {
                    "low": GoalPriority.LOW,
                    "normal": GoalPriority.NORMAL,
                    "high": GoalPriority.HIGH,
                }
                adjusted_priority = priority_map.get(adjusted_priority_str, priority)
                
                # Calculate proactivity level
                proactivity = self.personality.calculate_proactivity_level(personality_context)
                
                # Add personality context to metadata
                enriched_metadata['personality_context'] = {
                    'relationship_closeness': personality_context.relationship.closeness,
                    'proactivity_level': proactivity,
                    'priority_adjusted': adjusted_priority != priority,
                    'original_priority': priority.value,
                }
                
                pass  # Personality adjustment applied
                
                # Use adjusted priority
                priority = adjusted_priority
            
            # Step 2: Get world model context
            if self.world_model:
                pass  # Retrieving world context
                world_context = await self.world_model.get_world_context(
                    user_id=user_id,
                    include_entities=True,
                    include_projects=True,
                    include_open_loops=True,
                )
                
                # Add world context to metadata
                enriched_metadata['world_context'] = {
                    'active_projects': [p.id for p in world_context.projects],
                    'related_entities': [e.id for e in world_context.entities[:5]],
                    'open_loops': [loop.id for loop in world_context.open_loops],
                    'retrieved_at': world_context.retrieved_at.isoformat(),
                }
                
                pass  # World context retrieved
            
            # Step 3: Create goal with enriched metadata and adjusted priority
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=enriched_metadata,
                auto_plan=auto_plan,
            )
            
        except Exception as e:
            logger.error(f"[AGENCY_ENGINE] Failed to create goal with full context: {e}, using basic creation")
            import traceback
            logger.error(f"[AGENCY_ENGINE] Traceback: {traceback.format_exc()}")
            # Fall back to basic creation on error
            return await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=title,
                description=description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=metadata,
                auto_plan=auto_plan,
            )
    
    async def create_goal_from_curiosity_signal(
        self,
        user_id: str,
        signal,  # IntrinsicSignal
        auto_plan: bool = True,
    ) -> tuple[Goal, Optional[Plan]]:
        """Create a goal from a curiosity signal.
        
        Converts an IntrinsicSignal from the Curiosity Engine into a hobby goal.
        
        Args:
            user_id: User identifier
            signal: IntrinsicSignal from Curiosity Engine
            auto_plan: Whether to generate an initial plan
            
        Returns:
            Tuple of (created goal, optional plan)
        """
        try:
            pass  # Creating goal from curiosity signal
            
            # Phase 4: Values & Ethics gate - evaluate curiosity signal
            ethics_result = self.values_ethics.evaluate_curiosity_signal(signal, user_id)
            
            if ethics_result.decision == PolicyEffect.BLOCK:
                logger.warning(
                    f"[AGENCY_ENGINE] Curiosity signal blocked by ethics policy: {signal.topic}"
                )
                # Log the blocked signal as an event
                await self.event_store.log_event(
                    AgencyEvent(
                        user_id=user_id,
                        event_type="curiosity_signal_blocked",
                        source="values_ethics",
                        payload={
                            "signal_id": signal.signal_id,
                            "topic": signal.topic,
                            "reason_codes": ethics_result.reason_codes,
                            "message": ethics_result.user_message
                        }
                    )
                )
                raise ValueError(f"Curiosity signal blocked by ethics policy: {ethics_result.user_message}")
            
            if ethics_result.decision == PolicyEffect.NEEDS_CONSENT:
                logger.info(
                    f"[AGENCY_ENGINE] Curiosity signal requires consent: {signal.topic}"
                )
                # Log consent requirement - actual consent flow handled by UX
                await self.event_store.log_event(
                    AgencyEvent(
                        user_id=user_id,
                        event_type="curiosity_signal_needs_consent",
                        source="values_ethics",
                        payload={
                            "signal_id": signal.signal_id,
                            "topic": signal.topic,
                            "consent_scope": ethics_result.consent_scope,
                            "message": ethics_result.user_message
                        }
                    )
                )
                # For now, don't create the goal - wait for explicit consent
                raise ValueError(f"Curiosity signal requires consent: {ethics_result.user_message}")
            
            if ethics_result.decision == PolicyEffect.ALLOW_WITH_WARNING:
                logger.info(
                    f"[AGENCY_ENGINE] Curiosity signal allowed with warning: {signal.topic}"
                )
                # Log the warning
                await self.event_store.log_event(
                    AgencyEvent(
                        user_id=user_id,
                        event_type="curiosity_signal_warning",
                        source="values_ethics",
                        payload={
                            "signal_id": signal.signal_id,
                            "topic": signal.topic,
                            "reason_codes": ethics_result.reason_codes,
                            "message": ethics_result.user_message
                        }
                    )
                )
            
            # Determine origin based on signal type
            if signal.signal_type.value == "hobby_play":
                origin = GoalOrigin.HOBBY
            else:
                origin = GoalOrigin.CURIOSITY
            
            # Map signal priority to GoalPriority
            priority_map = {
                "low": GoalPriority.LOW,
                "normal": GoalPriority.NORMAL,
                "high": GoalPriority.HIGH,
            }
            priority = priority_map.get(signal.priority, GoalPriority.NORMAL)
            
            # Generate title embedding for similarity matching
            title_embedding = None
            try:
                if self.modelservice_client:
                    embedding_response = await self.modelservice_client.get_embeddings(
                        model="paraphrase-multilingual",
                        prompt=signal.topic
                    )
                    if embedding_response.get("success"):
                        title_embedding = embedding_response["data"]["embedding"]
            except Exception as e:
                logger.warning(f"[AGENCY_ENGINE] Failed to generate title embedding: {e}")
            
            # Build metadata with curiosity context
            metadata = {
                "curiosity_signal_id": signal.signal_id,
                "curiosity_type": signal.signal_type.value,
                "curiosity_score": signal.total_score,
                "novelty_score": signal.novelty_score,
                "user_relevance_score": signal.user_relevance_score,
                "source_component": signal.source_component,
                "topic_tags": signal.topic_tags,
                "title_embedding": title_embedding,  # Store for similarity matching
            }
            
            # Add template info if available
            if "template_id" in signal.context:
                metadata["hobby_template_id"] = signal.context["template_id"]
                metadata["hobby_category"] = signal.context.get("category")
            
            # CRITICAL FIX: Check for existing goals to prevent duplicates
            # 1. Exact title match (fast path)
            existing_goal = self._db_connection.execute(
                """SELECT goal_id, title, description, status, created_at FROM agency_goals 
                   WHERE user_id = ? AND title = ? AND status IN ('pending', 'active', 'paused')
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, signal.topic)
            ).fetchone()
            
            if existing_goal:
                logger.info(
                    f"[AGENCY_ENGINE] Goal '{signal.topic}' already exists (exact match, "
                    f"id={existing_goal['goal_id']}, status={existing_goal['status']}), skipping duplicate"
                )
                goal = await self.goal_store.get_goal(existing_goal['goal_id'])
                return goal, None
            
            # 2. Semantic similarity check (for near-duplicates with different wording)
            # Get recent goals of same type for similarity comparison
            recent_goals = self._db_connection.execute(
                """SELECT goal_id, title, description, status, created_at FROM agency_goals 
                   WHERE user_id = ? 
                   AND goal_type IN ('hobby', 'curiosity')
                   AND status IN ('pending', 'active', 'paused')
                   AND created_at > datetime('now', '-7 days')
                   ORDER BY created_at DESC LIMIT 20""",
                (user_id,)
            ).fetchall()
            
            # Check for semantic duplicates using simple keyword overlap
            # (More sophisticated: could use embeddings, but this is lightweight)
            signal_keywords = set(signal.topic.lower().split())
            signal_desc_keywords = set(signal.description.lower().split()) if signal.description else set()
            
            for existing in recent_goals:
                existing_keywords = set(existing['title'].lower().split())
                existing_desc_keywords = set(existing['description'].lower().split()) if existing['description'] else set()
                
                # Calculate Jaccard similarity for titles
                title_overlap = len(signal_keywords & existing_keywords)
                title_union = len(signal_keywords | existing_keywords)
                title_similarity = title_overlap / title_union if title_union > 0 else 0
                
                # Calculate description similarity
                desc_overlap = len(signal_desc_keywords & existing_desc_keywords)
                desc_union = len(signal_desc_keywords | existing_desc_keywords)
                desc_similarity = desc_overlap / desc_union if desc_union > 0 else 0
                
                # Combined similarity (weighted average)
                combined_similarity = (title_similarity * 0.7) + (desc_similarity * 0.3)
                
                # If similarity > 0.6, consider it a duplicate
                if combined_similarity > 0.6:
                    logger.info(
                        f"[AGENCY_ENGINE] Goal '{signal.topic}' is semantically similar to existing goal "
                        f"'{existing['title']}' (similarity={combined_similarity:.2f}, id={existing['goal_id']}), "
                        f"skipping duplicate"
                    )
                    goal = await self.goal_store.get_goal(existing['goal_id'])
                    return goal, None
            
            # Create goal with appropriate origin
            goal, plan = await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=signal.topic,
                description=signal.description,
                origin=origin,
                goal_type="curiosity" if origin == GoalOrigin.CURIOSITY else "hobby",
                priority=priority,
                metadata=metadata,
                auto_plan=auto_plan,
            )
            
            # Update signal status
            signal.status = "converted"
            
            logger.info(
                f"[AGENCY_ENGINE] Created {origin.value} goal {goal.goal_id} "
                f"from signal {signal.signal_id}"
            )
            
            return goal, plan
            
        except Exception as e:
            logger.error(f"[AGENCY_ENGINE] Failed to create goal from curiosity signal: {e}")
            raise

    async def _generate_and_store_plan(self, goal: Goal) -> Plan:
        """Generate an initial plan for a goal and persist it.
        
        Uses deterministic planner first, then optionally refines with LLM
        if a refiner callback has been injected by the backend.
        """

        # Generate base plan using deterministic planner
        plan = await self.planner.generate_initial_plan(goal)
        
        # Optionally refine with LLM if backend has injected a refiner
        if self._llm_plan_refiner:
            try:
                plan = await self._llm_plan_refiner(goal, plan)
            except Exception as e:
                logger.warning(f"[AGENCY_ENGINE] LLM plan refinement failed: {e}, using base plan")
        
        # Persist the plan (base or refined)
        plan = await self.plan_store.create_plan(plan)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=goal.user_id,
                goal_id=goal.goal_id,
                plan_id=plan.plan_id,
                event_type="plan_generated",
                source="agency_engine",
                payload={
                    "step_count": len(plan.steps),
                    "llm_refined": plan.metadata.get("llm_refined", False),
                },
            )
        )

        return plan

    # ------------------------------------------------------------------
    # Goal lifecycle helpers (Phase 1)
    # ------------------------------------------------------------------

    async def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Fetch a single goal by ID."""

        return await self.goal_store.get_goal(goal_id)

    async def list_goals_for_user(
        self,
        user_id: str,
        status: Optional[GoalStatus] = None,
    ) -> list[Goal]:
        """List goals for a user, optionally filtered by status."""

        return await self.goal_store.list_goals(user_id=user_id, status=status)

    async def _change_goal_status(
        self,
        *,
        goal_id: str,
        new_status: GoalStatus,
        event_type: str,
        source: str = "agency_engine",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Goal]:
        """Internal helper to transition goal status and log telemetry."""

        goal = await self.goal_store.get_goal(goal_id)
        if not goal:
            logger.warning("[AGENCY_ENGINE] Attempted to change status of unknown goal", extra={"goal_id": goal_id})
            return None

        await self.goal_store.update_goal_status(goal_id, new_status)

        await self.event_store.log_event(
            AgencyEvent(
                user_id=goal.user_id,
                goal_id=goal.goal_id,
                plan_id=None,
                event_type=event_type,
                source=source,
                payload={
                    "from": goal.status.value,
                    "to": new_status.value,
                    **(payload or {}),
                },
            )
        )

        # Return updated goal snapshot (caller can ignore if not needed)
        updated = await self.goal_store.get_goal(goal_id)
        return updated

    async def activate_goal(self, goal_id: str) -> Optional[Goal]:
        """Mark a goal as active."""
        logger.info("[AGENCY_ENGINE] Activating goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.ACTIVE,
            event_type="goal_activated",
        )

    async def pause_goal(self, goal_id: str) -> Optional[Goal]:
        """Pause a goal (user-requested or system-initiated)."""
        logger.info("[AGENCY_ENGINE] Pausing goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.PAUSED,
            event_type="goal_paused",
        )

    async def complete_goal(self, goal_id: str) -> Optional[Goal]:
        """Mark a goal as completed."""
        logger.info("[AGENCY_ENGINE] Completing goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.COMPLETED,
            event_type="goal_completed",
        )

    async def retire_goal(self, goal_id: str) -> Optional[Goal]:
        """Retire a goal (abandoned, no longer relevant, etc.)."""
        logger.info("[AGENCY_ENGINE] Retiring goal", extra={"goal_id": goal_id})
        return await self._change_goal_status(
            goal_id=goal_id,
            new_status=GoalStatus.RETIRED,
            event_type="goal_retired",
        )
    
    # ------------------------------------------------------------------
    # Phase 4: Intention Set Management
    # ------------------------------------------------------------------
    
    async def get_intention_set(self, user_id: str) -> IntentionSet:
        """
        Get the current intention set for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            IntentionSet with active and proposed intentions
        """
        return await self.arbiter.get_intention_set(user_id)
    
    async def update_intention_set_for_user(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentionSet:
        """
        Update the intention set by re-evaluating all pending goals.
        
        This is typically called:
        - After new goals are created
        - Periodically by a scheduler
        - When user context changes significantly
        
        Args:
            user_id: User ID
            context: Optional context (personality, emotion, system load)
            
        Returns:
            Updated IntentionSet
        """
        # Get all pending and active goals for this user
        pending_goals = await self.goal_store.get_goals_by_status(
            user_id=user_id,
            statuses=[GoalStatus.PENDING, GoalStatus.ACTIVE]
        )
        
        # Update intention set with arbiter
        intention_set = await self.arbiter.update_intention_set(
            user_id=user_id,
            candidate_goals=pending_goals,
            context=context
        )
        
        logger.info(
            f"[AGENCY_ENGINE] Updated intention set for {user_id}: "
            f"{len(intention_set.active_intentions)} active, "
            f"{len(intention_set.proposed_intentions)} proposed"
        )
        
        return intention_set

    # ------------------------------------------------------------------
    # Contract-style entrypoint for AgencyPlugin (Phase 1 stub)
    # ------------------------------------------------------------------

    async def analyze_conversation_turn(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze a conversation turn for agency opportunities.

        This is the contract-compliant entrypoint that AgencyPlugin calls.
        Phase 1: Returns empty suggestions (no autonomous behaviour yet).
        Later phases: Will return goal suggestions, plan updates, proactive actions.
        """

        # Phase 1: Return empty contract-compliant response
        return {
            "goal_suggestions": [],
            "plan_updates": [],
            "proactive_actions": [],
            "metadata": {
                "phase": "1",
                "analyzed_at": datetime.now(UTC).isoformat(),
            },
        }
    
    # ------------------------------------------------------------------
    # Phase 5: Self-Reflection Methods
    # ------------------------------------------------------------------
    
    async def run_self_reflection(
        self,
        user_id: str,
        run_type: Optional["RunType"] = None,
        trigger_reason: Optional[str] = None,
        analysis_window_days: int = 7,
    ) -> "ReflectionRun":
        """
        Run a self-reflection job for a user.
        
        Args:
            user_id: User to reflect on
            run_type: Type of reflection run (defaults to SCHEDULED)
            trigger_reason: Why this run was triggered
            analysis_window_days: How many days back to analyze
            
        Returns:
            ReflectionRun with results
        """
        from .models import RunType
        
        if run_type is None:
            run_type = RunType.SCHEDULED
        
        return await self.self_reflection.run_reflection(
            user_id=user_id,
            run_type=run_type,
            trigger_reason=trigger_reason,
            analysis_window_days=analysis_window_days,
        )
    
    async def get_active_lessons(
        self,
        user_id: str,
        lesson_type: Optional["LessonType"] = None,
    ) -> List["Lesson"]:
        """
        Get active behavioral lessons for a user.
        
        Args:
            user_id: User ID
            lesson_type: Optional filter by lesson type
            
        Returns:
            List of active lessons
        """
        return await self.self_reflection.get_active_lessons(
            user_id=user_id,
            lesson_type=lesson_type
        )
    
    async def get_self_model_entry(
        self,
        user_id: str,
        entity_type: "EntityType",
        entity_id: str,
    ) -> Optional["SelfModelEntry"]:
        """
        Get self-model performance data for an entity.
        
        Args:
            user_id: User ID
            entity_type: Type of entity (skill, goal_type, etc.)
            entity_id: Entity ID
            
        Returns:
            Latest self-model entry or None
        """
        return await self.self_reflection.get_self_model(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id
        )
    
    async def get_skill_performance(self, user_id: str, skill_id: str) -> Optional[float]:
        """
        Get skill success rate for planning decisions.
        
        Args:
            user_id: User ID
            skill_id: Skill ID
            
        Returns:
            Success rate (0.0-1.0) or None
        """
        return await self.self_reflection.get_skill_performance(user_id, skill_id)
    
    async def get_goal_type_performance_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get goal type performance data for arbiter context.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of goal_type -> performance metrics
        """
        # Get all goal types that have been used
        rows = self.goal_store.db.execute(
            """SELECT DISTINCT goal_type FROM agency_goals WHERE user_id = ?""",
            (user_id,)
        ).fetchall()
        
        performance_context = {}
        for row in rows:
            goal_type = row["goal_type"]
            perf_data = await self.self_reflection.get_goal_type_performance(user_id, goal_type)
            if perf_data:
                performance_context[goal_type] = perf_data
        
        return performance_context
    
    # ------------------------------------------------------------------
    # PerceptualEvent Processing (Phase 6 - Conversation Integration)
    # ------------------------------------------------------------------
    
    async def process_perceptual_event(self, event) -> Optional[Goal]:
        """
        Process a PerceptualEvent and potentially create a goal.
        
        This is the main entry point for conversation-based goal extraction
        and other perception-driven goal creation.
        
        Args:
            event: PerceptualEvent from conversation, sensors, or other sources
            
        Returns:
            Created Goal if event resulted in goal creation, None otherwise
        """
        from .perceptual_events import PerceptType, GoalOriginType
        
        try:
            logger.info(
                f"[AGENCY_ENGINE] Processing {event.percept_type.value} event: {event.summary_text[:100]}"
            )
            
            # Only process events with goal candidates
            if not event.candidate_goal_summaries:
                logger.debug("[AGENCY_ENGINE] Event has no goal candidates, skipping")
                return None
            
            # Extract goal details from event
            goal_title = event.candidate_goal_summaries[0]
            goal_description = event.metadata.get("goal_description")
            
            # Map event origin to goal origin
            origin_map = {
                GoalOriginType.USER: GoalOrigin.USER,
                GoalOriginType.CURIOSITY: GoalOrigin.CURIOSITY,
                GoalOriginType.AGENT_SELF: GoalOrigin.HOBBY,
                GoalOriginType.SYSTEM_MAINTENANCE: GoalOrigin.MAINTENANCE,
            }
            origin = origin_map.get(event.candidate_origin, GoalOrigin.USER)
            
            # Map horizon to goal type
            horizon_to_type = {
                "theme": "theme",
                "project": "project",
                "task": "task"
            }
            goal_type = horizon_to_type.get(
                event.candidate_goal_horizon.value if event.candidate_goal_horizon else "project",
                "project"
            )
            
            # Determine priority from urgency score
            if event.urgency_score >= 0.8:
                priority = GoalPriority.HIGH
            elif event.urgency_score >= 0.5:
                priority = GoalPriority.NORMAL
            else:
                priority = GoalPriority.LOW
            
            # Generate title embedding for similarity matching
            title_embedding = None
            try:
                if self.modelservice_client:
                    embedding_response = await self.modelservice_client.get_embeddings(
                        model="paraphrase-multilingual",
                        prompt=goal_title
                    )
                    if embedding_response.get("success"):
                        title_embedding = embedding_response["data"]["embedding"]
            except Exception as e:
                logger.warning(f"[AGENCY_ENGINE] Failed to generate title embedding: {e}")
            
            # Build metadata
            from datetime import datetime, UTC
            now = datetime.now(UTC)
            
            # Initialize intent_mentions array with first mention
            initial_mention = {
                "message_id": event.metadata.get("message_id"),
                "timestamp": (event.timestamp or now).isoformat(),
                "confidence": event.confidence_score,
                "message_text": event.metadata.get("original_message", "")[:100]
            }
            
            metadata = {
                "percept_id": event.percept_id,
                "source_component": event.source_component,
                "confidence": event.confidence_score,
                "salience": event.salience_score,
                "extracted_from_conversation": event.metadata.get("extracted_from_conversation", False),
                "original_message": event.metadata.get("original_message"),
                "intent_type": event.metadata.get("intent_type"),
                "title_embedding": title_embedding,  # Store for similarity matching
                "intent_mentions": [initial_mention],  # Initialize with first mention
                "mention_count": 1,  # Initialize persistence tracking
                "mention_frequency": 0.0,  # Will be calculated on first reinforcement
                "first_mentioned": (event.timestamp or now).isoformat(),
                "last_mentioned": (event.timestamp or now).isoformat(),
            }
            
            # Get user_id from event actors
            user_id = event.actors[0] if event.actors else None
            if not user_id:
                logger.warning("[AGENCY_ENGINE] Event has no user_id in actors, cannot create goal")
                return None
            
            # Create goal with optional plan
            goal, plan = await self.create_goal_with_optional_plan(
                user_id=user_id,
                title=goal_title,
                description=goal_description,
                origin=origin,
                goal_type=goal_type,
                priority=priority,
                metadata=metadata,
                auto_plan=True  # Generate plan for user goals
            )
            
            logger.info(
                f"[AGENCY_ENGINE] Created goal from {event.percept_type.value}: "
                f"'{goal_title}' (id={goal.goal_id}, origin={origin.value})"
            )
            
            # Log event
            await self.event_store.log_event(
                AgencyEvent(
                    user_id=user_id,
                    goal_id=goal.goal_id,
                    plan_id=plan.plan_id if plan else None,
                    event_type="goal_created_from_percept",
                    source="perceptual_event_processor",
                    payload={
                        "percept_type": event.percept_type.value,
                        "percept_id": event.percept_id,
                        "confidence": event.confidence_score,
                    }
                )
            )
            
            return goal
            
        except Exception as e:
            logger.error(f"[AGENCY_ENGINE] Failed to process perceptual event: {e}")
            return None
    
    # ------------------------------------------------------------------
    # BaseAIProcessor abstract method implementations
    # ------------------------------------------------------------------
    
    async def process(self, context) -> Any:
        """Process AI request (BaseAIProcessor interface).
        
        For AgencyEngine, this delegates to analyze_conversation_turn.
        """
        return await self.analyze_conversation_turn(
            user_id=context.user_id,
            conversation_id=context.conversation_id,
            message=context.message_content,
            context=context.shared_state,
        )
    
    async def health_check(self) -> bool:
        """Check if agency engine is healthy and operational."""
        try:
            # Check if stores are accessible
            test_goals = await self.goal_store.list_goals("health_check_user", status=None)
            return True
        except Exception as e:
            logger.error(f"[AGENCY_ENGINE] Health check failed: {e}")
            return False
    
    def get_supported_operations(self) -> list[str]:
        """Get list of operations supported by agency engine."""
        return [
            "analyze_conversation_turn",
            "create_goal",
            "activate_goal",
            "pause_goal",
            "complete_goal",
            "retire_goal",
            "list_goals",
        ]
