"""
AICO Conversation Engine

Central orchestrator for conversation flow that coordinates all AI components
to generate contextual, multimodal responses for authenticated users.

Design Principles:
- Simple, maintainable code structure
- Clear separation of concerns
- Extensible scaffolding for future features
- Easy debugging and testing
"""

import asyncio
import logging
import uuid
import time
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_core_envelope_pb2 import AicoMessage
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_modelservice_pb2 import CompletionsResponse, CompletionsRequest, ConversationMessage as ModelConversationMessage
from aico.ai import ProcessingContext, ai_registry
from aico.ai.llm.factory import LLMClientFactory
from aico.ai.characters import CharacterManager
from aico.data.uow import UnitOfWork
from core.services.ai_plugin_base import ProcessingRequest
from aico.common.service_container import BaseService
from google.protobuf.timestamp_pb2 import Timestamp

# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class ResponseMode(Enum):
    """Response delivery modes"""
    TEXT_ONLY = "text_only"
    MULTIMODAL = "multimodal"  # Text + Avatar + Voice
    PROACTIVE = "proactive"    # Autonomous initiation


@dataclass
class UserContext:
    """Per-user conversation context"""
    user_id: str
    username: str
    full_name: Optional[str] = None  # User's full name from database
    nickname: Optional[str] = None  # User's nickname from database
    relationship_type: str = "user"  # user, family_member, admin, etc.
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_style: str = "friendly"
    conversation_language: str = "en"  # ISO/BCP-47 language code for this conversation
    last_seen: Optional[datetime] = None
    
    # Scaffolding for future features
    voice_profile: Optional[Dict[str, Any]] = None  # Voice biometrics (future)
    behavioral_patterns: Dict[str, Any] = field(default_factory=dict)  # Behavior analysis (future)
    relationship_context: Dict[str, Any] = field(default_factory=dict)  # Family relationships (future)


# Deprecated thread management classes removed - using semantic memory approach


class ConversationEngine(BaseService):
    """
    Central conversation orchestrator for AICO.
    
    Responsibilities:
    - Manage per-user conversation threads
    - Coordinate AI component responses (emotion, personality, memory, LLM)
    - Handle multimodal response generation (text, avatar, voice)
    - Provide scaffolding for autonomous agency
    
    Design: Simple, maintainable, extensible
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        # Use AICO logging system instead of standard logging
        # self.logger is already set by BaseService using get_logger("backend", f"service.{name}")
        
        # Message bus client
        self.bus_client: Optional[MessageBusClient] = None

        # LLM client (vLLM)
        self.llm_client = None
        
        # Character manager
        self.character_manager = None

        # Optional agency plugin (wired via feature flag and service container)
        self.agency_plugin = None
        
        # AI Processing uses global registry
        # Processors registered via: ai_registry.register("emotion", processor_instance)
        
        # User context management (simplified)
        self.user_contexts: Dict[str, UserContext] = {}
        
        # AI processing coordination
        self.pending_responses: Dict[str, Dict[str, Any]] = {}  # request_id -> response data

        # Streaming chunk routing (subscribe once; route by request_id)
        self._modelservice_stream_subscribed = False

        # Configuration - access via core.conversation path (like other services)
        # NOTE: These configs are validated at startup - if missing, startup fails
        engine_config = self.container.config.get("conversation", {})
        features_config = engine_config.get("features", {})
        plugins_config = self.container.config.get("api_gateway.plugins", {})
        
        # Feature flags for gradual implementation
        self.enable_emotion_integration = features_config.get("enable_emotion_integration", False)
        self.enable_personality_integration = features_config.get("enable_personality_integration", False)
        self.enable_memory_integration = features_config.get("enable_memory_integration", True)  # RE-ENABLED - was disabled for test
        self.enable_embodiment = features_config.get("enable_embodiment", False)

        # Agency is controlled solely by the agency plugin being enabled
        agency_plugin_config = plugins_config.get("agency", {})
        self.enable_agency = bool(agency_plugin_config.get("enabled", False))
        
        
        self.max_context_messages = engine_config.get("max_context_messages", 10)
        self.response_timeout = engine_config.get("response_timeout_seconds", 15.0)
        self.default_response_mode = ResponseMode(engine_config.get("default_response_mode", "text_only"))
        
        # Initialize LLM client (vLLM)
        try:
            llm_config = self.container.config.get("llm")
            if not llm_config:
                raise ValueError("CRITICAL: Missing llm configuration")
            
            self.llm_client = LLMClientFactory.create(llm_config)
            self.logger.info("✅ vLLM client initialized")
        except Exception as e:
            raise ValueError(f"CRITICAL: Failed to initialize vLLM client: {e}")
        
        # Initialize character manager
        try:
            self.character_manager = CharacterManager(self.container.config)
            
            # Get default character from config
            vllm_config = self.container.config.get("llm.vllm", {})
            self.character_name = vllm_config.get("default_character", "eve")
            
            # Load character configuration
            character_config = self.character_manager.get_character(self.character_name)
            self.model_name = character_config.get("base_model")
            
            self.logger.info(f"✅ Character manager initialized: {self.character_name} ({self.model_name})")
        except Exception as e:
            raise ValueError(f"CRITICAL: Failed to initialize character manager: {e}")
        
        self.logger.debug(f"Conversation engine using model: {self.model_name}")

    def get_active_features(self) -> List[str]:
        """Return a list of enabled AI integration features."""
        features = []
        if self.enable_emotion_integration: features.append("emotion")
        if self.enable_personality_integration: features.append("personality")
        if self.enable_memory_integration: features.append("memory")
        if self.enable_embodiment: features.append("embodiment")
        if self.enable_agency: features.append("agency")
        return features
    
    async def initialize(self) -> None:
        """Initialize service resources - called once during startup"""
        # Configuration is handled in __init__.
        pass
    
    async def start(self) -> None:
        """Start the conversation engine service"""
        try:
            self.logger.info("Starting conversation engine...")
            
            # Initialize message bus client
            self.bus_client = MessageBusClient("conversation_engine")
            await self.bus_client.connect()
            self.logger.debug("Message bus client connected")
            
            # AI processors will be registered here when implemented
            # No initialization needed for empty registry

            # Optional: resolve agency plugin from service container when enabled
            if self.enable_agency:
                try:
                    self.agency_plugin = self.container.get_service("agency_plugin")
                    if self.agency_plugin:
                        self.logger.debug("[AGENCY] Agency plugin resolved and ready for Phase 0 wiring")
                    else:
                        self.logger.warning("[AGENCY] enable_agency=True but agency_plugin service not found")
                except Exception as e:
                    self.logger.warning(f"[AGENCY] Failed to resolve agency_plugin service: {e}")
            
            # Subscribe to conversation topics
            await self._setup_subscriptions()
            self.logger.debug("Subscriptions established")
            
            self.logger.info("Conversation engine started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start conversation engine: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the conversation engine service"""
        try:
            self.logger.info("Stopping conversation engine...")
            
            # No AI coordinator cleanup needed
            
            if self.bus_client:
                await self.bus_client.disconnect()
            
            self.logger.info("Conversation engine stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping conversation engine: {e}")
    
    # ============================================================================
    # MESSAGE BUS SETUP
    # ============================================================================
    
    async def _setup_subscriptions(self) -> None:
        """Set up message bus subscriptions based on enabled features"""
        # Core conversation input
        # IMPORTANT: MessageBusClient.publish() tenant-scopes subjects as:
        #   aico.<tenant_id>.<topic.replace('/', '.')>
        # Core runs multi-tenant, so it must subscribe with a wildcard tenant prefix.
        topic_subject = AICOTopics.CONVERSATION_USER_INPUT.replace("/", ".")
        wildcard_pattern = f"aico.*.{topic_subject}"
        self.logger.info(f"🔍 [SUBSCRIPTION] Subscribing to wildcard pattern: {wildcard_pattern}")
        await self.bus_client.subscribe(
            wildcard_pattern,
            self._handle_user_input,
        )
        self.logger.info(f"✅ [SUBSCRIPTION] Successfully subscribed to: {wildcard_pattern}")
        
        # Note: LLM response subscriptions are now dynamic per-request
        # Each request subscribes to its own response topic: modelservice/chat/response/v1/conversation_engine/{request_id}
        # This eliminates cross-talk between conversation engine and other services (KG, etc.)
        
        # Optional component subscriptions
        # Note: Emotion integration uses direct service access (emotion_engine.get_current_state())
        # User emotion detection (Phase 2+) will subscribe to AI_EMOTION_ANALYSIS_RESPONSE
        # if self.enable_emotion_integration:
        #     await self.bus_client.subscribe(
        #         AICOTopics.AI_EMOTION_ANALYSIS_RESPONSE,
        #         self._handle_emotion_response
        #     )
        
        if self.enable_personality_integration:
            await self.bus_client.subscribe(
                AICOTopics.PERSONALITY_EXPRESSION_RESPONSE,
                self._handle_personality_response
            )
        
        # V2: Direct memory integration - no message bus subscriptions needed
        
        self.logger.debug("Message bus subscriptions established")
    
    # ============================================================================
    # CORE MESSAGE HANDLERS
    # ============================================================================
    
    async def _handle_user_input(self, message) -> None:
        """Handle incoming user input message from conversation API"""
        self.logger.info(
            f"🔍 [CORE_RECEIVE] ConversationEngine received user input message! "
            f"message_id={message.metadata.message_id if message.metadata else 'unknown'}"
        )
        try:
            # The message is an AicoMessage envelope, need to unpack the ConversationMessage
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            
            # Unpack the ConversationMessage from the AicoMessage envelope
            conv_message = ConversationMessage()
            message.any_payload.Unpack(conv_message)
            
            # DEBUG: Log the received message structure
            self.logger.info(
                f"🔍 [DEBUG] Received ConversationMessage: turn_number={conv_message.message.turn_number}, "
                f"text='{conv_message.message.text[:50]}...', conversation_id={conv_message.message.conversation_id}"
            )

            tenant_id = None
            request_id = None
            try:
                tenant_id = message.metadata.attributes.get("tenant_id")
                request_id = message.metadata.attributes.get("request_id")
            except Exception:
                tenant_id = None
                request_id = None
            
            # Extract user information from the message
            # Use user_id field (actual user UUID), not source (which is just "conversation_api")
            user_id = conv_message.user_id if conv_message.user_id else conv_message.source
            conversation_id = conv_message.message.conversation_id
            
            self.logger.debug(
                "[DEBUG] ConversationEngine: Received user input.",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "message_type": conv_message.message.type,
                },
            )
            
            # Get user context (simplified)
            user_context = await self._get_or_create_user_context(user_id)

            # Persist conversation + user message (REQUIRED - Postgres is the source of truth)
            if not tenant_id:
                self.logger.error(
                    "[CRITICAL] Missing tenant_id in envelope metadata; cannot persist or process conversation.",
                    extra={
                        "request_id": conv_message.message_id,
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "envelope_attributes": dict(getattr(message.metadata, "attributes", {}) or {}),
                    },
                )
                await self._publish_persistence_error(
                    request_id=conv_message.message_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error=f"Missing tenant_id in envelope metadata",
                )
                return
            if not request_id:
                self.logger.error(
                    "[CRITICAL] Missing request_id in envelope metadata; cannot correlate persistence/response.",
                    extra={
                        "request_id": conv_message.message_id,
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "envelope_attributes": dict(getattr(message.metadata, "attributes", {}) or {}),
                    },
                )
                await self._publish_persistence_error(
                    request_id=conv_message.message_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error=f"Missing request_id in envelope metadata",
                )
                return

            try:
                await self._persist_user_message(
                    tenant_id=tenant_id,
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=conv_message.message.text,
                )
            except Exception as e:
                self.logger.error(f"Failed to persist user message (aborting processing): {e}")
                await self._publish_persistence_error(
                    request_id=conv_message.message_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error=f"Failed to persist user message: {e}",
                )
                return

            # Generate response using semantic memory approach
            # IMPORTANT: tenant_id + http_request_id must be available for assistant persistence
            # before any LLM generation/finalization occurs.
            await self._generate_response(
                user_context,
                conv_message,
                tenant_id=tenant_id,
                http_request_id=request_id,
            )

            # Phase 6: Async goal extraction (fire-and-forget, no blocking)
            if self.enable_agency and self.agency_plugin:
                try:
                    message_text = conv_message.message.text
                    asyncio.create_task(
                        self._extract_user_goal_async(
                            user_id=user_id,
                            message_id=conv_message.message_id,
                            message_text=message_text,
                            conversation_id=conversation_id,
                        )
                    )
                except Exception as task_error:
                    self.logger.error(f"Goal extraction task creation failed: {task_error}")
            
        except Exception as e:
            self.logger.error(f"Error handling user input: {e}", extra={
                "error": str(e)
            })

    async def _publish_persistence_error(
        self,
        *,
        request_id: str | None,
        user_id: str,
        conversation_id: str,
        error: str,
    ) -> None:
        """Publish an explicit error response and terminate any streaming for this request.

        This prevents API callers from hanging/timeouting when persistence fails.
        """
        try:
            if not self.bus_client:
                return

            from aico.core.topics import AICOTopics

            rid = request_id or str(uuid.uuid4())

            # Terminate streaming with an error marker (if the client is streaming)
            try:
                from aico.proto.aico_conversation_pb2 import StreamingResponse as StreamingResponseProto

                error_chunk = StreamingResponseProto(
                    request_id=rid,
                    content=error,
                    accumulated_content=error,
                    done=True,
                    content_type="error",
                )
                # Get user context for routing
                pending_data = self.pending_responses.get(rid, {})
                user_context = pending_data.get("user_context")
                tenant_id = pending_data.get("tenant_id")
                
                attributes = {}
                if user_context:
                    attributes["user_uuid"] = user_context.user_id
                
                await self.bus_client.publish(
                    AICOTopics.CONVERSATION_STREAM,
                    error_chunk,
                    tenant_id=tenant_id,
                    correlation_id=rid,
                    attributes=attributes if attributes else None,
                )
            except Exception:
                # Streaming termination is best-effort; the HTTP API should still get an error response.
                pass

            # Also publish a normal final response message (non-streaming path)
            from aico.proto.aico_conversation_pb2 import ConversationMessage, Message
            from google.protobuf.timestamp_pb2 import Timestamp
            import time

            ai_message = Message()
            ai_message.conversation_id = conversation_id
            ai_message.type = Message.MessageType.SYSTEM_RESPONSE
            ai_message.text = error
            # turn_number assigned automatically by repository

            conv_message = ConversationMessage()
            conv_message.message_id = rid
            conv_message.user_id = user_id
            conv_message.source = "conversation_engine"

            ts = Timestamp()
            ts.FromSeconds(int(time.time()))
            conv_message.timestamp.CopyFrom(ts)
            conv_message.message.CopyFrom(ai_message)

            await self.bus_client.publish(
                AICOTopics.CONVERSATION_RESPONSE,
                conv_message,
                tenant_id=tenant_id,
                correlation_id=rid,
            )
            await self.bus_client.publish(
                "conversation/ai/response/v1",
                conv_message,
                tenant_id=tenant_id,
                correlation_id=rid,
            )
        except Exception as e:
            self.logger.error(f"Failed to publish persistence error response: {e}")
    
    # ============================================================================
    # USER & THREAD MANAGEMENT
    # ============================================================================
    
    async def _get_or_create_user_context(self, user_id: str) -> UserContext:
        """Get or create user context for authenticated user"""
        if user_id not in self.user_contexts:
            # Load user data from database
            user_profile = None
            try:
                from aico.data.postgres.connection import get_session_factory
                from aico.data.uow import UnitOfWork

                session_factory = await get_session_factory()
                async with UnitOfWork(session_factory) as uow:
                    user_profile = await uow.users.get_by_id(user_id)
            except Exception as e:
                self.logger.warning(f"Failed to load user profile from database: {e}")
            
            # Create context with database data or fallback to placeholder
            if user_profile:
                self.user_contexts[user_id] = UserContext(
                    user_id=user_id,
                    username=user_profile.nickname or user_profile.full_name or f"User_{user_id[:8]}",
                    full_name=user_profile.full_name,
                    nickname=user_profile.nickname,
                    relationship_type="user",
                    conversation_style="friendly",
                    conversation_language=user_profile.primary_language or "en",
                    last_seen=datetime.now(UTC)
                )
                self.logger.debug(f"Loaded user context from database", extra={
                    "user_id": user_id,
                    "full_name": user_profile.full_name,
                    "nickname": user_profile.nickname
                })
            else:
                # Fallback to placeholder if database load fails
                self.user_contexts[user_id] = UserContext(
                    user_id=user_id,
                    username=f"User_{user_id[:8]}",
                    relationship_type="user",
                    conversation_style="friendly",
                    conversation_language="en",
                    last_seen=datetime.now(UTC)
                )
                self.logger.warning(f"Created placeholder user context (database load failed)", extra={
                    "user_id": user_id
                })
        else:
            # Update last seen
            self.user_contexts[user_id].last_seen = datetime.now(UTC)
        
        return self.user_contexts[user_id]
    
