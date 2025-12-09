from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional, Tuple, Awaitable, Union
from datetime import datetime

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


logger = get_logger("shared", "ai.agency.engine")


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
    ):
        """Initialize the agency engine.

        Args:
            config: Configuration manager
            db_connection: Database connection (basic or encrypted)
            llm_plan_refiner: Optional callback for LLM-based plan refinement
            world_model: Optional world model service for Phase 2+ context (Phase 2)
            personality_service: Optional personality service for Phase 2+ (Phase 2)
            message_bus: Optional message bus for intention set publishing (Phase 4)
        """
        super().__init__(component_name="agency_engine", version="v1")
        self.config = config
        self._db_connection = db_connection

        self.goal_store = GoalStore(db_connection)
        self.plan_store = PlanStore(db_connection)
        self.event_store = AgencyEventStore(db_connection)
        self.reflection_store = ReflectionStore(db_connection)
        self.planner = Planner()
        
        # Phase 4: Values & Ethics service
        print("🔧 [PHASE 4 DEBUG] Initializing ValuesEthicsService...")
        self.values_ethics = ValuesEthicsService(db_connection, logger=logger)
        print("✅ [PHASE 4 DEBUG] ValuesEthicsService initialized!")
        logger.info("[AGENCY_ENGINE] Values & Ethics service initialized (Phase 4)")
        
        # Phase 4: Goal Arbiter with configuration
        print("🔧 [PHASE 4 DEBUG] Initializing GoalArbiter with config...")
        print(f"🔧 [PHASE 4 DEBUG] Config object: {config}")
        print(f"🔧 [PHASE 4 DEBUG] Message bus: {message_bus}")
        self.arbiter = GoalArbiter(
            db_connection, 
            config=config,
            message_bus=message_bus, 
            logger=logger
        )
        print("✅ [PHASE 4 DEBUG] GoalArbiter initialized!")
        logger.info("[AGENCY_ENGINE] Goal Arbiter initialized (Phase 4)")
        
        # Optional backend hook for LLM-based plan refinement (injected by backend)
        self._llm_plan_refiner: Optional[Callable[[Goal, Plan], Awaitable[Plan]]] = llm_plan_refiner
        
        # Phase 2: World Model integration
        self.world_model = world_model
        if world_model and WORLD_MODEL_AVAILABLE:
            logger.info("[AGENCY_ENGINE] World Model integration enabled (Phase 2)")
        else:
            logger.debug("[AGENCY_ENGINE] Running without World Model (Phase 1 mode)")
        
        # Phase 2: Personality integration
        self.personality = personality_service
        if personality_service and PERSONALITY_AVAILABLE:
            logger.info("[AGENCY_ENGINE] Personality integration enabled (Phase 2)")
        else:
            logger.debug("[AGENCY_ENGINE] Running without Personality (Phase 1 mode)")

    async def initialize(self) -> None:  # type: ignore[override]
        """Placeholder for future initialization hooks."""
        return
    
    def set_llm_plan_refiner(self, refiner: Callable[[Goal, Plan], Awaitable[Plan]]) -> None:
        """Inject an LLM plan refinement callback from the backend layer.
        
        This allows the backend to provide LLM-enhanced planning without
        introducing backend dependencies into the shared agency code.
        """
        self._llm_plan_refiner = refiner
        logger.info("[AGENCY_ENGINE] LLM plan refiner injected")

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
            await self.log_event(
                user_id=user_id,
                event_type="goal_blocked",
                source="values_ethics",
                payload={
                    "title": title,
                    "reason_codes": ethics_result.reason_codes,
                    "message": ethics_result.user_message
                }
            )
            raise ValueError(f"Goal blocked by ethics policy: {ethics_result.user_message}")
        
        # Store ethics evaluation in metadata
        goal.metadata["ethics_evaluation"] = {
            "decision": ethics_result.decision.value,
            "reason_codes": ethics_result.reason_codes,
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        if ethics_result.decision == PolicyEffect.ALLOW_WITH_WARNING:
            goal.metadata["ethics_warning"] = ethics_result.user_message
            logger.info(f"[AGENCY_ENGINE] Goal allowed with warning: {title}")

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
            logger.debug("[AGENCY_ENGINE] World model not available, using basic goal creation")
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
            
            logger.info(
                f"[AGENCY_ENGINE] Enriched goal with world context: "
                f"{len(world_context.projects)} projects, "
                f"{len(world_context.entities)} entities, "
                f"{len(world_context.open_loops)} open loops"
            )
            
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
            logger.debug("[AGENCY_ENGINE] No Phase 2 services available, using basic goal creation")
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
                logger.debug(f"[AGENCY_ENGINE] Retrieving personality context for user {user_id}")
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
                
                logger.info(
                    f"[AGENCY_ENGINE] Personality adjustment: "
                    f"priority {priority.value} → {adjusted_priority.value}, "
                    f"proactivity={proactivity:.2f}"
                )
                
                # Use adjusted priority
                priority = adjusted_priority
            
            # Step 2: Get world model context
            if self.world_model:
                logger.debug(f"[AGENCY_ENGINE] Retrieving world context for user {user_id}")
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
                
                logger.info(
                    f"[AGENCY_ENGINE] World context: "
                    f"{len(world_context.projects)} projects, "
                    f"{len(world_context.entities)} entities"
                )
            
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
            logger.info(f"[AGENCY_ENGINE] Creating goal from curiosity signal: {signal.topic}")
            
            # Phase 4: Values & Ethics gate - evaluate curiosity signal
            ethics_result = self.values_ethics.evaluate_curiosity_signal(signal, user_id)
            
            if ethics_result.decision == PolicyEffect.BLOCK:
                logger.warning(
                    f"[AGENCY_ENGINE] Curiosity signal blocked by ethics policy: {signal.topic}"
                )
                # Log the blocked signal as an event
                await self.log_event(
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
                raise ValueError(f"Curiosity signal blocked by ethics policy: {ethics_result.user_message}")
            
            if ethics_result.decision == PolicyEffect.NEEDS_CONSENT:
                logger.info(
                    f"[AGENCY_ENGINE] Curiosity signal requires consent: {signal.topic}"
                )
                # Log consent requirement - actual consent flow handled by UX
                await self.log_event(
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
                # For now, don't create the goal - wait for explicit consent
                raise ValueError(f"Curiosity signal requires consent: {ethics_result.user_message}")
            
            if ethics_result.decision == PolicyEffect.ALLOW_WITH_WARNING:
                logger.info(
                    f"[AGENCY_ENGINE] Curiosity signal allowed with warning: {signal.topic}"
                )
                # Log the warning
                await self.log_event(
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
            
            # Build metadata with curiosity context
            metadata = {
                "curiosity_signal_id": signal.signal_id,
                "curiosity_type": signal.signal_type.value,
                "curiosity_score": signal.total_score,
                "novelty_score": signal.novelty_score,
                "user_relevance_score": signal.user_relevance_score,
                "source_component": signal.source_component,
                "topic_tags": signal.topic_tags,
            }
            
            # Add template info if available
            if "template_id" in signal.context:
                metadata["hobby_template_id"] = signal.context["template_id"]
                metadata["hobby_category"] = signal.context.get("category")
            
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
        # Get all pending goals for this user
        pending_goals = await self.goal_store.get_goals_by_status(
            user_id=user_id,
            status=GoalStatus.PENDING
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
                "analyzed_at": datetime.utcnow().isoformat(),
            },
        }
    
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
