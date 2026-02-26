"""
AICO Backend Lifecycle Manager - Clean FastAPI Integration

Centralized lifecycle management that properly integrates AICO's service container
with FastAPI's lifespan events, eliminating event loop conflicts and dependency issues.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger, initialize_logging
from aico.security import AICOKeyManager
from aico.core.paths import AICOPaths

from .service_container import ServiceContainer, BaseService
from backend.core.plugin_base import get_plugin_registry
from backend.api_gateway.core.protocol_manager import ProtocolAdapterManager
from backend.api_gateway.middleware.encryption import EncryptionMiddleware
# Import moved to avoid circular dependency

class BackendLifecycleManager:
    """
    Centralized lifecycle management for AICO backend
    
    Manages service container, FastAPI app creation, middleware configuration,
    and router mounting with proper dependency injection.
    """
    
    def __init__(self, config_manager: ConfigurationManager, role: str = "monolith"):
        self.config = config_manager
        self.logger = get_logger("backend.core.lifecycle_manager")
        import time
        self.start_time = time.time()

        self.role = role
        
        # Core components
        self.container = ServiceContainer(config_manager)
        self.db_connection: Optional[Any] = None
        self.app: Optional[FastAPI] = None
        
        # Protocol adapter manager for WebSocket and other protocols
        self.protocol_manager = ProtocolAdapterManager(
            config_manager.get("api_gateway", {}),
            self.logger
        )
        
        self.logger.debug("Backend lifecycle manager initialized")
    
    def _display_startup_status(self):
        """Display beautiful cross-platform startup status for all components"""
        # Minimal startup display - detailed status available via logs
        pass
    
    async def startup(self) -> FastAPI:
        """Complete backend startup sequence"""
        self.logger.debug("Starting AICO backend components...")
        
        # 1. Initialize PostgreSQL session factory FIRST (needed by AI processors)
        from backend.core.postgres_dependencies import initialize_postgres_dependencies
        await initialize_postgres_dependencies()
        self.logger.debug("PostgreSQL session factory initialized")
        
        # 2. Initialize service container (AI processors need UoW factory)
        await self._initialize_container()
        
        # 3. Initialize OpenTelemetry instrumentation (now has database access)
        await self._initialize_telemetry()
        
        self.logger.info(f"🔍 Role check: self.role='{self.role}', is_core={self.role == 'core'}, is_gateway={self.role == 'gateway'}")
        
        if self.role == "core":
            await self.container.start_all()
            self._display_service_status()
            self._display_plugin_status()
            
            # Initialize NATS request handlers for gateway→core communication
            await self._initialize_nats_handlers()
            
            self.logger.info("AICO core startup complete")
            return None

        # gateway / monolith
        self.logger.info("🚀 Starting gateway/monolith initialization (NOT core role)")
        self.app = self._create_fastapi_app()

        # Store start time in app state for health monitoring
        self.app.state.backend_start_time = self.start_time

        # Configure middleware stack
        self._configure_middleware()

        # Mount API routers
        self._mount_routers()

        # Instrument FastAPI with OpenTelemetry
        self._instrument_fastapi()

        # Start all services
        await self.container.start_all()

        # Display service and plugin startup status
        self._display_service_status()
        self._display_plugin_status()

        # Initialize gateway NATS client for gateway→core communication
        await self._initialize_gateway_nats_client()

        # Legacy broker startup is a no-op in NATS-only mode
        await self._start_message_broker()

        # Display available routes
        self._display_routes()

        # Start protocol adapters (WebSocket)
        await self._start_protocol_adapters()

        self.logger.info("AICO backend startup complete")
        return self.app
    
    async def stop(self) -> None:
        """Complete backend shutdown sequence with cross-platform status display"""
        self.logger.info("Shutting down AICO backend components...")
        
        # Stop protocol adapters first
        await self._stop_protocol_adapters()
        
        # Shutdown telemetry
        await self._shutdown_telemetry()
        
        # Stop service container
        if self.container:
            await self.container.stop_all()
        
        self.logger.info("Backend shutdown complete")
    
    async def _initialize_telemetry(self) -> None:
        """Initialize OpenTelemetry instrumentation"""
        try:
            from backend.core.telemetry import initialize_telemetry
            
            # Read instrumentation config from core.instrumentation
            enabled = self.config.get("instrumentation.enabled", False)
            mode = self.config.get("instrumentation.mode", "dev")

            if not enabled:
                self.logger.debug(
                    "OpenTelemetry instrumentation disabled via config (instrumentation.enabled = false); "
                    "skipping telemetry setup"
                )
                return

            self.logger.debug(f"Initializing OpenTelemetry instrumentation (enabled, mode={mode})")

            # Get encrypted database connection from container (will be available after container init)
            db_connection = None
            if hasattr(self, 'container') and self.container:
                try:
                    db_connection = self.container.get_service("database")
                except Exception:
                    self.logger.warning("Database connection not yet available for telemetry")
            
            # Build config dict expected by initialize_telemetry
            config_dict = {
                'instrumentation': {
                    'enabled': enabled,
                    'mode': mode
                }
            }
            
            initialize_telemetry(config_dict, db_connection=db_connection)
            
            self.logger.info("OpenTelemetry instrumentation initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize telemetry: {e}")
    
    def _instrument_fastapi(self) -> None:
        """Instrument FastAPI app with OpenTelemetry"""
        if not self.app:
            self.logger.warning("Cannot instrument FastAPI - app not created")
            return
        
        try:
            from backend.core.telemetry import instrument_fastapi
            instrument_fastapi(self.app)
            self.logger.info("FastAPI instrumented with OpenTelemetry")
            
        except Exception as e:
            self.logger.warning(f"Failed to instrument FastAPI: {e}")
    
    async def _shutdown_telemetry(self) -> None:
        """Shutdown OpenTelemetry and flush pending data"""
        try:
            from backend.core.telemetry import shutdown_telemetry
            shutdown_telemetry()
            
        except Exception as e:
            self.logger.warning(f"Error during telemetry shutdown: {e}")
    
    async def _initialize_container(self) -> None:
        """Initialize service container with all services"""
        self.container = ServiceContainer(self.config)
        
        # Register plugin classes first
        self._register_plugin_classes()
        
        # Register core services
        await self._register_core_services()

        # Register AI processors
        await self._register_ai_processors()
        
        # Register plugins
        await self._register_plugins()
        
        self.logger.info("Service container initialized")
    
    async def _register_core_services(self) -> None:
        """Register core infrastructure services"""
        
        # Database connection factory
        def create_database_connection(container: ServiceContainer) -> Any:
            # Legacy database connection - not used with PostgreSQL
            # PostgreSQL uses UnitOfWork pattern per request
            return None
        
        # Config service factory
        def create_config_service(container: ServiceContainer):
            return container.config
        
        # ChromaDB client factory (shared singleton)
        def create_chromadb_client(container: ServiceContainer):
            from aico.core.paths import AICOPaths
            import chromadb
            from chromadb.config import Settings
            
            chromadb_path = AICOPaths.get_semantic_memory_path()
            # Use consistent settings for all ChromaDB clients
            return chromadb.PersistentClient(
                path=str(chromadb_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True  # Match semantic memory settings
                )
            )
        
        # Register services
        self.container.register_service(
            "database",
            create_database_connection,
            dependencies=[],
            priority=5  # Start early, stop late
        )
        
        self.container.register_service(
            "chromadb_client",
            create_chromadb_client,
            dependencies=[],
            priority=6  # After database
        )
        
        self.container.register_service(
            "config",
            create_config_service,
            dependencies=[],
            priority=1  # Start first
        )
        
        # NOTE: Do not register shared UserService here.
        # Backend uses PostgreSQL via UnitOfWork/repositories; the shared UserService
        # expects an asyncpg connection and would be constructed with database=None
        # (since the backend's legacy `database` service is intentionally unused).
        
        if self.role != "gateway":
            # Task scheduler factory
            def create_task_scheduler(container: ServiceContainer):
                from backend.scheduler import TaskScheduler
                return TaskScheduler("task_scheduler", container)

            self.container.register_service(
                "task_scheduler",
                create_task_scheduler,
                dependencies=[],
                priority=25
            )

            # Emotion engine factory
            def create_emotion_engine(container: ServiceContainer):
                from backend.services.emotion_engine import EmotionEngine
                return EmotionEngine("emotion_engine", container)

            self.container.register_service(
                "emotion_engine",
                create_emotion_engine,
                dependencies=[],
                priority=30  # Start after message_bus (20), before conversation_engine (35)
            )

            # Conversation engine factory
            def create_conversation_engine(container: ServiceContainer, emotion_engine=None):
                from backend.services.conversation_engine import ConversationEngine
                return ConversationEngine("conversation_engine", container)

            self.container.register_service(
                "conversation_engine",
                create_conversation_engine,
                dependencies=["emotion_engine"],  # Ensure emotion engine is ready
                priority=35  # Start after message_bus (20) and emotion_engine (30)
            )
        
        self.logger.debug("Core services registered")

    async def _register_ai_processors(self) -> None:
        """Register core AI processors with the AI registry"""
        self.logger.info("Registering AI processors...")

        from aico.ai import ai_registry
        from aico.ai.memory.manager import MemoryManager
        from backend.services.modelservice_client import get_modelservice_client
        from aico.ai.agency import AgencyEngine
        from aico.ai.agency import bootstrap as agency_bootstrap

        # Get UoW factory for AI processors
        from backend.core.postgres_dependencies import get_uow_factory
        uow_factory = get_uow_factory()

        # ------------------------------------------------------------------
        # MemoryManager registration (using UoW pattern)
        # ------------------------------------------------------------------
        memory_manager = MemoryManager(self.config, uow_factory=uow_factory)
        self.logger.info("✅ Created MemoryManager with UoW factory")
        
        # Inject modelservice dependency for semantic memory
        try:
            modelservice_client = get_modelservice_client(self.config)
            memory_manager.set_modelservice(modelservice_client)
            self.logger.info("✅ Injected modelservice dependency into MemoryManager")
            
            # Note: We don't check modelservice health here because the modelservice depends on the backend,
            # not the other way around. The modelservice will connect to the backend's message bus when it starts.
        except Exception as e:
            self.logger.error(f"❌ Failed to inject modelservice into MemoryManager: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Force initialization to see config logs
        try:
            self.logger.info("🔧 [AI_PROCESSORS] Initializing MemoryManager...")
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule initialization for later and wait for it
                self.logger.info("🔧 [AI_PROCESSORS] Event loop is running, scheduling MemoryManager initialization...")
                await memory_manager.initialize()
            else:
                # Initialize immediately
                self.logger.info("🔧 [AI_PROCESSORS] Event loop not running, initializing MemoryManager immediately...")
                loop.run_until_complete(memory_manager.initialize())
            self.logger.info("✅ [AI_PROCESSORS] MemoryManager initialized during startup")
        except Exception as e:
            self.logger.error(f"❌ [AI_PROCESSORS] Failed to initialize MemoryManager during startup: {e}")
            import traceback
            self.logger.error(f"❌ [AI_PROCESSORS] Full traceback: {traceback.format_exc()}")
        
        ai_registry.register("memory", memory_manager)
        self.logger.info("Registered 'memory' processor.")

        # ------------------------------------------------------------------
        # AgencyEngine registration (Phase 1 goals & planning, Phase 2 context)
        # ------------------------------------------------------------------
        try:
            # Initialize agency tool registry (connectivity + maintenance tools).
            # This ensures import-time registration side effects have run before
            # any skills try to resolve their implementation tools.
            try:
                await agency_bootstrap.initialize()
                self.logger.info("[AI_PROCESSORS] Agency bootstrap completed (tools registered)")
            except Exception as exc:  # pragma: no cover - defensive safeguard
                self.logger.warning(
                    f"[AI_PROCESSORS] Agency bootstrap failed; some tools may be unavailable: {exc}"
                )

            # Phase 2: Initialize WorldModelService using initialized MemoryManager
            world_model = None
            try:
                from aico.ai.world_model import WorldModelService

                # Reuse KG storage and semantic memory from MemoryManager when available.
                kg_storage = None
                semantic_memory = None

                # Knowledge graph components are initialized lazily inside MemoryManager
                if getattr(memory_manager, "_kg_initialized", False):
                    kg_storage = getattr(memory_manager, "_kg_storage", None)

                # Semantic memory store (may be disabled via config)
                semantic_memory = getattr(memory_manager, "_semantic_store", None)

                if not kg_storage or not semantic_memory:
                    raise RuntimeError(
                        "Knowledge graph storage or semantic memory not available from MemoryManager"
                    )

                world_model = WorldModelService(
                    kg_storage=kg_storage,
                    semantic_memory=semantic_memory,
                    memory_manager=memory_manager,
                )
                self.logger.info("✅ [AI_PROCESSORS] Created WorldModelService (Phase 2)")
            except Exception as e:
                self.logger.warning(f"⚠️ [AI_PROCESSORS] Failed to create WorldModelService: {e}")
                self.logger.warning("⚠️ [AI_PROCESSORS] AgencyEngine will run without world model context")
            
            # Phase 2: Initialize PersonalityService
            personality_service = None
            try:
                from aico.ai.personality import PersonalityService
                
                personality_service = PersonalityService()
                self.logger.info("✅ [AI_PROCESSORS] Created PersonalityService (Phase 2)")
            except Exception as e:
                self.logger.warning(f"⚠️ [AI_PROCESSORS] Failed to create PersonalityService: {e}")
                self.logger.warning("⚠️ [AI_PROCESSORS] AgencyEngine will run without personality context")
            
            # Phase 3: Initialize CuriosityEngine
            curiosity_engine = None
            try:
                from aico.ai.curiosity import CuriosityEngine
                
                # Phase 6.3: Get AMS service for user interest tracking
                ams_service = None
                try:
                    ams_service = ai_registry.get("memory")  # MemoryManager provides AMS access
                except Exception as e:
                    logger.debug(f"Could not get AMS service: {e}")
                curiosity_engine = CuriosityEngine(
                    world_model=world_model,
                    personality_service=personality_service,
                    ams_service=ams_service,
                )
                self.logger.info("Created CuriosityEngine (Phase 6.3 with AMS integration)")
            except Exception as e:
                import traceback
                self.logger.warning(f"Failed to create CuriosityEngine: {e}")
                self.logger.warning("Curiosity-driven goals will not be generated")
            
            # Create message bus client for Phase 4 intention set publishing
            # Note: Connection will be established later when message bus broker is ready
            from aico.core.bus import MessageBusClient
            message_bus = MessageBusClient("agency_engine", config_manager=self.config)
            
            # Create AgencyService wrapper that manages UoW lifecycle per operation
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.agency_service import AgencyService
            
            session_factory = await get_session_factory()
            
            # Create a proxy that wraps AgencyService and manages UoW per method call
            class AgencyServiceProxy:
                """Proxy that creates UnitOfWork per method call."""
                def __init__(self, session_factory, skill_matcher=None):
                    self._session_factory = session_factory
                    self._skill_matcher = skill_matcher
                
                async def _execute_with_uow(self, method_name, *args, **kwargs):
                    async with UnitOfWork(self._session_factory) as uow:
                        service = AgencyService(uow, skill_matcher=self._skill_matcher)
                        method = getattr(service, method_name)
                        return await method(*args, **kwargs)
                
                # Delegate all AgencyService methods
                async def create_goal(self, goal):
                    return await self._execute_with_uow('create_goal', goal)
                
                async def get_goal(self, goal_id):
                    return await self._execute_with_uow('get_goal', goal_id)
                
                async def update_goal(self, goal):
                    return await self._execute_with_uow('update_goal', goal)
                
                async def list_goals(self, user_id=None, status=None):
                    return await self._execute_with_uow('list_goals', user_id=user_id, status=status)
                
                async def get_active_goals(self, user_id):
                    return await self._execute_with_uow('get_active_goals', user_id)
                
                async def get_goals_bulk(self, goal_ids):
                    return await self._execute_with_uow('get_goals_bulk', goal_ids)
                
                async def create_plan(self, plan):
                    return await self._execute_with_uow('create_plan', plan)

                # Plan management
                async def get_plan(self, plan_id: str):
                    return await self._execute_with_uow('get_plan', plan_id)

                async def list_plans(self, goal_id: str, status=None):
                    return await self._execute_with_uow('list_plans', goal_id=goal_id, status=status)

                async def update_plan(self, plan):
                    return await self._execute_with_uow('update_plan', plan)

                async def delete_plan(self, plan_id: str):
                    return await self._execute_with_uow('delete_plan', plan_id)

                async def get_active_plan(self, goal_id: str):
                    return await self._execute_with_uow('get_active_plan', goal_id)

                # Plan execution & steps (used by PlanExecutor)
                async def create_plan_execution(self, execution_data: Dict[str, Any]):
                    return await self._execute_with_uow('create_plan_execution', execution_data)

                async def get_plan_execution(self, execution_id: str):
                    return await self._execute_with_uow('get_plan_execution', execution_id)

                async def get_plan_executions(self, plan_id: str, limit: int = 10):
                    """Proxy to AgencyService.get_plan_executions with optional limit.

                    The underlying service method supports a limit parameter to avoid
                    loading unbounded execution history. Expose the same signature
                    here so API callers can explicitly bound the number of returned
                    executions.
                    """
                    return await self._execute_with_uow('get_plan_executions', plan_id, limit=limit)

                async def get_next_pending_step(self, execution_id: str):
                    return await self._execute_with_uow('get_next_pending_step', execution_id)

                async def count_pending_steps(self, execution_id: str) -> int:
                    return await self._execute_with_uow('count_pending_steps', execution_id)

                async def count_step_executions(self, execution_id: str) -> int:
                    return await self._execute_with_uow('count_step_executions', execution_id)

                async def get_step_executions(self, execution_id: str):
                    return await self._execute_with_uow('get_step_executions', execution_id)

                async def update_step_execution(self, step_execution_id: str, updates: Dict[str, Any]):
                    return await self._execute_with_uow('update_step_execution', step_execution_id, updates)

                async def update_plan_execution(self, execution_id: str, updates: Dict[str, Any]):
                    return await self._execute_with_uow('update_plan_execution', execution_id, updates)
                
                def set_skill_matcher(self, skill_matcher):
                    """Update the skill_matcher reference after AgencyEngine initializes it."""
                    self._skill_matcher = skill_matcher
            
            agency_service = AgencyServiceProxy(session_factory)
            
            # Create AgencyEngine with Phase 2 services and Phase 4 message bus
            agency_engine = AgencyEngine(
                self.config,
                agency_service=agency_service,
                world_model=world_model,
                personality_service=personality_service,
                message_bus=message_bus,
                memory_manager=memory_manager,
                session_factory=session_factory,
            )
            self.logger.info("✅ Created AgencyEngine with message bus and services")

            # Initialize AgencyEngine (placeholder hook for future behaviour)
            self.logger.info("🔧 [AI_PROCESSORS] Initializing AgencyEngine...")
            await agency_engine.initialize()
            self.logger.info("✅ [AI_PROCESSORS] AgencyEngine initialized during startup")
            
            # Update AgencyServiceProxy with skill_matcher after AgencyEngine initializes it
            if agency_engine.planner and agency_engine.planner.skill_matcher:
                agency_service.set_skill_matcher(agency_engine.planner.skill_matcher)
                self.logger.info("✅ [AI_PROCESSORS] Injected SkillMatcher into AgencyServiceProxy for auto-fixing old plans")
            
            # Phase 4: Install default policies if configured
            try:
                # Validate configuration exists
                values_ethics_config = self.config.get("agency.values_ethics", None)
                if values_ethics_config is None:
                    raise RuntimeError(
                        "CRITICAL: agency.values_ethics configuration not found in agency.yaml. "
                        "Phase 4 requires this configuration section."
                    )
                
                install_policies = self.config.get("agency.values_ethics.install_default_policies", True)
                policy_mode = self.config.get("agency.values_ethics.policy_mode", "enforce")
                
                self.logger.info(f"[AI_PROCESSORS] Values/Ethics policy mode: {policy_mode}")
                
                if install_policies:
                    from aico.ai.agency.default_policies import install_default_policies
                    from aico.data.uow import UnitOfWork
                    
                    self.logger.info("[AI_PROCESSORS] Installing default policy rules...")
                    
                    # Create UoW for policy installation
                    async with UnitOfWork(session_factory) as uow:
                        installed_count = await install_default_policies(agency_engine.values_ethics, uow)
                        if installed_count > 0:
                            self.logger.info(f"Installed {installed_count} default policy rules (Phase 4)")
                        else:
                            self.logger.info("Default policies already installed (Phase 4)")
                else:
                    self.logger.warning("Default policy installation disabled in configuration")
            except Exception as e:
                error_msg = f"Failed to initialize Phase 4 Values/Ethics policies: {e}"
                self.logger.error(f"{error_msg}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise RuntimeError(f"CRITICAL: {error_msg}")

            # Inject modelservice client for goal embeddings (needed for deduplication)
            try:
                agency_engine.modelservice_client = modelservice_client
                self.logger.info("✅ [AI_PROCESSORS] Injected modelservice client into AgencyEngine")
                
                # Update SkillMatcher with embedding client for skill gap deduplication
                agency_engine.update_skill_matcher_embedding_client()
            except Exception as e:
                self.logger.warning(f"⚠️ [AI_PROCESSORS] Failed to inject modelservice client: {e}")
                self.logger.warning("⚠️ [AI_PROCESSORS] AgencyEngine will not generate goal embeddings")
            
            # Inject LLM client into Planner for LLM-based plan generation
            try:
                agency_engine.set_llm_client(modelservice_client)
                self.logger.info("✅ [AI_PROCESSORS] Injected LLM client into Planner")
            except Exception as e:
                self.logger.warning(f"⚠️ [AI_PROCESSORS] Failed to inject LLM client: {e}")
                self.logger.warning("⚠️ [AI_PROCESSORS] Planner will use fallback planning only")
            
            # Inject LLM planning helper (Phase 1: templated prompts + hand-authored patterns)
            try:
                from backend.services.agency_planner import LLMPlanningHelper
                
                llm_helper = LLMPlanningHelper(self.config, modelservice_client)
                
                # Create refiner callback that wraps the helper
                async def llm_refiner_callback(goal, base_plan):
                    return await llm_helper.refine_plan_with_llm(goal, base_plan)
                
                agency_engine.set_llm_plan_refiner(llm_refiner_callback)
                self.logger.info("✅ [AI_PROCESSORS] Injected LLM planning helper into AgencyEngine")
            except Exception as e:
                self.logger.warning(f"⚠️ [AI_PROCESSORS] Failed to inject LLM planning helper: {e}")
                self.logger.warning("⚠️ [AI_PROCESSORS] AgencyEngine will use deterministic planning only")

            # Phase 5: Self-Reflection Engine (PostgreSQL)
            try:
                self_reflection_enabled = self.config.get("agency.self_reflection.enabled", False)
                if self_reflection_enabled:
                    from aico.ai.agency.reflection import SelfReflectionEngine

                    agency_engine.self_reflection = SelfReflectionEngine(
                        config=self.config,
                        session_factory=session_factory,
                        llm_client=modelservice_client,
                    )
                    self.logger.info("✅ [AI_PROCESSORS] Self-reflection engine enabled")
                else:
                    self.logger.info("[AI_PROCESSORS] Self-reflection engine disabled in configuration")
            except Exception as e:
                self.logger.error(f"CRITICAL: Failed to initialize self-reflection engine: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise RuntimeError(f"CRITICAL: Failed to initialize self-reflection engine: {e}")

            ai_registry.register("agency", agency_engine)
            self.logger.info("✅ Registered 'agency' processor with Phase 2 context services.")
            
            # Verify registration succeeded
            if ai_registry.get("agency") is None:
                raise RuntimeError("AgencyEngine registration failed - not found in ai_registry after registration")
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ CRITICAL: Failed to initialize AgencyEngine during startup: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            # Don't re-raise - allow backend to start but agency endpoints will fail gracefully
        
        # Register CuriosityEngine (Phase 3) - outside try/except to ensure it runs
        try:
            if curiosity_engine:
                ai_registry.register("curiosity", curiosity_engine)
                self.logger.info("Registered 'curiosity' processor (Phase 3).")
            else:
                self.logger.warning("CuriosityEngine was not created, skipping registration")
        except Exception as e:
            self.logger.error(f"Failed to register CuriosityEngine: {e}")

        # EmotionEngine is already registered in _register_core_services() (lines 266-275)
        # and will be started automatically by the service container

        self.logger.info("AI processors registered.")
    
    def _register_plugin_classes(self) -> None:
        """Register all plugin classes with the plugin registry"""
        from backend.api_gateway.plugins import (
            MessageBusPlugin,
            SecurityPlugin,
            RateLimitingPlugin,
            ValidationPlugin,
            RoutingPlugin,
            EncryptionPlugin
        )
        
        registry = get_plugin_registry()
        
        # Register plugin classes
        registry.register_plugin_class("message_bus", MessageBusPlugin)
        registry.register_plugin_class("security", SecurityPlugin)
        registry.register_plugin_class("rate_limiting", RateLimitingPlugin)
        registry.register_plugin_class("validation", ValidationPlugin)
        registry.register_plugin_class("routing", RoutingPlugin)
        registry.register_plugin_class("encryption", EncryptionPlugin)
        
        # Register AI plugin classes
        from backend.services.embodiment_engine import EmbodimentPlugin
        from backend.services.agency_engine import AgencyPlugin
        from backend.services.personality_engine import PersonalityPlugin
        
        registry.register_plugin_class("embodiment", EmbodimentPlugin)
        registry.register_plugin_class("agency", AgencyPlugin)
        registry.register_plugin_class("personality", PersonalityPlugin)
        
        # Note: EmotionEngine is registered as a service (lines 266-275), not a plugin
        
        self.logger.debug("Plugin classes registered")
    
    async def _register_plugins(self) -> None:
        """Register plugin services"""
        # Get plugin configuration
        plugin_config = self.config.get("api_gateway.plugins", {})
        
        for plugin_name, config in plugin_config.items():
            if not config.get("enabled", False):
                self.logger.debug(f"Plugin {plugin_name} disabled, skipping registration")
                continue
            
            # Get plugin factory from registry
            try:
                factory = get_plugin_registry().create_plugin_factory(plugin_name)
                
                # Determine dependencies based on plugin type
                dependencies = self._get_plugin_dependencies(plugin_name)
                
                # Register plugin service
                self.container.register_service(
                    f"{plugin_name}_plugin",
                    factory,
                    dependencies=dependencies,
                    priority=self._get_plugin_priority(plugin_name)
                )
                
                self.logger.debug(f"Registered plugin service: {plugin_name}_plugin")
                
            except Exception as e:
                self.logger.error(f"Failed to register plugin '{plugin_name}': {e}")
                # Fail fast - don't continue with broken plugins
                raise
        
        self.logger.debug("Plugin services registered")
    
    def _get_plugin_dependencies(self, plugin_name: str) -> list:
        """Get plugin dependencies based on plugin type"""
        # Standard dependencies for different plugin types
        dependency_map = {
            "security": ["database"],
            "encryption": ["database"],
            "rate_limiting": ["database"],
            "validation": [],
            "routing": [],
            "message_bus": [],
            # AI plugins need message bus for inter-plugin communication
            "embodiment": [],
            "agency": [],
            "emotion": [],
            "personality": [],
        }
        
        return dependency_map.get(plugin_name, [])
    
    def _get_plugin_priority(self, plugin_name: str) -> int:
        """Get plugin startup priority"""
        priority_map = {
            "message_bus": 20,
            "security": 30,
            "encryption": 35,
            "rate_limiting": 40,
            "validation": 45,
            "routing": 50,
            # AI plugins start after core infrastructure
            "embodiment": 60,
            "agency": 61,
            "emotion": 62,
            "personality": 63,
        }
        
        return priority_map.get(plugin_name, 100)
    
    async def _start_protocol_adapters(self) -> None:
        """Start protocol adapters (WebSocket, ZeroMQ)"""
        try:
            # Get protocol configuration
            protocols_config = self.config.get("api_gateway.protocols", {})
            
            # Prepare dependencies from service container
            dependencies = {
                'config': self.config,
                'logger': self.logger,
                'db_connection': self.container.get_service('database'),
            }
            
            # Add plugin services as dependencies
            try:
                security_plugin = self.container.get_service('security_plugin')
                if security_plugin:
                    dependencies['authz_manager'] = getattr(security_plugin, 'authz_manager', None)
                    dependencies['auth_manager'] = getattr(security_plugin, 'auth_manager', None)
            except:
                self.logger.warning("Security plugin not available for protocol adapters")
            
            try:
                routing_plugin = self.container.get_service('routing_plugin')
                if routing_plugin:
                    dependencies['message_router'] = getattr(routing_plugin, 'message_router', None)
            except:
                self.logger.warning("Routing plugin not available for protocol adapters")
            
            try:
                rate_limiting_plugin = self.container.get_service('rate_limiting_plugin')
                if rate_limiting_plugin:
                    dependencies['rate_limiter'] = getattr(rate_limiting_plugin, 'rate_limiter', None)
            except:
                self.logger.warning("Rate limiting plugin not available for protocol adapters")
            
            try:
                validation_plugin = self.container.get_service('validation_plugin')
                if validation_plugin:
                    dependencies['validator'] = getattr(validation_plugin, 'validator', None)
            except:
                self.logger.warning("Validation plugin not available for protocol adapters")
            
            # Initialize and start WebSocket adapter if enabled
            websocket_config = protocols_config.get("websocket", {})
            if websocket_config.get("enabled", True):
                await self.protocol_manager.initialize_adapter("websocket", websocket_config, dependencies)
                await self.protocol_manager.start_adapter("websocket")
            
            self.logger.info("Protocol adapters started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start protocol adapters: {e}")
            raise
    
    async def _stop_protocol_adapters(self) -> None:
        """Stop protocol adapters"""
        try:
            await self.protocol_manager.stop_all()
        except Exception as e:
            self.logger.error(f"Error stopping protocol adapters: {e}")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with proper lifespan"""
        
        @asynccontextmanager
        async def app_lifespan(app: FastAPI):
            # Services already started in startup() - just store references
            try:
                # Store container for dependency injection
                app.state.service_container = self.container
                app.state.lifecycle_manager = self
                
                # Store task scheduler for scheduler API endpoints
                task_scheduler = None
                try:
                    task_scheduler = self.container.get_service('task_scheduler')
                except Exception:
                    task_scheduler = None
                if task_scheduler:
                    app.state.task_scheduler = task_scheduler
                
                yield
                
            finally:
                # Shutdown handled by lifecycle manager
                # (actual shutdown called from main())
                pass
        
        # Import version function
        from aico.core.version import get_backend_version
        
        app = FastAPI(
            title="AICO Backend API",
            version=get_backend_version(),
            description="AICO Backend REST API with clean architecture",
            lifespan=app_lifespan
        )
        
        return app
    
    def _configure_middleware(self) -> None:
        """Configure middleware stack in correct order"""
        if not self.app:
            raise RuntimeError("FastAPI app not created")

        # Register exception handlers FIRST
        from backend.core.exception_handlers import register_exception_handlers
        register_exception_handlers(self.app)

        # 1. CORS middleware (outermost)
        from fastapi.middleware.cors import CORSMiddleware
        cors_origins = self.config.get(
            "api_gateway.cors_origins",
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3002",
                "http://127.0.0.1:3002",
            ],
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 2. Metrics middleware (collect request metrics)
        from backend.api_gateway.middleware.metrics import MetricsMiddleware
        self.app.add_middleware(MetricsMiddleware)

        # 3. Correlation context middleware (request-scoped IDs for structured logging)
        from fastapi import Request

        @self.app.middleware("http")
        async def inject_log_context(request: Request, call_next):
            from uuid import uuid4
            from aico.core.logging import set_log_context, clear_log_context

            request_id = request.headers.get("x-request-id") or str(uuid4())
            client_id = request.headers.get("x-client-id")
            session_id = request.headers.get("x-session-id")

            set_log_context(request_id=request_id, client_id=client_id, session_id=session_id)
            try:
                response = await call_next(request)
            finally:
                clear_log_context()

            try:
                response.headers.setdefault("x-request-id", request_id)
            except Exception:
                pass

            return response

        # 4. Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            if request.url.path.startswith("/api/v1/"):
                self.logger.debug(f"Request: {request.method} {request.url.path}")

            response = await call_next(request)

            if request.url.path.startswith("/api/v1/") and response.status_code >= 400:
                self.logger.warning(f"Response: {request.method} {request.url.path} -> {response.status_code}")

            return response
        
        # 5. Plugin-based middleware will be added by plugins during their initialization
        self.logger.debug("Middleware stack configured")
    
    def _display_service_status(self) -> None:
        """Display core service startup status"""
        # Service status available via logs
        pass
    
    def _display_plugin_status(self) -> None:
        """Display plugin startup status"""
        # Plugin status available via logs
        pass
    
    
    def _mount_routers(self) -> None:
        """Mount API routers with proper dependency injection"""
        if not self.app:
            raise RuntimeError("FastAPI app not created")

        self.logger.info("🚀 _mount_routers() called")
        
        # Mount domain routers
        try:
            self._mount_domain_routers()
            self.logger.info("✅ _mount_domain_routers() completed successfully")
        except Exception as e:
            self.logger.error(f"❌ _mount_domain_routers() FAILED: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        self.logger.debug("API routers mounted")

        # Apply encryption middleware as final ASGI wrapper (after all routers mounted)
        plugin_enabled = bool(self.config.get("api_gateway.plugins.encryption.enabled", True))
        transport_enabled = bool(self.config.get("security.transport.encryption.enabled", True))
        if plugin_enabled and transport_enabled:
            self.logger.debug("Starting encryption middleware initialization")
            key_manager = AICOKeyManager(self.config)
            # Store reference to FastAPI app before wrapping for route display
            self.fastapi_app = self.app
            # Create encryption middleware instance
            encryption_middleware = EncryptionMiddleware(self.app, key_manager)
            # Store middleware instance in app.state for access by streaming endpoints
            self.app.state.encryption_middleware = encryption_middleware
            # Wrap the app with the middleware
            self.app = encryption_middleware
            self.logger.debug("Encryption middleware started successfully")
        else:
            self.logger.info(
                "Encryption middleware disabled",
                extra={
                    "plugin_enabled": plugin_enabled,
                    "transport_enabled": transport_enabled,
                },
            )

    def _mount_domain_routers(self) -> None:
        """Mount domain-specific API routers"""
        self.logger.info("🔧 Starting router mounting process...")
        # Import routers
        from backend.api.handshake.router import router as handshake_router
        from backend.api.health.router import router as health_router
        from backend.api.echo.router import router as echo_router
        from backend.api.users.router import router as users_router
        from backend.api.admin.router import router as admin_router
        from backend.api.logs.router import router as logs_router
        from backend.api.conversation.router import router as conversation_router
        from backend.api.interactions.router import router as interactions_router
        from backend.api.memory.router import router as memory_router
        from backend.api.system.router import router as system_router
        from backend.api.system.health.router import router as system_health_router
        from backend.api.memory_album import router as memory_album_router
        from backend.api.kg.router import router as kg_router
        from backend.api.behavioral.router import router as behavioral_router
        from backend.api.emotion.router import router as emotion_router
        from backend.api.tts.router import router as tts_router
        from backend.api.agency.router import router as agency_router
        from backend.api.ams.router import router as ams_router
        from backend.api.operations.router import router as operations_router
        from backend.api.scheduler.router import router as scheduler_router
        from backend.api.users_sessions.router import router as users_sessions_router
        
        self.logger.info("✅ All routers imported successfully")
        
        # Mount routers with prefixes
        # NOTE: /api/v1/handshake is handled by EncryptionMiddleware, not a router
        # The middleware intercepts this path and processes handshakes with proper transport encryption
        # self.app.include_router(handshake_router, prefix="/api/v1/handshake", tags=["handshake"])
        # self.logger.info("✅ Mounted: /api/v1/handshake")

        self.app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
        self.logger.info("✅ Mounted: /api/v1/health")
        
        self.app.include_router(echo_router, prefix="/api/v1/echo", tags=["echo"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/echo", "tags": ["echo"]})
        
        self.app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/users", "tags": ["users"]})
        
        self.app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/admin", "tags": ["admin"]})
        
        self.app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/logs", "tags": ["logs"]})
        
        self.app.include_router(conversation_router, prefix="/api/v1/conversation", tags=["conversation"])
        self.logger.info("✅ Mounted: /api/v1/conversation")

        self.app.include_router(interactions_router, prefix="/api/v1/interactions", tags=["interactions"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/interactions", "tags": ["interactions"]})
        
        self.app.include_router(memory_router, prefix="/api/v1", tags=["memory"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1", "tags": ["memory"]})
        
        self.app.include_router(system_router, prefix="/api/v1/system", tags=["system"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/system", "tags": ["system"]})
        
        self.app.include_router(system_health_router, prefix="/api/v1/system", tags=["system-health"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/system", "tags": ["system-health"]})
        
        self.app.include_router(memory_album_router, prefix="/api/v1/memory-album", tags=["memory-album"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/memory-album", "tags": ["memory-album"]})
        
        self.app.include_router(kg_router, prefix="/api/v1/kg", tags=["knowledge-graph"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/kg", "tags": ["knowledge-graph"]})
        
        self.app.include_router(behavioral_router, prefix="/api/v1/behavioral", tags=["behavioral"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/behavioral", "tags": ["behavioral"]})
        
        self.app.include_router(emotion_router, prefix="/api/v1/emotion", tags=["emotion"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/emotion", "tags": ["emotion"]})
        
        self.app.include_router(tts_router, prefix="/api/v1/tts", tags=["tts"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/tts", "tags": ["tts"]})
        
        self.app.include_router(agency_router, prefix="/api/v1/agency", tags=["agency"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/agency", "tags": ["agency"]})
        
        self.app.include_router(ams_router, prefix="/api/v1", tags=["ams"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1", "tags": ["ams"]})
        
        self.app.include_router(operations_router, prefix="/api/v1/operations", tags=["operations"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/operations", "tags": ["operations"]})
        
        self.app.include_router(scheduler_router, prefix="/api/v1/scheduler", tags=["scheduler"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/scheduler", "tags": ["scheduler"]})
        
        self.app.include_router(users_sessions_router, prefix="/api/v1/users-sessions", tags=["users-sessions"])
        self.logger.debug("Router mounted", extra={"prefix": "/api/v1/users-sessions", "tags": ["users-sessions"]})
        
        self.logger.info(f"🎉 Router mounting complete: {len(self.app.routes)} total routes")
    
    def _display_routes(self) -> None:
        """Display available API route groups"""
        # Route information available via logs
        pass
    
    async def _start_message_broker(self) -> None:
        """Start message broker"""
        # NATS-only: broker is an external dependency
        # Legacy embedded broker startup is intentionally disabled.
        self.logger.info("Message broker startup skipped (NATS-only; external bus)")
    
    def _notify_log_transport_broker_ready(self) -> None:
        """Notify log transport that broker is ready"""
        # Logs now go directly to InfluxDB
        # Log consumer service removed - no longer needed
        pass
    
    def _notify_log_consumer_broker_ready(self) -> None:
        """Notify log consumer service that broker is ready and schedule buffer flush after subscription"""
        # Log consumer service removed - logs now go directly to InfluxDB
        pass
    
    async def _connect_log_consumer_and_flush_buffer(self, log_consumer):
        """Connect log consumer and flush buffer after subscription is complete"""
        # Log consumer service removed - logs now go directly to InfluxDB
        pass
    
    def _display_log_consumer_status(self) -> None:
        """Display log consumer service status"""
        # Log consumer service removed - logs now go directly to InfluxDB
        pass
    
    async def _debug_log_consumer_initialization(self) -> None:
        """Debug log consumer initialization issues"""
        # Log consumer service removed - logs now go directly to InfluxDB
        pass


# Dependency injection functions for FastAPI
    async def _initialize_nats_handlers(self) -> None:
        """Initialize NATS request handlers for gateway→core communication"""
        try:
            from backend.core.nats_handlers import CoreNATSHandlers
            from aico.core.bus import MessageBusClient
            
            # Create dedicated message bus client for request handling
            message_bus = MessageBusClient("core_request_handler")
            await message_bus.connect()
            
            # Initialize and register handlers
            handlers = CoreNATSHandlers(self.container)
            await handlers.setup_handlers(message_bus)
            
            self.logger.info("✅ NATS request handlers initialized for gateway→core communication")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NATS handlers: {e}", exc_info=True)
            # Don't fail startup if NATS handlers fail - core services can still work

    async def _initialize_gateway_nats_client(self) -> None:
        """Initialize gateway NATS client for making requests to core"""
        try:
            from backend.api_gateway.core.nats_client import initialize_gateway_nats_client
            from aico.core.bus import MessageBusClient
            
            # Create dedicated message bus client for gateway requests
            message_bus = MessageBusClient("gateway_nats_client")
            await message_bus.connect()
            
            # Initialize the singleton
            initialize_gateway_nats_client(message_bus)
            self.logger.info("✅ Gateway NATS client initialized for core communication")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize gateway NATS client: {e}", exc_info=True)


def get_service_container(request: Request) -> ServiceContainer:
    """Get service container from FastAPI app state"""
    if not hasattr(request.app.state, 'service_container'):
        raise RuntimeError("Service container not available")
    return request.app.state.service_container

def get_auth_manager(container: ServiceContainer = Depends(get_service_container)):
    """Get auth manager via dependency injection"""
    # Auth manager is provided by security plugin
    security_plugin = container.get_service("security_plugin")
    if not security_plugin or not hasattr(security_plugin, 'auth_manager'):
        raise RuntimeError("Auth manager not available")
    return security_plugin.auth_manager

def get_database(container: ServiceContainer = Depends(get_service_container)) -> Any:
    """Get database connection via dependency injection"""
    return container.get_service("database")