# Thread management removed - using semantic memory for conversation continuity
    
    # ============================================================================
    # MESSAGE ANALYSIS & RESPONSE GENERATION
    # ============================================================================
    
    # Message analysis removed - semantic memory handles context automatically
    
    async def _generate_response(
        self,
        user_context: UserContext,
        user_message: ConversationMessage,
        *,
        tenant_id: str,
        http_request_id: str,
    ) -> None:
        """Generate and deliver response based on enabled features"""
        try:
            # Use the message_id from the API Gateway as request_id for proper correlation
            request_id = user_message.message_id if user_message.message_id else str(uuid.uuid4())
            
            # Initialize response tracking (simplified)
            self.pending_responses[request_id] = {
                "user_context": user_context,
                "user_message": user_message,
                # Required for Postgres source-of-truth persistence
                "tenant_id": tenant_id,
                "http_request_id": http_request_id,
                "components_needed": [],
                "components_ready": {},
                "started_at": datetime.now(UTC)
            }
            
            # Determine what components we need
            components_needed = []
            
            # Get memory context if enabled
            memory_context = None
            if self.enable_memory_integration:
                try:
                    memory_context = await self._get_memory_context(request_id, user_context, user_message)
                    if memory_context is None:
                        self.logger.error(f"Memory context retrieval returned None for request {request_id}")
                except Exception as e:
                    self.logger.error(f"Exception calling _get_memory_context(): {e}")
                    memory_context = None

            # Phase 0: Minimal agency wiring (no behavioural changes yet)
            # Skip agency for technical users
            is_technical_user = False
            try:
                from aico.data.postgres.connection import get_session_factory
                from aico.data.uow import UnitOfWork

                session_factory = await get_session_factory()
                async with UnitOfWork(session_factory) as uow:
                    profile = await uow.users.get_by_id(user_context.user_id)
                    if profile and getattr(profile, "is_technical", False):
                        is_technical_user = True
            except Exception:
                is_technical_user = False

            if self.enable_agency and self.agency_plugin and not is_technical_user:
                try:
                    self.logger.debug(f"[AGENCY] Phase 0: invoking agency plugin for request {request_id}")
                    agency_context: Dict[str, Any] = {
                        "memory_context": memory_context,
                        "user_context": {
                            "user_id": user_context.user_id,
                            "conversation_language": user_context.conversation_language,
                        },
                    }
                    agency_request = ProcessingRequest(
                        request_id=request_id,
                        user_id=user_context.user_id,
                        conversation_id=user_message.message.conversation_id,
                        text=user_message.message.text,
                        context=agency_context,
                        timestamp=datetime.now(UTC),
                    )
                    agency_response = await self.agency_plugin.process(agency_request)
                    self.logger.debug(
                        f"[AGENCY] Phase 0: agency plugin completed for {request_id} (success={agency_response.success}, "
                        f"confidence={agency_response.confidence}, keys={list(agency_response.data.keys())})"
                    )
                    # Store agency response in components_ready for future phases
                    self.pending_responses[request_id]["components_ready"]["agency"] = {
                        "request_id": agency_response.request_id,
                        "data": agency_response.data,
                        "confidence": agency_response.confidence,
                        "processing_time_ms": agency_response.processing_time_ms,
                        "success": agency_response.success,
                        "error": agency_response.error,
                    }
                except Exception as e:
                    self.logger.error(f"[AGENCY] Phase 0: error while invoking agency plugin for {request_id}: {e}")
            
            # Generate LLM response with memory context
            await self._generate_llm_response(request_id, user_context, user_message, memory_context)

            if request_id not in self.pending_responses:
                self.logger.warning(
                    "Request %s was cleaned up during LLM generation; skipping post-LLM bookkeeping",
                    request_id,
                )
                return

            self.pending_responses[request_id]["components_needed"] = components_needed
            
            # Note: LLM response already generated above, no need for fallback logic
            
            # Set timeout - normal responses should be 1-6 seconds
            self.logger.debug(f"🔍 [ENGINE_FLOW] Request {request_id} created, starting timeout handler")
            asyncio.create_task(self._response_timeout_handler(request_id))
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}", extra={
                "conversation_id": user_message.message.conversation_id
            })
    
    # ============================================================================
    # AI COMPONENT INTEGRATION (SCAFFOLDING)
    # ============================================================================
    
    # Emotion and personality integration removed - focusing on semantic memory approach
    
    
    async def _get_memory_context(self, request_id: str, user_context: UserContext, message: ConversationMessage) -> Optional[Dict[str, Any]]:
        """Get memory context (working + semantic) - returns None if unavailable"""
        try:
            self.logger.debug(f"🧠 [CONTEXT_TRACE] Starting context retrieval for request {request_id}")
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ❌ Memory manager NOT registered in ai_registry")
                return None
            
            self.logger.debug(f"🧠 [CONTEXT_TRACE] ✅ Memory manager found")
            
            user_id = user_context.user_id
            conversation_id = message.message.conversation_id
            message_text = message.message.text
            
            self.logger.debug(f"🧠 [CONTEXT_TRACE] Calling memory_manager.assemble_context(user_id={user_id}, conversation_id={conversation_id})")
            
            # Get context from memory manager
            context = await memory_manager.assemble_context(
                user_id=user_id,
                current_message=message_text,
                conversation_id=conversation_id
            )
            
            # Log what we got back
            if context:
                memory_data = context.get("memory_context", {})
                user_facts = memory_data.get("user_facts", [])
                recent_context = memory_data.get("recent_context", [])
                metadata = context.get("metadata", {})
                
                self.logger.debug(f"🧠 [CONTEXT_TRACE] ✅ Context retrieved:")
                self.logger.debug(f"🧠 [CONTEXT_TRACE]   - user_facts: {len(user_facts)} items")
                self.logger.debug(f"🧠 [CONTEXT_TRACE]   - recent_context: {len(recent_context)} messages")
                self.logger.debug(f"🧠 [CONTEXT_TRACE]   - total_items: {metadata.get('total_items', 0)}")
                self.logger.debug(f"🧠 [CONTEXT_TRACE]   - assembly_time: {metadata.get('assembly_time_ms', 0):.2f}ms")
                
                if user_facts:
                    self.logger.debug(f"🧠 [CONTEXT_TRACE] Sample user_facts: {user_facts[0].get('content', 'N/A')[:100]}...")
                if recent_context:
                    self.logger.debug(f"🧠 [CONTEXT_TRACE] Sample recent_context: {recent_context[0].get('content', 'N/A')[:100]}...")
            else:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ⚠️  Context is None or empty")
            
            # Store user message for future context
            try:
                await memory_manager.store_message(user_id, conversation_id, message_text, "user", language=user_context.conversation_language)
                self.logger.debug(f"User message stored for future context")
            except Exception as e:
                self.logger.warning(f"Failed to store user message: {e}")
            
            return context
                
        except Exception as e:
            self.logger.error(f"🧠 [CONTEXT_TRACE] ❌ EXCEPTION in _get_memory_context: {e}")
            import traceback
            self.logger.error(f"🧠 [CONTEXT_TRACE] Traceback: {traceback.format_exc()}")
            return None

    async def _process_memory_background(self, request_id: str, user_context: UserContext, message: ConversationMessage):
        """Store user message in background for future context (storage only)"""
        try:
            start_time = time.time()
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                self.logger.error(f"🔍 [MEMORY_BACKGROUND] Memory manager not available for {request_id}")
                return
            
            user_id = user_context.user_id
            conversation_id = message.message.conversation_id
            message_text = message.message.text
            
            self.logger.debug(f"🔍 [MEMORY_BACKGROUND] Starting background message storage for {request_id}")
            
            # Store user message for future context (let it take as long as needed - it's background)
            try:
                await memory_manager.store_message(user_id, conversation_id, message_text, "user", language=user_context.conversation_language)
                total_duration = time.time() - start_time
                self.logger.debug(f"🔍 [MEMORY_BACKGROUND] ✅ User message stored in {total_duration:.3f}s for {request_id}")
            except Exception as e:
                total_duration = time.time() - start_time
                self.logger.error(f"🔍 [MEMORY_BACKGROUND] ❌ Storage failed after {total_duration:.3f}s for {request_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"🔍 [MEMORY_BACKGROUND] ❌ Background memory processing failed for {request_id}: {e}")


    # ============================================================================
    # COMPONENT RESPONSE HANDLERS
    # ============================================================================
    
    async def _handle_emotion_response(self, topic: str, response: Any) -> None:
        """Handle emotion analysis response"""
        try:
            request_id = response.get("request_id") if isinstance(response, dict) else None
            if request_id and request_id in self.pending_responses:
                self.pending_responses[request_id]["components_ready"]["emotion"] = response
                await self._check_response_completion(request_id)
        except Exception as e:
            self.logger.error(f"Error handling emotion response: {e}")
    
    async def _handle_personality_response(self, topic: str, response: Any) -> None:
        """Handle personality expression response"""
        try:
            request_id = response.get("request_id") if isinstance(response, dict) else None
            if request_id and request_id in self.pending_responses:
                self.pending_responses[request_id]["components_ready"]["personality"] = response
                await self._check_response_completion(request_id)
        except Exception as e:
            self.logger.error(f"Error handling personality response: {e}")
    
    # V2: Memory response handler removed - direct integration used instead
    
    async def _check_response_completion(self, request_id: str) -> None:
        """Check if all components are ready and generate final response"""
        try:
            if request_id not in self.pending_responses:
                return
            
            pending_data = self.pending_responses[request_id]
            needed = set(pending_data["components_needed"])
            ready = set(pending_data["components_ready"].keys())
            
            if needed.issubset(ready):
                # All components ready, generate LLM response
                user_context = pending_data["user_context"]
                user_message = pending_data["user_message"]
                context = pending_data["components_ready"]
                
                await self._generate_llm_response(request_id, user_context, user_message, context)
                
        except Exception as e:
            self.logger.error(f"Error checking response completion: {e}")
    
    # ============================================================================
    # LLM INTEGRATION & RESPONSE DELIVERY
    # ============================================================================
    
    async def _generate_llm_response(self, request_id: str, user_context: UserContext, user_message: ConversationMessage, memory_context: Optional[Dict[str, Any]]) -> None:
        """Generate LLM response with memory context and skill selection"""
        from aico.core.topics import AICOTopics
        try:
            # Check if LLM request already sent to prevent duplicates
            if request_id in self.pending_responses and self.pending_responses[request_id].get("llm_request_sent"):
                return
            
            # Phase 3: Select skill for this interaction
            selected_skill_id = await self._select_skill(user_context, user_message, memory_context)
            if selected_skill_id:
                self.pending_responses[request_id]["selected_skill_id"] = selected_skill_id
                self.logger.debug(f"🎯 [SKILL] Selected skill: {selected_skill_id}")
            
            # Build system prompt with memory context and skill template
            if memory_context is None:
                self.logger.warning(f"No memory context provided for request {request_id}")
            else:
                memory_data = memory_context.get("memory_context", {})
                user_facts = memory_data.get("user_facts", [])
                recent_context = memory_data.get("recent_context", [])
                self.logger.debug(f"Context: {len(user_facts)} facts, {len(recent_context)} messages")
            
            # Build system message with character personality + memory context
            memory_facts = None
            if memory_context:
                memory_data = memory_context.get("memory_context", {})
                user_facts = memory_data.get("user_facts", [])
                if user_facts:
                    memory_facts = {"facts": [f.get("content", "") for f in user_facts]}
            
            system_message = self.character_manager.build_system_message(
                self.character_name,
                memory_context=memory_facts
            )
            
            # Build messages for LLM
            messages = [system_message]
            
            # Add conversation history as actual messages (not just in system prompt)
            history_message_count = 0
            history_truncated_count = 0
            if memory_context:
                memory_data = memory_context.get("memory_context", {})
                recent_context = memory_data.get("recent_context", [])
                max_history_messages = 4
                max_history_chars_per_message = 600
                max_history_chars_total = 2400
                
                # CRITICAL: recent_context is in REVERSE chronological order (newest first)
                # We need to reverse it to get chronological order (oldest first) for LLM
                # Take last 5 messages and reverse them
                history_messages = list(reversed(recent_context[:max_history_messages]))
                
                self.logger.debug(f"🧠 [CONTEXT_TRACE] Processing {len(history_messages)} history messages for LLM")
                history_chars_total = 0
                for msg in history_messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '').strip()
                    if not content:
                        continue

                    remaining_budget = max_history_chars_total - history_chars_total
                    if remaining_budget <= 0:
                        break

                    truncated = False
                    content_limit = min(max_history_chars_per_message, remaining_budget)
                    if len(content) > content_limit:
                        content = content[: max(0, content_limit - 1)] + "…"
                        truncated = True

                    messages.append(ModelConversationMessage(role=role, content=content))
                    history_message_count += 1
                    history_chars_total += len(content)
                    self.logger.debug(f"🧠 [CONTEXT_TRACE] ✅ Added {role} message to LLM: {content[:80]}...")
                    if truncated:
                        history_truncated_count += 1
                        self.logger.debug(f"🧠 [CONTEXT_TRACE] ⚠️  Truncated {role} history message to {len(content)} chars")
                
                # CRITICAL VALIDATION: Warn if no conversation history was added
                if history_message_count == 0 and len(recent_context) > 0:
                    self.logger.error(f"🚨 [CONTEXT_ERROR] recent_context has {len(recent_context)} items but ZERO messages added to LLM!")
                    self.logger.error(f"🚨 [CONTEXT_ERROR] Sample item keys: {list(recent_context[0].keys()) if recent_context else 'N/A'}")
                else:
                    self.logger.debug(f"🧠 [CONTEXT_TRACE] ✅ Added {history_message_count} history messages to LLM context")
            else:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ⚠️  No memory_context provided - LLM has no conversation history")
            
            # Add current user message
            current_content = user_message.message.text.strip()
            current_user_chars = len(current_content) if current_content else 0
            if current_content:
                messages.append(ModelConversationMessage(role="user", content=current_content))

            system_chars = len(system_message.get("content", "")) if system_message else 0
            history_chars = history_chars_total if memory_context else 0
            self.logger.info(
                "🧠 [LLM_CONTEXT] request_id=%s model=%s messages=%s system_chars=%s history_msgs=%s history_chars=%s history_trunc=%s user_chars=%s",
                request_id,
                self.model_name,
                len(messages),
                system_chars,
                history_message_count,
                history_chars,
                history_truncated_count,
                current_user_chars,
            )
            
            # Get character parameters
            character_params = self.character_manager.get_parameters(self.character_name)
            
            # Convert messages to dict format for LLM client
            llm_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    llm_messages.append(msg)
                else:
                    llm_messages.append({"role": msg.role, "content": msg.content})
            
            # Call vLLM directly (async streaming)
            try:
                self.logger.info(f"🚀 [vLLM] Calling vLLM with {len(llm_messages)} messages, model={self.model_name}")

                # True streaming from vLLM (OpenAI-compatible stream)
                stream_iter = await self.llm_client.chat_completion(
                    messages=llm_messages,
                    model=self.model_name,
                    stream=True,
                    **character_params,
                )

                from aico.proto.aico_conversation_pb2 import StreamingResponse as StreamingResponseProto
                from aico.core.topics import AICOTopics

                # Split stream into two channels:
                # - content_type="thinking": content inside <think>...</think>
                # - content_type="response": content outside tags
                accumulated_response = ""
                accumulated_thinking = ""
                chunk_count = 0

                in_think = False
                parse_buffer = ""
                open_tag = "<think>"
                close_tag = "</think>"
                
                # Define attributes for NATS publishing (used in _publish_delta and final chunk)
                pending_data = self.pending_responses.get(request_id, {})
                tenant_id_for_attrs = pending_data.get("tenant_id")
                attributes = {"user_uuid": user_context.user_id}

                def _emit_safe_non_tag_suffix(buf: str, tag: str) -> tuple[str, str]:
                    """Return (emit_text, keep_suffix) keeping at most len(tag)-1 chars to handle split tags."""
                    keep_len = max(0, len(tag) - 1)
                    if keep_len == 0 or len(buf) <= keep_len:
                        return "", buf
                    return buf[:-keep_len], buf[-keep_len:]

                async def _publish_delta(delta_text: str, *, content_type: str) -> None:
                    nonlocal accumulated_response, accumulated_thinking
                    if not delta_text:
                        return

                    if content_type == "thinking":
                        accumulated_thinking += delta_text
                        accumulated_for_type = accumulated_thinking
                    else:
                        accumulated_response += delta_text
                        accumulated_for_type = accumulated_response

                    streaming_chunk = StreamingResponseProto(
                        request_id=request_id,
                        content=delta_text,
                        accumulated_content=accumulated_for_type,
                        done=False,
                        content_type=content_type,
                    )

                    await self.bus_client.publish(
                        AICOTopics.CONVERSATION_STREAM,
                        streaming_chunk,
                        tenant_id=tenant_id_for_attrs,
                        correlation_id=request_id,
                        attributes=attributes,
                    )

                async for chunk in stream_iter:
                    try:
                        # openai-python streaming chunk object
                        if not getattr(chunk, "choices", None):
                            continue
                        choice0 = chunk.choices[0]
                        delta = getattr(choice0, "delta", None)

                        # vLLM/OpenAI-compatible servers may expose reasoning/thinking separately
                        # (e.g., delta.reasoning or delta.reasoning_content). If present, stream it
                        # as content_type="thinking" so the Flutter right drawer can display it.
                        delta_reasoning = None
                        if delta is not None:
                            delta_reasoning = getattr(delta, "reasoning", None)
                            if not delta_reasoning:
                                delta_reasoning = getattr(delta, "reasoning_content", None)

                        if delta_reasoning:
                            chunk_count += 1
                            await _publish_delta(str(delta_reasoning), content_type="thinking")
                            if chunk_count == 1:
                                self.logger.info(f"📤 [vLLM] Published first streaming delta")

                        delta_content = getattr(delta, "content", None) if delta else None
                        if not delta_content:
                            # can be role/tool_calls/etc.
                            continue

                        chunk_count += 1

                        parse_buffer += delta_content

                        # Incrementally parse think tags, even if tags are split across deltas.
                        while True:
                            if not in_think:
                                idx = parse_buffer.find(open_tag)
                                if idx == -1:
                                    emit_text, keep_suffix = _emit_safe_non_tag_suffix(parse_buffer, open_tag)
                                    if emit_text:
                                        await _publish_delta(emit_text, content_type="response")
                                    parse_buffer = keep_suffix
                                    break

                                # Emit response text before <think>
                                before = parse_buffer[:idx]
                                if before:
                                    await _publish_delta(before, content_type="response")

                                # Consume the open tag
                                parse_buffer = parse_buffer[idx + len(open_tag):]
                                in_think = True
                                continue

                            # in_think
                            idx = parse_buffer.find(close_tag)
                            if idx == -1:
                                emit_text, keep_suffix = _emit_safe_non_tag_suffix(parse_buffer, close_tag)
                                if emit_text:
                                    await _publish_delta(emit_text, content_type="thinking")
                                parse_buffer = keep_suffix
                                break

                            before = parse_buffer[:idx]
                            if before:
                                await _publish_delta(before, content_type="thinking")

                            parse_buffer = parse_buffer[idx + len(close_tag):]
                            in_think = False
                            continue

                        if chunk_count == 1:
                            self.logger.info(f"📤 [vLLM] Published first streaming delta")

                    except Exception as e:
                        self.logger.error(f"❌ [vLLM] Error processing streaming delta: {e}")

                # Flush remaining parse buffer after stream ends
                if parse_buffer:
                    if in_think:
                        await _publish_delta(parse_buffer, content_type="thinking")
                    else:
                        await _publish_delta(parse_buffer, content_type="response")
                    parse_buffer = ""

                assistant_content = accumulated_response
                self.logger.info(
                    f"✅ [vLLM] Streaming complete ({chunk_count} deltas, response_chars={len(accumulated_response)}, thinking_chars={len(accumulated_thinking)})"
                )

                # Store response for delivery
                self.pending_responses[request_id]["llm_response"] = assistant_content

                # Final done=True marker chunk
                self.logger.info(f"🏁 [STREAMING] About to publish final done=True chunk for request_id={request_id}")
                final_chunk = StreamingResponseProto(
                    request_id=request_id,
                    content="",
                    accumulated_content=assistant_content,
                    done=True,
                    content_type="response",
                )
                await self.bus_client.publish(
                    AICOTopics.CONVERSATION_STREAM,
                    final_chunk,
                    tenant_id=tenant_id_for_attrs,
                    correlation_id=request_id,
                    attributes=attributes,
                )
                self.logger.info(f"✅ [STREAMING] Published final done=True chunk for request_id={request_id}")

                self.logger.info(f"📤 [vLLM] Delivering response to user via _finalize_streaming_response")

                # Deliver final response to user
                await self._finalize_streaming_response(request_id, assistant_content)

                self.logger.info(f"✅ [vLLM] Response delivered successfully")
                
            except Exception as e:
                self.logger.error(f"❌ [vLLM] vLLM call failed: {e}", exc_info=True)
                # Clean up and re-raise - no fallback to Ollama/modelservice
                if request_id in self.pending_responses:
                    await self._cleanup_request(request_id)
                raise
            # Streaming chunks are handled by the shared subscription handler
            # (_handle_modelservice_stream_chunk)
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}")
            await self._cleanup_request(request_id)

    async def _handle_modelservice_stream_chunk(self, envelope) -> None:
        """Route modelservice streaming chunks to the correct pending request."""
        try:
            from aico.proto.aico_modelservice_pb2 import StreamingChunk
            streaming_chunk = StreamingChunk()
            envelope.any_payload.Unpack(streaming_chunk)

            request_id = streaming_chunk.request_id
            if not request_id or request_id not in self.pending_responses:
                return

            chunk_content = streaming_chunk.content
            accumulated_content = streaming_chunk.accumulated_content
            content_type = streaming_chunk.content_type
            is_done = streaming_chunk.done

            # Publish streaming chunk to API layer
            from aico.proto.aico_conversation_pb2 import StreamingResponse
            import time

            streaming_response = StreamingResponse()
            streaming_response.request_id = request_id
            streaming_response.content = chunk_content
            streaming_response.accumulated_content = accumulated_content
            streaming_response.done = is_done
            streaming_response.timestamp = int(time.time() * 1000)
            streaming_response.content_type = content_type

            # Get user context for routing
            pending_data = self.pending_responses.get(request_id, {})
            user_context = pending_data.get("user_context")
            tenant_id = pending_data.get("tenant_id")
            
            attributes = {}
            if user_context:
                attributes["user_uuid"] = user_context.user_id
            
            await self.bus_client.publish(
                AICOTopics.CONVERSATION_STREAM,
                streaming_response,
                tenant_id=tenant_id,
                correlation_id=request_id,
                attributes=attributes if attributes else None,
            )

            if is_done:
                await self._finalize_streaming_response(request_id, accumulated_content)

        except Exception as e:
            self.logger.error(f"Error routing streaming chunk: {e}")
    
    async def _handle_streaming_response(self, request_id: str, stream_topic: str) -> None:
        """LEGACY: Per-request streaming handler.

        This method is intentionally disabled.

        Rationale:
        - Subscribing to the global stream topic per-request caused an ever-growing
          callback list and degraded performance until requests timed out.
        - Streaming is now handled by a single shared subscription:
          `self._handle_modelservice_stream_chunk()`.

        Kept temporarily for reference while the new routing logic bakes.
        """
        self.logger.warning(
            "DEPRECATED: _handle_streaming_response() was called (request_id=%s, stream_topic=%s). "
            "This method is intentionally disabled; streaming is routed via _handle_modelservice_stream_chunk().",
            request_id,
            stream_topic,
        )
        return
    
    async def _finalize_streaming_response(self, request_id: str, final_content: str, thinking_content: str = "") -> None:
        """Finalize streaming response and deliver to user (semantic memory approach)"""
        try:
            self.logger.info(f"🔍 [FINALIZE] Starting finalization for request_id={request_id}")
            
            if request_id not in self.pending_responses:
                self.logger.warning(f"Request {request_id} not found in pending responses")
                return
            
            request_data = self.pending_responses[request_id]
            user_message = request_data["user_message"]
            
            # Extract user info from the original message
            user_id = user_message.user_id
            conversation_id = user_message.message.conversation_id

            tenant_id = request_data.get("tenant_id")
            http_request_id = request_data.get("http_request_id")
            
            self.logger.info(f"🔍 [FINALIZE] user_id={user_id}, conversation_id={conversation_id}")

            # Persist assistant message (REQUIRED - Postgres is the source of truth)
            if not tenant_id:
                await self._publish_persistence_error(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error="Missing tenant_id for request",
                )
                return
            if not http_request_id:
                await self._publish_persistence_error(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error="Missing http_request_id for request",
                )
                return

            try:
                await self._persist_assistant_message(
                    tenant_id=tenant_id,
                    request_id=http_request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=final_content,
                )
            except Exception as e:
                self.logger.error(f"Failed to persist assistant message (aborting delivery): {e}")
                await self._publish_persistence_error(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    error=f"Failed to persist assistant message: {e}",
                )
                return
            
            # NOTE: AI response storage happens in streaming handler (line ~895)
            # to avoid duplicate storage
            # Store thinking in message metadata if present
            
            # Create final response message for API layer
            ai_message = Message()
            ai_message.conversation_id = conversation_id
            ai_message.type = Message.MessageType.SYSTEM_RESPONSE
            ai_message.text = final_content
            # turn_number assigned automatically by repository
            
            # NOTE: Thinking is already delivered via streaming chunks with content_type="thinking"
            # No need to store it in the final message - frontend handles it during streaming
            
            # Create ConversationMessage for API layer (with message_id)
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            from google.protobuf.timestamp_pb2 import Timestamp
            import time
            
            conv_message = ConversationMessage()
            conv_message.message_id = request_id  # Set message_id for API layer
            conv_message.user_id = user_id
            conv_message.source = "conversation_engine"
            
            # Set timestamp
            timestamp = Timestamp()
            timestamp.FromSeconds(int(time.time()))
            conv_message.timestamp.CopyFrom(timestamp)
            
            # Set the message content
            conv_message.message.CopyFrom(ai_message)
            
            # Publish final response to both topics for compatibility
            try:
                self.logger.info(f"🔍 [FINALIZE] Publishing to NATS topic: {AICOTopics.CONVERSATION_RESPONSE}")
                await self.bus_client.publish(
                    AICOTopics.CONVERSATION_RESPONSE,
                    conv_message,
                    tenant_id=tenant_id,
                    correlation_id=request_id,
                )
                self.logger.info(f"✅ [FINALIZE] Published to {AICOTopics.CONVERSATION_RESPONSE}")

                # Also publish to AI response topic for API layer with user_uuid for WS routing
                self.logger.info(f"🔍 [FINALIZE] Publishing to NATS topic: conversation/ai/response/v1")
                await self.bus_client.publish(
                    "conversation/ai/response/v1",
                    conv_message,
                    tenant_id=tenant_id,
                    correlation_id=request_id,
                    attributes={"user_uuid": user_id},
                )
                self.logger.info(f"✅ [FINALIZE] Published to conversation/ai/response/v1")
            except Exception as publish_error:
                self.logger.error(f"❌ [FINALIZE] Final response publish failed; enqueueing outbox fallback: {publish_error}")
                try:
                    await self._enqueue_outbox_fallback(
                        tenant_id=tenant_id,
                        topics=[AICOTopics.CONVERSATION_RESPONSE, "conversation/ai/response/v1"],
                        payload_envelope=conv_message,
                        correlation_id=request_id,
                    )
                except Exception as outbox_error:
                    self.logger.error(f"❌ [FINALIZE] Outbox enqueue failed after publish failure: {outbox_error}")
            
            # Phase 3: Log trajectory for behavioral learning
            if request_id in self.pending_responses:
                pending_data = self.pending_responses[request_id]
                
                user_context = pending_data.get("user_context")
                user_message = pending_data.get("user_message")
                selected_skill_id = pending_data.get("selected_skill_id")
                agency_data = pending_data.get("components_ready", {}).get("agency")
                
                if user_context and user_message:
                    await self._log_trajectory(
                        user_context,
                        user_message,
                        final_content,  # Fixed: use final_content parameter
                        selected_skill_id,
                        agency_data  # Pass agency context
                    )
            
            await self._cleanup_request(request_id)
            
        except Exception as e:
            self.logger.error(f"Error finalizing streaming response for {request_id}: {e}")

    async def _enqueue_outbox_fallback(
        self,
        *,
        tenant_id: str,
        topics: list[str],
        payload_envelope: Any,
        correlation_id: str,
    ) -> None:
        """Enqueue an outbox event for later publication.

        This is a fallback path used only when inline publish fails.
        It must never be used for streaming chunks.
        """
        if not self.bus_client:
            raise RuntimeError("bus_client not available")

        from aico.data.outbox.models import OutboxEvent
        from aico.data.postgres.connection import get_session_factory

        # We enqueue the raw NATS payload bytes (protobuf envelope) so the outbox publisher
        # can publish without needing protobuf types.
        if self.bus_client._nats is None:  # type: ignore[attr-defined]
            raise RuntimeError("NATS client not connected")

        # Rebuild the exact bytes that MessageBusClient.publish() would send.
        from aico.proto.aico_core_envelope_pb2 import AicoMessage
        from google.protobuf.any_pb2 import Any as ProtoAny
        from aico.core.bus import _create_message_metadata

        now = datetime.now(UTC)
        session_factory = await get_session_factory()

        async with UnitOfWork(session_factory) as uow:
            for topic in topics:
                metadata = _create_message_metadata(
                    message_id=str(uuid.uuid4()),
                    source="conversation_engine",
                    message_type=topic,
                )
                metadata.attributes["correlation_id"] = correlation_id

                envelope = AicoMessage()
                envelope.metadata.CopyFrom(metadata)
                any_payload = ProtoAny()
                any_payload.Pack(payload_envelope)
                envelope.any_payload.CopyFrom(any_payload)
                payload_bytes = envelope.SerializeToString()

                event = OutboxEvent(
                    event_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    subject=topic.replace("/", "."),
                    payload_bytes=payload_bytes,
                    status="pending",
                    attempts=0,
                    available_at=now,
                    created_at=now,
                    sent_at=None,
                )
                await uow.outbox_events.enqueue(event)

    async def _persist_user_message(
        self,
        *,
        tenant_id: str,
        request_id: str,
        user_id: str,
        conversation_id: str,
        content: str,
    ) -> None:
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.data.conversation.models import ConversationMessage

        now = datetime.now(UTC)
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            await uow.conversations.touch(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                status="active",
            )
            await uow.conversation_messages.create_idempotent(
                ConversationMessage(
                    message_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    actor_type="user",
                    actor_id=user_id,
                    message_type="user_input",
                    content=content,
                    correlation_id=request_id,
                    request_id=request_id,
                    turn_number=0,  # Repository assigns actual sequential turn number
                    created_at=now,
                )
            )

        # Best-effort working-memory population (UI uses this for "Working" stats).
        # Keep this decoupled from persistence: failures must not affect the golden path.
        try:
            memory_manager = ai_registry.get("memory")
            if memory_manager:
                await memory_manager.store_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                    role="user",
                )
        except Exception as e:
            self.logger.warning(f"Failed to store user message in working memory: {e}")

    async def _persist_assistant_message(
        self,
        *,
        tenant_id: str,
        request_id: str,
        user_id: str,
        conversation_id: str,
        content: str,
    ) -> None:
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.data.conversation.models import ConversationMessage

        now = datetime.now(UTC)
        session_factory = await get_session_factory()
        async with UnitOfWork(session_factory) as uow:
            await uow.conversations.touch(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                agent_id=getattr(self, "character_name", None),
                status="active",
            )
            await uow.conversation_messages.create_idempotent(
                ConversationMessage(
                    message_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    agent_id=getattr(self, "character_name", None),
                    actor_type="agent",
                    actor_id=getattr(self, "character_name", None),
                    message_type="ai_response",
                    content=content,
                    correlation_id=request_id,
                    request_id=request_id,
                    turn_number=0,  # Repository assigns actual sequential turn number
                    created_at=now,
                )
            )

        # Best-effort working-memory population (UI uses this for "Working" stats).
        try:
            memory_manager = ai_registry.get("memory")
            if memory_manager:
                await memory_manager.store_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                    role="assistant",
                )
        except Exception as e:
            self.logger.warning(f"Failed to store assistant message in working memory: {e}")
    
    def _build_system_prompt(self, user_context: UserContext, memory_context: Optional[Dict[str, Any]], skill_id: Optional[str] = None, user_message: Optional[ConversationMessage] = None) -> str:
        """Build system prompt with memory context and optional skill template
        
        NOTE: Character personality is defined in the Modelfile (e.g., Modelfile.eve).
        This method only adds contextual information like memory facts, NOT character definition.
        
        Returns empty string if there's no contextual information to add, allowing the
        Modelfile's SYSTEM instruction to be the sole system prompt.
        """
        # DO NOT define character here - that's in the Modelfile
        # Only add contextual information that helps with the current conversation
        prompt_parts = []

        # Language policy: default to the user's preferred language unless they explicitly ask otherwise
        effective_language = None
        if user_context and getattr(user_context, "conversation_language", None):
            effective_language = user_context.conversation_language
            self.logger.debug(
                f"🗣️ [LANG_POLICY] conversation_language from user_context: {effective_language}",
            )
        else:
            self.logger.debug("🗣️ [LANG_POLICY] No conversation_language found on user_context; language will follow model defaults")

        if effective_language:
            prompt_parts.append(
                f"The user's preferred language is {effective_language}. You must respond in this language unless the user explicitly asks you in their CURRENT message to reply in a different language. Do not switch languages just because past memories or content are in another language."
            )
            self.logger.debug(f"🗣️ [LANG_POLICY] Added language directive to system prompt for language={effective_language}")
        
        # Phase 3: Add skill template if selected
        if skill_id:
            try:
                memory_manager = ai_registry.get("memory")
                if memory_manager and hasattr(memory_manager, '_skill_store') and memory_manager._skill_store:
                    # Synchronously access skill from database (get_skill is async but we're in sync context)
                    # TODO: Cache skills at initialization to avoid this sync/async mismatch
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is running, we can't use asyncio.run()
                            # Skip skill template injection in this case
                            self.logger.debug(f"🎯 [SKILL] Skipping skill template (event loop running)")
                        else:
                            skill = asyncio.run(memory_manager._skill_store.get_skill(skill_id))
                            if skill:
                                prompt_parts.append(f"Interaction style:\n{skill.procedure_template}")
                                self.logger.debug(f"🎯 [SKILL] Injected skill template: {skill.skill_name}")
                    except RuntimeError:
                        # No event loop, create one
                        skill = asyncio.run(memory_manager._skill_store.get_skill(skill_id))
                        if skill:
                            prompt_parts.append(f"Interaction style:\n{skill.procedure_template}")
                            self.logger.debug(f"🎯 [SKILL] Injected skill template: {skill.skill_name}")
            except Exception as e:
                self.logger.warning(f"🎯 [SKILL] Failed to inject skill template: {e}")
        
        # Add identity context - CRITICAL for LLM to know who it is and who it's talking to
        identity_parts = []
        
        # CRITICAL: Tell the LLM its character name (e.g., "Eve" from model "eve:latest")
        # This prevents the LLM from defaulting to its base model name (e.g., "Qwen")
        if getattr(self, "character_name", None):
            identity_parts.append(f"Your name is {self.character_name}.")
        elif self.model_name:
            # Extract character name from model.
            # Examples:
            # - "eve:latest" -> "Eve"
            # - "boeni/eve:latest" -> "Eve"
            # - "huihui_ai/qwen3-abliterated:latest" -> "Qwen3-abliterated" (still better than full path)
            model_base = self.model_name.split(":", 1)[0]
            model_base = model_base.rsplit("/", 1)[-1]
            character_name = model_base.strip().capitalize() if model_base else ""
            if character_name:
                identity_parts.append(f"Your name is {character_name}.")
        
        # Get user's first name from database
        if user_context and hasattr(user_context, 'full_name') and user_context.full_name:
            try:
                user_first_name = user_context.full_name.split()[0]
                # Make this VERY explicit so the LLM doesn't ignore it
                identity_parts.append(f"The person you are talking to is named {user_first_name}. This is their actual name from your memory system. When they ask if you remember their name, you should tell them their name is {user_first_name}.")
            except (IndexError, AttributeError):
                # If full_name is empty or malformed, skip user name
                pass
        
        if identity_parts:
            prompt_parts.append("\n".join(identity_parts))
        
        # Add emotional conditioning if available (Phase 1 emotion system)
        if self.enable_emotion_integration:
            try:
                emotion_engine = self.container.get_service("emotion_engine")
                if emotion_engine:
                    # Get current emotional state (compact projection)
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Skip in this case - emotion will still be published to bus
                            pass
                        else:
                            emotional_state = asyncio.run(emotion_engine.get_current_state())
                            if emotional_state:
                                style = emotional_state.get("style", {})
                                label = emotional_state.get("label", {})
                                
                                # Build concise emotional guidance
                                emotion_guidance = []
                                emotion_guidance.append(f"Current emotional tone: {label.get('primary', 'calm')}")
                                
                                # Add style hints
                                warmth = style.get("warmth", 0.6)
                                energy = style.get("energy", 0.5)
                                directness = style.get("directness", 0.5)
                                
                                if warmth > 0.7:
                                    emotion_guidance.append("Respond with warmth and care.")
                                if energy > 0.6:
                                    emotion_guidance.append("Show engaged, active energy.")
                                elif energy < 0.4:
                                    emotion_guidance.append("Maintain a calm, gentle presence.")
                                if directness > 0.7:
                                    emotion_guidance.append("Be direct and clear.")
                                elif directness < 0.4:
                                    emotion_guidance.append("Be gentle and indirect.")
                                
                                if emotion_guidance:
                                    prompt_parts.append("\n".join(emotion_guidance))
                                    self.logger.debug(f"🎭 Added emotional conditioning: {label.get('primary', 'calm')}")
                    except RuntimeError:
                        # No event loop
                        emotional_state = asyncio.run(emotion_engine.get_current_state())
                        if emotional_state:
                            style = emotional_state.get("style", {})
                            label = emotional_state.get("label", {})
                            
                            emotion_guidance = []
                            emotion_guidance.append(f"Current emotional tone: {label.get('primary', 'calm')}")
                            
                            warmth = style.get("warmth", 0.6)
                            energy = style.get("energy", 0.5)
                            directness = style.get("directness", 0.5)
                            
                            if warmth > 0.7:
                                emotion_guidance.append("Respond with warmth and care.")
                            if energy > 0.6:
                                emotion_guidance.append("Show engaged, active energy.")
                            elif energy < 0.4:
                                emotion_guidance.append("Maintain a calm, gentle presence.")
                            if directness > 0.7:
                                emotion_guidance.append("Be direct and clear.")
                            elif directness < 0.4:
                                emotion_guidance.append("Be gentle and indirect.")
                            
                            if emotion_guidance:
                                prompt_parts.append("\n".join(emotion_guidance))
                                self.logger.debug(f"🎭 Added emotional conditioning: {label.get('primary', 'calm')}")
            except Exception as e:
                self.logger.warning(f"🎭 Failed to add emotional conditioning: {e}")
        
        # Add memory context if available
        if memory_context:
            memory_data = memory_context.get("memory_context", {})
            user_facts = memory_data.get("user_facts", [])
            recent_context = memory_data.get("recent_context", [])
            kg_data = memory_context.get("knowledge_graph", {})
            
            self.logger.debug(f"Building system prompt: {len(user_facts)} facts, {len(recent_context)} messages")
            
            # Add knowledge graph context (relationships only)
            if kg_data:
                entities = kg_data.get("entities", [])
                relationships = kg_data.get("relationships", [])
                
                # Add relationships as facts (entities are filtered at extraction time)
                if relationships:
                    kg_parts = []
                    rel_lines = []
                    for r in relationships:
                        # Use actual entity text, not type names
                        source = r.get('source', '')
                        target = r.get('target', '')
                        relation = r.get('relation', '')
                        # Filter out placeholders / incomplete relations that add noise to the prompt
                        if not source or not target or not relation:
                            continue
                        if source.strip() == "?" or target.strip() == "?" or relation.strip() == "?":
                            continue
                        rel_lines.append(f"- {source} {relation} {target}")
                    
                    if rel_lines:
                        kg_parts.append(f"Known facts:\n" + "\n".join(rel_lines))
                        prompt_parts.append("\n".join(kg_parts))
                        self.logger.debug(f"Added {len(relationships)} KG relationships to system prompt")
            
            # Add user facts if available (conversation history goes in messages array, not system prompt)
            if user_facts:
                facts_text = "\n".join([f"- {fact.get('content', '')}" for fact in user_facts[-5:]])
                prompt_parts.append(f"Additional facts:\n{facts_text}")
                self.logger.debug(f"Added {len(user_facts)} user facts to system prompt")
            else:
                # NOTE: Empty system prompt is OK - conversation history is in messages array (vLLM standard)
                self.logger.debug(f"No user facts - system prompt empty (history in messages array)")
        else:
            self.logger.warning(f"⚠️ [PROMPT_BUILD] NO memory_context provided")
        
        # Only return a prompt if we have contextual information to add
        # Otherwise return empty string to let Modelfile's SYSTEM be the only system instruction
        prompt = "\n\n".join(prompt_parts) if prompt_parts else ""
        
        if prompt:
            self.logger.debug(f"Final system prompt: {len(prompt)} chars")
        else:
            self.logger.debug(f"No system prompt - using Modelfile's SYSTEM instruction only")
        
        return prompt
    
    async def _handle_llm_response(self, response) -> None:
        """Handle LLM completion response and deliver final response"""
        try:
            self.logger.debug(f"LLM response received, processing...")
            
            # Unpack the LLM response from AicoMessage envelope
            from aico.proto.aico_modelservice_pb2 import CompletionsResponse
            
            # Debug the response structure
            self.logger.debug(f"Received LLM response structure: {type(response)}")
            
            # Unpack the CompletionsResponse from the AicoMessage envelope
            completions_response = CompletionsResponse()
            response.any_payload.Unpack(completions_response)
            
            # Extract correlation ID from response for proper matching
            correlation_id = None
            try:
                # Get correlation ID from envelope metadata
                correlation_id = response.metadata.attributes.get("correlation_id")
                self.logger.debug(f"Received LLM response with correlation_id: {correlation_id}")
            except Exception as e:
                self.logger.error(f"Failed to extract correlation_id from LLM response: {e}")
                return
            
            # Find matching request using correlation ID
            # Note: With request-specific response topics, we should ALWAYS find a match
            # If not found, it indicates a bug in subscription/cleanup logic
            if correlation_id and correlation_id in self.pending_responses:
                self.logger.debug(f"Processing response for correlation_id: {correlation_id}")
                request_id = correlation_id
                pending_data = self.pending_responses[request_id]
                user_context = pending_data["user_context"]
                
                # Extract response text from the completion response
                response_text = "I'm here to help!"  # Default fallback
                
                if completions_response.success and completions_response.result:
                    # Get the message content from the result
                    if completions_response.result.message and completions_response.result.message.content:
                        response_text = completions_response.result.message.content
                elif completions_response.error:
                    self.logger.error(f"LLM completion error: {completions_response.error}")
                    response_text = "I apologize, but I encountered an error generating a response."
                
                # Store response text for direct API access
                if request_id in self.pending_responses:
                    self.pending_responses[request_id]["response_text"] = response_text
                    self.pending_responses[request_id]["response_ready"] = True
                
                # Store AI response in semantic memory
                user_message = self.pending_responses[request_id]["user_message"]
                user_context = self.pending_responses[request_id].get("user_context")
                memory_manager = ai_registry.get("memory")
                if memory_manager:
                    try:
                        language = user_context.conversation_language if user_context else "en"
                        await memory_manager.store_message(
                            user_message.user_id, 
                            user_message.message.conversation_id, 
                            response_text, 
                            "assistant",
                            language=language
                        )
                        self.logger.debug(f"AI response stored in semantic memory")
                    except Exception as e:
                        self.logger.error(f"Failed to store AI response in memory: {e}")
                
                self.logger.debug(f"🔍 [ENGINE_FLOW] ✅ Response processing complete for correlation_id: {correlation_id}")
                
                # Clean up (but only if not being used by direct API)
                if request_id in self.pending_responses and not self.pending_responses[request_id].get("direct_api_call"):
                    await self._cleanup_request(request_id)
            else:
                # This should NEVER happen with request-specific topics
                # If it does, it indicates a bug in subscription/cleanup logic
                self.logger.error(f"BUG: Received response for unknown correlation_id: {correlation_id} (subscription leak detected)")
                    
        except Exception as e:
            self.logger.error(f"Error handling LLM response: {e}")

    # Embodiment system removed - focusing on core conversation functionality
    async def _response_timeout_handler(self, request_id: str) -> None:
        """Handle response timeout for a specific request"""
        try:
            self.logger.debug(f"🔍 [ENGINE_TIMEOUT] Starting timeout handler for request: {request_id}")
            await asyncio.sleep(self.response_timeout)
            
            # Check if request is still pending after timeout
            if request_id in self.pending_responses:
                self.logger.error(f"🔍 [ENGINE_TIMEOUT] ❌ REQUEST TIMED OUT after {self.response_timeout}s: {request_id}")
                await self._cleanup_request(request_id)
            else:
                self.logger.debug(f"🔍 [ENGINE_TIMEOUT] ✅ Request completed before timeout: {request_id}")
                
        except Exception as e:
            self.logger.error(f"Error in timeout handler for {request_id}: {e}")
    
    async def _cleanup_request(self, request_id: str) -> None:
        """Clean up completed request"""
        if request_id in self.pending_responses:
            # Unsubscribe from request-specific response topic
            response_topic = self.pending_responses[request_id].get("response_topic")
            if response_topic:
                try:
                    await self.bus_client.unsubscribe(response_topic)
                    self.logger.debug(f"Unsubscribed from {response_topic}")
                except Exception as e:
                    self.logger.warning(f"Failed to unsubscribe from {response_topic}: {e}")
            
            del self.pending_responses[request_id]
            self.logger.debug(f"Cleaned up request {request_id}")
    
    # ============================================================================
    # PHASE 3: BEHAVIORAL LEARNING INTEGRATION
    # ============================================================================
    
    async def _select_skill(self, user_context: UserContext, user_message: ConversationMessage, memory_context: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Select skill for current interaction using Thompson Sampling.
        
        Args:
            user_context: User context
            user_message: Current user message
            memory_context: Memory context
            
        Returns:
            skill_id if selected, None otherwise
        """
        try:
            # Check if behavioral learning is enabled
            memory_manager = ai_registry.get("memory")
            
            self.logger.debug(f"Starting skill selection for user {user_context.user_id}")
            
            if not memory_manager:
                self.logger.warning("No memory manager found in registry")
                return None
            
            if not hasattr(memory_manager, '_behavioral_enabled'):
                self.logger.warning("Memory manager missing _behavioral_enabled attribute")
                return None
                
            if not memory_manager._behavioral_enabled:
                self.logger.debug("Behavioral learning disabled")
                return None
            
            # Get Thompson Sampling selector
            if not hasattr(memory_manager, '_thompson_sampling'):
                self.logger.warning("Memory manager missing _thompson_sampling attribute")
                return None
                
            if not memory_manager._thompson_sampling:
                self.logger.warning("Thompson sampling selector is None")
                return None
            
            thompson_sampling = memory_manager._thompson_sampling
            skill_store = memory_manager._skill_store
            
            # Get available skills
            candidate_skills = await skill_store.list_skills(skill_type=None)
            
            if not candidate_skills:
                self.logger.debug("No skills available for selection")
                return None
            
            self.logger.debug(f"Found {len(candidate_skills)} candidate skills")
            
            # Build context for selection (simplified - could be enhanced with intent detection)
            context = {
                "message_text": user_message.message.text if user_message else "",
                "time_of_day": "any"
            }
            
            # Select skill using Thompson Sampling
            selected_skill_id = await thompson_sampling.select_skill(
                user_id=user_context.user_id,
                candidate_skills=[s.skill_id for s in candidate_skills],
                context=context
            )
            
            if selected_skill_id:
                self.logger.debug(f"Selected skill: {selected_skill_id}")
            else:
                self.logger.debug("Thompson Sampling returned None")
            
            return selected_skill_id
            
        except Exception as e:
            self.logger.error(f"Failed to select skill: {e}")
            import traceback
            print(f"🎯 [SKILL] Traceback: {traceback.format_exc()}")
            return None
    
    async def _log_trajectory(self, user_context: UserContext, user_message: ConversationMessage, ai_response: str, selected_skill_id: Optional[str], agency_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log conversation trajectory for behavioral learning.
        
        Args:
            user_context: User context
            user_message: User message
            ai_response: AI response text
            selected_skill_id: ID of skill that was applied
            agency_data: Agency plugin response data (intentions, ethics decisions, etc.)
        """
        try:
            # Check if behavioral learning is enabled
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                return
            
            if not hasattr(memory_manager, '_behavioral_enabled'):
                return
                
            if not memory_manager._behavioral_enabled:
                return
            
            # Generate trajectory ID
            import uuid
            import json
            trajectory_id = str(uuid.uuid4())
            conversation_id = user_message.message.conversation_id
            
            # Use UnitOfWork to persist trajectory via repository
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            try:
                session_factory = await get_session_factory()
                async with UnitOfWork(session_factory) as uow:
                    # Get turn number by counting existing trajectories
                    turn_number = await uow.ams_trajectories.count(
                        filters={"user_id": user_context.user_id, "conversation_id": conversation_id}
                    ) + 1
                    
                    # Extract agency context for logging
                    agency_context_json = None
                    if agency_data and agency_data.get("success"):
                        agency_context = {
                            "intention_set": agency_data.get("data", {}).get("intention_set"),
                            "active_goals": agency_data.get("data", {}).get("active_goals"),
                            "ethics_decisions": agency_data.get("data", {}).get("ethics_decisions"),
                            "confidence": agency_data.get("confidence"),
                            "processing_time_ms": agency_data.get("processing_time_ms")
                        }
                        # Remove None values
                        agency_context = {k: v for k, v in agency_context.items() if v is not None}
                        if agency_context:
                            agency_context_json = json.dumps(agency_context)
                            
                            # Log agency decisions as structured log entry
                            self.logger.debug(
                                f"🎯 [AGENCY] Turn {turn_number} - Agency context",
                                extra={
                                    "conversation_id": conversation_id,
                                    "turn_number": turn_number,
                                    "agency_context": agency_context,
                                    "subsystem": "agency"
                                }
                            )
                    
                    # Create trajectory via repository
                    from aico.data.ams.models import Trajectory
                    trajectory = Trajectory(
                        trajectory_id=trajectory_id,
                        user_id=user_context.user_id,
                        conversation_id=conversation_id,
                        turn_number=turn_number,
                        user_input=user_message.message.text,
                        selected_skill_id=selected_skill_id,
                        ai_response=ai_response,
                        message_id=user_message.message_id,
                        agency_context=agency_context_json,
                        timestamp=datetime.now(UTC)
                    )
                    
                    await uow.ams_trajectories.create(trajectory)
                    await uow.commit()
                    
                    self.logger.debug(f"📝 [TRAJECTORY] Logged turn {turn_number} for conversation {conversation_id}")
            except Exception as db_error:
                self.logger.error(f"📝 [TRAJECTORY] Database error logging trajectory: {db_error}")
                raise
            
        except Exception as e:
            self.logger.error(f"📝 [TRAJECTORY] Failed to log trajectory: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for conversation engine"""
        return {
            "status": "healthy" if self.bus_client else "disconnected",
            "active_users": len(self.user_contexts),
            "active_threads": len(self.active_threads),
            "features_enabled": {
                "emotion": self.enable_emotion_integration,
                "personality": self.enable_personality_integration,
                "memory": self.enable_memory_integration,
                "embodiment": self.enable_embodiment,
                "agency": self.enable_agency
            }
        }
    
    async def stop(self) -> None:
        """Stop service operations - integrates with AICO service container shutdown"""
        self.logger.warning(f"🔄 CONVERSATION ENGINE: Stopping service and AI components")
        start_time = time.time()
        
        try:
            # Signal global shutdown to semantic memory components
            from aico.ai.memory.request_queue import _set_global_shutdown
            _set_global_shutdown()
            
            # Shutdown memory manager (includes semantic memory with thread pools)
            memory_manager = ai_registry.get("memory")
            if memory_manager and hasattr(memory_manager, 'shutdown'):
                await memory_manager.shutdown(timeout=20.0)  # Leave time for other services
                self.logger.debug("Memory manager shutdown completed")
            
            # Shutdown message bus client
            if self.bus_client:
                # MessageBusClient doesn't have async shutdown, but we should close it
                # TODO: Add proper shutdown to MessageBusClient if needed
                self.bus_client = None
            
            # Clear conversation state
            self.user_contexts.clear()
            self.pending_responses.clear()
            
            total_time = time.time() - start_time
            self.logger.warning(f"✅ CONVERSATION ENGINE: Service stopped in {total_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error during conversation engine stop: {e}")
    
    # ============================================================================
    # GOAL EXTRACTION (Phase 6 - Conversation Integration)
    # ============================================================================
    
    async def _extract_user_goal_async(
        self,
        user_id: str,
        message_id: str,
        message_text: str,
        conversation_id: str
    ) -> None:
        """Extract user goals from conversation message (async, non-blocking).
        
        This runs in the background after the conversation response is sent,
        using XLM-RoBERTa for fast intent classification and LLM for goal extraction.
        
        Args:
            user_id: User ID
            message_id: Message ID for provenance
            message_text: User's message text
            conversation_id: Conversation ID for context
        """
        try:
            print(f"🎯 [GOAL_EXTRACTION] Starting async extraction for user {user_id[:8]}")
            print(f"🎯 [GOAL_EXTRACTION] Message: '{message_text[:100]}...'")
            self.logger.info(f"[GOAL_EXTRACTION] Starting async extraction for message: {message_text[:50]}...")
            
            # Get goal extractor with event store for metrics tracking
            from aico.ai.agency import UserGoalExtractor
            from aico.ai.processors import ai_registry
            print(f"🎯 [GOAL_EXTRACTION] Getting goal extractor instance...")
            
            # Get agency engine to access event store and database connection
            agency_engine = ai_registry.get("agency")
            event_store = getattr(agency_engine, "event_store", None) if agency_engine else None
            db_connection = self.container.get_service("database") if hasattr(self, 'container') else None
            
            extractor = UserGoalExtractor(event_store=event_store, db_connection=db_connection)
            print(f"🎯 [GOAL_EXTRACTION] ✅ Goal extractor ready (event_store={'enabled' if event_store else 'disabled'})")
            
            # Extract goal (XLM-RoBERTa + LLM, ~500ms total)
            print(f"🎯 [GOAL_EXTRACTION] Calling extractor.extract_goal_from_message()...")
            perceptual_event = await extractor.extract_goal_from_message(
                user_id=user_id,
                message_id=message_id,
                message_text=message_text,
                conversation_id=conversation_id,
                conversation_context=None  # TODO: Get recent conversation context
            )
            
            if not perceptual_event:
                print(f"🎯 [GOAL_EXTRACTION] ❌ No goal detected in message (intent not goal-forming or low confidence)")
                self.logger.info("[GOAL_EXTRACTION] No goal detected in message")
                return
            
            print(f"🎯 [GOAL_EXTRACTION] ✅ Goal detected!")
            print(f"🎯 [GOAL_EXTRACTION]   Title: '{perceptual_event.candidate_goal_summaries[0]}'")
            print(f"🎯 [GOAL_EXTRACTION]   Confidence: {perceptual_event.confidence_score:.2f}")
            # Handle both enum and string values for horizon
            horizon_value = perceptual_event.candidate_goal_horizon.value if hasattr(perceptual_event.candidate_goal_horizon, 'value') else perceptual_event.candidate_goal_horizon if perceptual_event.candidate_goal_horizon else 'unknown'
            print(f"🎯 [GOAL_EXTRACTION]   Horizon: {horizon_value}")
            print(f"🎯 [GOAL_EXTRACTION]   Urgency: {perceptual_event.urgency_score:.2f}")
            self.logger.info(
                f"[GOAL_EXTRACTION] Goal detected: '{perceptual_event.candidate_goal_summaries[0]}' "
                f"(confidence={perceptual_event.confidence_score:.2f})"
            )
            
            # Get agency engine from registry
            from aico.ai.processors import ai_registry
            print(f"🎯 [GOAL_EXTRACTION] Getting agency engine from registry...")
            agency_engine = ai_registry.get("agency")
            
            if not agency_engine:
                print(f"🎯 [GOAL_EXTRACTION] ❌ Agency engine not available in registry")
                self.logger.warning("[GOAL_EXTRACTION] Agency engine not available in registry")
                return
            print(f"🎯 [GOAL_EXTRACTION] ✅ Agency engine ready")
            
            # Process perceptual event to create goal
            print(f"🎯 [GOAL_EXTRACTION] Processing perceptual event to create goal...")
            goal = await agency_engine.process_perceptual_event(perceptual_event)
            
            if goal:
                print(f"🎯 [GOAL_EXTRACTION] ✅✅✅ SUCCESS! Created user goal:")
                print(f"🎯 [GOAL_EXTRACTION]   Goal ID: {goal.goal_id}")
                print(f"🎯 [GOAL_EXTRACTION]   Title: '{goal.title}'")
                print(f"🎯 [GOAL_EXTRACTION]   Origin: {goal.origin.value}")
                print(f"🎯 [GOAL_EXTRACTION]   Status: {goal.status.value}")
                print(f"🎯 [GOAL_EXTRACTION]   Priority: {goal.priority.value}")
                self.logger.info(
                    f"[GOAL_EXTRACTION] ✅ Created user goal: '{goal.title}' "
                    f"(id={goal.goal_id}, origin={goal.origin.value})"
                )
                
                # Frontend will pick up via regular polling of agency endpoints
                # No WebSocket needed - polling already implemented
                
            else:
                print(f"🎯 [GOAL_EXTRACTION] ❌ Failed to create goal from perceptual event")
                self.logger.warning("[GOAL_EXTRACTION] Failed to create goal from perceptual event")
                
        except Exception as e:
            # Don't fail conversation flow if goal extraction fails
            print(f"🎯 [GOAL_EXTRACTION] ❌❌❌ EXCEPTION: {e}")
            import traceback
            print(f"🎯 [GOAL_EXTRACTION] Traceback: {traceback.format_exc()}")
            self.logger.error(f"[GOAL_EXTRACTION] Async goal extraction failed: {e}", exc_info=True)
    

