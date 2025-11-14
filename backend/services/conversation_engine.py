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
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_core_envelope_pb2 import AicoMessage
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from aico.proto.aico_modelservice_pb2 import CompletionsResponse, CompletionsRequest, ConversationMessage as ModelConversationMessage
from aico.ai import ProcessingContext, ai_registry
from backend.core.service_container import BaseService
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
        
        # AI Processing uses global registry
        # Processors registered via: ai_registry.register("emotion", processor_instance)
        
        # User context management (simplified)
        self.user_contexts: Dict[str, UserContext] = {}
        
        # AI processing coordination
        self.pending_responses: Dict[str, Dict[str, Any]] = {}  # request_id -> response data

        # Configuration - access via core.conversation path (like other services)
        engine_config = self.container.config.get("core.conversation", {})
        features_config = engine_config.get("features", {})
        
        # Feature flags for gradual implementation
        self.enable_emotion_integration = features_config.get("enable_emotion_integration", False)
        self.enable_personality_integration = features_config.get("enable_personality_integration", False)
        self.enable_memory_integration = features_config.get("enable_memory_integration", True)  # RE-ENABLED - was disabled for test
        self.enable_embodiment = features_config.get("enable_embodiment", False)
        self.enable_agency = features_config.get("enable_agency", False)
        
        
        self.max_context_messages = engine_config.get("max_context_messages", 10)
        self.response_timeout = engine_config.get("response_timeout_seconds", 15.0)
        self.default_response_mode = ResponseMode(engine_config.get("default_response_mode", "text_only"))
        
        # Load conversation model name from configuration
        # NO FALLBACK - fail loudly if model configuration is missing or invalid
        modelservice_config = self.container.config.get("core.modelservice.ollama")
        if not modelservice_config:
            raise ValueError("CRITICAL: Missing core.modelservice.ollama configuration")
        
        default_models = modelservice_config.get("default_models")
        if not default_models:
            raise ValueError("CRITICAL: Missing core.modelservice.ollama.default_models configuration")
        
        conversation_model_config = default_models.get("conversation")
        if not conversation_model_config:
            raise ValueError("CRITICAL: Missing core.modelservice.ollama.default_models.conversation configuration")
        
        self.model_name = conversation_model_config.get("name")
        if not self.model_name:
            raise ValueError("CRITICAL: Missing core.modelservice.ollama.default_models.conversation.name - model name must be explicitly configured")
        
        self.logger.info(f"Conversation engine using model: {self.model_name}")
        

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
            print("💬 [CONVERSATION_ENGINE] 🚀 STARTING CONVERSATION ENGINE...")
            self.logger.info("💬 [CONVERSATION_ENGINE] 🚀 STARTING CONVERSATION ENGINE...")
            
            # Initialize message bus client
            self.bus_client = MessageBusClient("conversation_engine")
            await self.bus_client.connect()
            print("💬 [CONVERSATION_ENGINE] ✅ Message bus client connected")
            self.logger.info("💬 [CONVERSATION_ENGINE] ✅ Message bus client connected")
            
            # AI processors will be registered here when implemented
            # No initialization needed for empty registry
            
            # Subscribe to conversation topics
            await self._setup_subscriptions()
            print("💬 [CONVERSATION_ENGINE] ✅ Subscriptions established")
            self.logger.info("💬 [CONVERSATION_ENGINE] ✅ Subscriptions established")
            
            print("💬 [CONVERSATION_ENGINE] 🎉 CONVERSATION ENGINE STARTED SUCCESSFULLY!")
            self.logger.info("💬 [CONVERSATION_ENGINE] 🎉 CONVERSATION ENGINE STARTED SUCCESSFULLY!")
            
        except Exception as e:
            self.logger.error(f"💬 [CONVERSATION_ENGINE] ❌ FAILED TO START: {e}")
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
        await self.bus_client.subscribe(
            AICOTopics.CONVERSATION_USER_INPUT,
            self._handle_user_input
        )
        
        # Subscribe to LLM responses (always enabled)
        await self.bus_client.subscribe(
            AICOTopics.MODELSERVICE_CHAT_RESPONSE,
            self._handle_llm_response
        )
        
        # Optional component subscriptions
        if self.enable_emotion_integration:
            await self.bus_client.subscribe(
                AICOTopics.EMOTION_ANALYSIS_RESPONSE,
                self._handle_emotion_response
            )
        
        if self.enable_personality_integration:
            await self.bus_client.subscribe(
                AICOTopics.PERSONALITY_EXPRESSION_RESPONSE,
                self._handle_personality_response
            )
        
        # V2: Direct memory integration - no message bus subscriptions needed
        
        # Future: Agency proactive triggers
        if self.enable_agency:
            # await self.bus_client.subscribe(AICOTopics.AGENCY_PROACTIVE_TRIGGER, ...)
            pass
        
        self.logger.info("Message bus subscriptions established")
    
    # ============================================================================
    # CORE MESSAGE HANDLERS
    # ============================================================================
    
    async def _handle_user_input(self, message) -> None:
        """Handle incoming user input message"""
        try:
            import time
            timestamp = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 🔥 RECEIVED USER INPUT MESSAGE! [{timestamp:.6f}]")
            print(f"💬 [CONVERSATION_ENGINE] Message type: {type(message)}")
            self.logger.info(f"💬 [CONVERSATION_ENGINE] 🔥 RECEIVED USER INPUT MESSAGE!")
            self.logger.info(f"💬 [CONVERSATION_ENGINE] Message type: {type(message)}")
            
            # The message is an AicoMessage envelope, need to unpack the ConversationMessage
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            
            # Unpack the ConversationMessage from the AicoMessage envelope
            conv_message = ConversationMessage()
            message.any_payload.Unpack(conv_message)
            print(f"💬 [CONVERSATION_ENGINE] ✅ Unpacked ConversationMessage successfully")
            
            # Extract user information from the message
            # Use user_id field (actual user UUID), not source (which is just "conversation_api")
            user_id = conv_message.user_id if conv_message.user_id else conv_message.source
            conversation_id = conv_message.message.conversation_id
            print(f"💬 [CONVERSATION_ENGINE] 📋 User ID: {user_id}, Conversation ID: {conversation_id}")
            
            self.logger.info(f"[DEBUG] ConversationEngine: Received user input.", extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "message_type": conv_message.message.type
            })
            
            # Get user context (simplified)
            user_context = await self._get_or_create_user_context(user_id)
            
            
            # Generate response using semantic memory approach
            print(f"💬 [CONVERSATION_ENGINE] 🎯 Generating response...")
            await self._generate_response(user_context, conv_message)
            
        except Exception as e:
            self.logger.error(f"Error handling user input: {e}", extra={
                "error": str(e)
            })
    
    # ============================================================================
    # USER & THREAD MANAGEMENT
    # ============================================================================
    
    async def _get_or_create_user_context(self, user_id: str) -> UserContext:
        """Get or create user context for authenticated user"""
        print(f"🔍 [USER_CONTEXT] _get_or_create_user_context called for user_id: {user_id}")
        if user_id not in self.user_contexts:
            print(f"🔍 [USER_CONTEXT] User not in cache, loading from database...")
            # Load user data from database
            user_profile = None
            try:
                # Access user_service directly from service container (not via dependency injection)
                if hasattr(self, 'container') and self.container:
                    user_service = self.container.get_service("user_service")
                    print(f"🔍 [USER_CONTEXT] Got user_service from container: {user_service}")
                    if user_service:
                        print(f"🔍 [USER_CONTEXT] Calling user_service.get_user({user_id})...")
                        user_profile = await user_service.get_user(user_id)
                        print(f"🔍 [USER_CONTEXT] Got user_profile: {user_profile}")
                else:
                    print(f"🔍 [USER_CONTEXT] ⚠️  No service_container available")
            except Exception as e:
                print(f"🔍 [USER_CONTEXT] ❌ Exception loading user profile: {e}")
                import traceback
                print(f"🔍 [USER_CONTEXT] Traceback: {traceback.format_exc()}")
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
                    last_seen=datetime.utcnow()
                )
                self.logger.info(f"Loaded user context from database", extra={
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
                    last_seen=datetime.utcnow()
                )
                self.logger.warning(f"Created placeholder user context (database load failed)", extra={
                    "user_id": user_id
                })
        else:
            # Update last seen
            self.user_contexts[user_id].last_seen = datetime.utcnow()
        
        return self.user_contexts[user_id]
    
# Thread management removed - using semantic memory for conversation continuity
    
    # ============================================================================
    # MESSAGE ANALYSIS & RESPONSE GENERATION
    # ============================================================================
    
    # Message analysis removed - semantic memory handles context automatically
    
    async def _generate_response(self, user_context: UserContext, user_message: ConversationMessage) -> None:
        """Generate and deliver response based on enabled features"""
        try:
            # Use the message_id from the API Gateway as request_id for proper correlation
            request_id = user_message.message_id if user_message.message_id else str(uuid.uuid4())
            print(f"💬 [CONVERSATION_ENGINE] 🎯 Request ID: {request_id} (from API Gateway: {user_message.message_id})")
            
            # Initialize response tracking (simplified)
            print(f"💬 [CONVERSATION_ENGINE] 📝 Creating pending request: {request_id}")
            self.pending_responses[request_id] = {
                "user_context": user_context,
                "user_message": user_message,
                "components_needed": [],
                "components_ready": {},
                "started_at": datetime.utcnow()
            }
            print(f"💬 [CONVERSATION_ENGINE] 📋 Total pending requests: {len(self.pending_responses)}")
            
            # Determine what components we need
            components_needed = []
            print(f"💬 [CONVERSATION_ENGINE] 🔧 Checking enabled features...")
            print(f"💬 [CONVERSATION_ENGINE] 🧠 Memory integration enabled: {self.enable_memory_integration}")
            
            # Get memory context if enabled
            memory_context = None
            if self.enable_memory_integration:
                print(f"💬 [CONVERSATION_ENGINE] 🧠 Calling _get_memory_context()...")
                try:
                    memory_context = await self._get_memory_context(request_id, user_context, user_message)
                    if memory_context is None:
                        print(f"💬 [CONVERSATION_ENGINE] ❌ _get_memory_context() returned None!")
                        self.logger.error(f"🚨 [CONTEXT_TRACE] _get_memory_context() returned None - context will NOT be passed to LLM!")
                    else:
                        print(f"💬 [CONVERSATION_ENGINE] ✅ Got memory context!")
                        self.logger.info(f"🧠 [CONTEXT_TRACE] ✅ Got memory_context from _get_memory_context()")
                except Exception as e:
                    print(f"💬 [CONVERSATION_ENGINE] ❌ EXCEPTION in _get_memory_context(): {e}")
                    self.logger.error(f"🚨 [CONTEXT_TRACE] EXCEPTION calling _get_memory_context(): {e}")
                    import traceback
                    self.logger.error(f"🚨 [CONTEXT_TRACE] Traceback:\n{traceback.format_exc()}")
                    memory_context = None
            else:
                print(f"💬 [CONVERSATION_ENGINE] ⚠️  Memory integration DISABLED")
                self.logger.warning(f"🚨 [CONTEXT_TRACE] Memory integration DISABLED - no context will be retrieved")
            
            # Generate LLM response with memory context
            await self._generate_llm_response(request_id, user_context, user_message, memory_context)
            
            self.pending_responses[request_id]["components_needed"] = components_needed
            print(f"💬 [CONVERSATION_ENGINE] 📝 Components needed: {components_needed}")
            
            # Note: LLM response already generated above, no need for fallback logic
            
            # Set timeout - normal responses should be 1-6 seconds
            self.logger.info(f"🔍 [ENGINE_FLOW] Request {request_id} created, starting timeout handler")
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
            self.logger.info(f"🧠 [CONTEXT_TRACE] Starting context retrieval for request {request_id}")
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ❌ Memory manager NOT registered in ai_registry")
                return None
            
            self.logger.info(f"🧠 [CONTEXT_TRACE] ✅ Memory manager found")
            
            user_id = user_context.user_id
            conversation_id = message.message.conversation_id
            message_text = message.message.text
            
            self.logger.info(f"🧠 [CONTEXT_TRACE] Calling memory_manager.assemble_context(user_id={user_id}, conversation_id={conversation_id})")
            
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
                
                self.logger.info(f"🧠 [CONTEXT_TRACE] ✅ Context retrieved:")
                self.logger.info(f"🧠 [CONTEXT_TRACE]   - user_facts: {len(user_facts)} items")
                self.logger.info(f"🧠 [CONTEXT_TRACE]   - recent_context: {len(recent_context)} messages")
                self.logger.info(f"🧠 [CONTEXT_TRACE]   - total_items: {metadata.get('total_items', 0)}")
                self.logger.info(f"🧠 [CONTEXT_TRACE]   - assembly_time: {metadata.get('assembly_time_ms', 0):.2f}ms")
                
                if user_facts:
                    self.logger.info(f"🧠 [CONTEXT_TRACE] Sample user_facts: {user_facts[0].get('content', 'N/A')[:100]}...")
                if recent_context:
                    self.logger.info(f"🧠 [CONTEXT_TRACE] Sample recent_context: {recent_context[0].get('content', 'N/A')[:100]}...")
            else:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ⚠️  Context is None or empty")
            
            # Store user message for future context
            print(f"💬 [CONVERSATION_ENGINE] 💾 Storing user message (len: {len(message_text)})...")
            try:
                await memory_manager.store_message(user_id, conversation_id, message_text, "user")
                print(f"💬 [CONVERSATION_ENGINE] ✅ User message stored successfully!")
                self.logger.debug(f"🧠 [CONTEXT_TRACE] User message stored for future context")
            except Exception as e:
                print(f"💬 [CONVERSATION_ENGINE] ❌ Failed to store user message: {e}")
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
            
            self.logger.info(f"🔍 [MEMORY_BACKGROUND] Starting background message storage for {request_id}")
            
            # Store user message for future context (let it take as long as needed - it's background)
            try:
                await memory_manager.store_message(user_id, conversation_id, message_text, "user")
                total_duration = time.time() - start_time
                self.logger.info(f"🔍 [MEMORY_BACKGROUND] ✅ User message stored in {total_duration:.3f}s for {request_id}")
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
            import time
            timestamp = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 🔍 Checking response completion for {request_id} [{timestamp:.6f}]")
            
            if request_id not in self.pending_responses:
                print(f"💬 [CONVERSATION_ENGINE] ❌ Request {request_id} not found in pending_responses")
                return
            
            pending_data = self.pending_responses[request_id]
            needed = set(pending_data["components_needed"])
            ready = set(pending_data["components_ready"].keys())
            
            import time
            timestamp = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 📊 Components needed: {needed}, ready: {ready} [{timestamp:.6f}]")
            
            if needed.issubset(ready):
                import time
                timestamp = time.time()
                print(f"💬 [CONVERSATION_ENGINE] ✅ All components ready! Generating LLM response... [{timestamp:.6f}]")
                # All components ready, generate LLM response
                user_context = pending_data["user_context"]
                user_message = pending_data["user_message"]
                context = pending_data["components_ready"]
                
                await self._generate_llm_response(request_id, user_context, user_message, context)
            else:
                print(f"💬 [CONVERSATION_ENGINE] ⏳ Still waiting for components: {needed - ready}")
                
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
                self.logger.info(f"🎯 [SKILL] Selected skill: {selected_skill_id}")
            
            # Build system prompt with memory context and skill template
            print(f"🔍 [MEMORY_DEBUG] memory_context type: {type(memory_context)}")
            print(f"🔍 [MEMORY_DEBUG] memory_context keys: {list(memory_context.keys()) if memory_context else 'None'}")
            if memory_context is None:
                self.logger.warning(f"No memory context provided for request {request_id}")
            else:
                memory_data = memory_context.get("memory_context", {})
                print(f"🔍 [MEMORY_DEBUG] memory_data keys: {list(memory_data.keys())}")
                user_facts = memory_data.get("user_facts", [])
                recent_context = memory_data.get("recent_context", [])
                print(f"🔍 [MEMORY_DEBUG] recent_context length: {len(recent_context)}")
                print(f"🔍 [MEMORY_DEBUG] recent_context sample: {recent_context[:2] if recent_context else 'empty'}")
                self.logger.info(f"Context: {len(user_facts)} facts, {len(recent_context)} messages")
            
            system_prompt = self._build_system_prompt(user_context, memory_context, selected_skill_id)
            if system_prompt:
                self.logger.debug(f"System prompt: {len(system_prompt)} chars")
            
            # Build messages for LLM
            # IMPORTANT: Only add system message if we have contextual information to provide
            # The Modelfile's SYSTEM instruction should be the primary character definition
            messages = []
            if system_prompt and system_prompt.strip():
                messages.append(ModelConversationMessage(role="system", content=system_prompt))
            
            # Add conversation history as actual messages (not just in system prompt)
            history_message_count = 0
            if memory_context:
                memory_data = memory_context.get("memory_context", {})
                recent_context = memory_data.get("recent_context", [])
                
                # CRITICAL: recent_context is in REVERSE chronological order (newest first)
                # We need to reverse it to get chronological order (oldest first) for LLM
                # Take last 5 messages and reverse them
                history_messages = list(reversed(recent_context[-5:]))
                
                self.logger.info(f"🧠 [CONTEXT_TRACE] Processing {len(history_messages)} history messages for LLM")
                for msg in history_messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '').strip()
                    if content:
                        messages.append(ModelConversationMessage(role=role, content=content))
                        history_message_count += 1
                        self.logger.info(f"🧠 [CONTEXT_TRACE] ✅ Added {role} message to LLM: {content[:80]}...")
                
                # CRITICAL VALIDATION: Warn if no conversation history was added
                if history_message_count == 0 and len(recent_context) > 0:
                    self.logger.error(f"🚨 [CONTEXT_ERROR] recent_context has {len(recent_context)} items but ZERO messages added to LLM!")
                    self.logger.error(f"🚨 [CONTEXT_ERROR] Sample item keys: {list(recent_context[0].keys()) if recent_context else 'N/A'}")
                else:
                    self.logger.info(f"🧠 [CONTEXT_TRACE] ✅ Added {history_message_count} history messages to LLM context")
            else:
                self.logger.warning(f"🧠 [CONTEXT_TRACE] ⚠️  No memory_context provided - LLM has no conversation history")
            
            # Add current user message
            current_content = user_message.message.text.strip()
            if current_content:
                messages.append(ModelConversationMessage(role="user", content=current_content))
                self.logger.debug(f"🔍 [PROMPT_DEBUG] Added current user message: {current_content[:50]}...")
            
            # Create and publish LLM request
            # CRITICAL: Do NOT override Modelfile parameters (temperature, max_tokens, etc.)
            # The Modelfile defines character-specific settings that should be respected
            completions_request = CompletionsRequest(
                model=self.model_name,
                messages=messages,
                stream=True
            )
            
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_CHAT_REQUEST,
                completions_request,
                correlation_id=request_id
            )
            
            # Mark request sent and start streaming handler
            self.pending_responses[request_id]["llm_request_sent"] = True
            asyncio.create_task(self._handle_streaming_response(request_id, AICOTopics.MODELSERVICE_COMPLETIONS_STREAM))
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}")
            await self._cleanup_request(request_id)
    
    async def _handle_streaming_response(self, request_id: str, stream_topic: str) -> None:
        """Handle streaming chunks from modelservice and forward to API layer"""
        try:
            self.logger.debug(f"Starting streaming handler for {request_id}")
            accumulated_content = ""
            accumulated_thinking = ""
            
            # Subscribe to streaming chunks with callback
            async def handle_chunk(envelope):
                nonlocal accumulated_content, accumulated_thinking
                try:
                    # Extract StreamingChunk from protobuf envelope
                    from aico.proto.aico_modelservice_pb2 import StreamingChunk
                    streaming_chunk = StreamingChunk()
                    envelope.any_payload.Unpack(streaming_chunk)
                    
                    # Only process chunks for our specific request
                    if streaming_chunk.request_id != request_id:
                        return False  # Not for us, continue listening
                    
                    # Extract chunk content and type from protobuf
                    chunk_content = streaming_chunk.content
                    accumulated_content = streaming_chunk.accumulated_content
                    content_type = streaming_chunk.content_type  # "thinking" or "response"
                    is_done = streaming_chunk.done
                    
                    # Track thinking separately
                    if content_type == "thinking":
                        accumulated_thinking += chunk_content
                    
                    # Publish streaming chunk directly to API layer via message bus
                    if request_id in self.pending_responses:
                        from aico.proto.aico_conversation_pb2 import StreamingResponse
                        import time
                        
                        # Create proper protobuf streaming response with content_type
                        streaming_response = StreamingResponse()
                        streaming_response.request_id = request_id
                        streaming_response.content = chunk_content
                        streaming_response.accumulated_content = accumulated_content
                        streaming_response.done = is_done
                        streaming_response.timestamp = int(time.time() * 1000)  # milliseconds
                        streaming_response.content_type = content_type  # Forward content_type to frontend
                        
                        # Publish directly to API streaming topic
                        await self.bus_client.publish(
                            AICOTopics.CONVERSATION_STREAM,
                            streaming_response,
                            correlation_id=request_id
                        )
                    
                    # If this is the final chunk, handle completion
                    if is_done:
                        self.logger.info(f"Streaming complete: {len(accumulated_content)} chars, thinking: {len(accumulated_thinking)} chars")
                        await self._finalize_streaming_response(request_id, accumulated_content, accumulated_thinking)
                        return True  # Signal to stop subscription
                    return False
                    
                except Exception as e:
                    self.logger.error(f"Error processing streaming chunk: {e}")
                    return False
            
            # Subscribe with proper callback
            await self.bus_client.subscribe(stream_topic, handle_chunk)
                    
        except Exception as e:
            self.logger.error(f"Streaming handler error for {request_id}: {e}")
    
    async def _finalize_streaming_response(self, request_id: str, final_content: str, thinking_content: str = "") -> None:
        """Finalize streaming response and deliver to user (semantic memory approach)"""
        try:
            print(f"💬 [CONVERSATION_ENGINE] 🏁 Finalizing streaming response for {request_id}")
            
            if request_id not in self.pending_responses:
                print(f"💬 [CONVERSATION_ENGINE] ⚠️ Request {request_id} not found in pending responses")
                return
            
            request_data = self.pending_responses[request_id]
            user_message = request_data["user_message"]
            
            # Extract user info from the original message
            user_id = user_message.user_id
            conversation_id = user_message.message.conversation_id
            
            # NOTE: AI response storage happens in streaming handler (line ~895)
            # to avoid duplicate storage
            # Store thinking in message metadata if present
            
            # Create final response message for API layer
            ai_message = Message()
            ai_message.conversation_id = conversation_id
            ai_message.type = Message.MessageType.SYSTEM_RESPONSE
            ai_message.text = final_content
            ai_message.turn_number = 1  # Simple turn tracking
            
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
            await self.bus_client.publish(
                AICOTopics.CONVERSATION_RESPONSE,
                conv_message,
                correlation_id=request_id
            )
            
            # Also publish to AI response topic for API layer
            await self.bus_client.publish(
                "conversation/ai/response/v1",
                conv_message,
                correlation_id=request_id
            )
            
            # Phase 3: Log trajectory for behavioral learning
            if request_id in self.pending_responses:
                pending_data = self.pending_responses[request_id]
                
                user_context = pending_data.get("user_context")
                user_message = pending_data.get("user_message")
                selected_skill_id = pending_data.get("selected_skill_id")
                
                if user_context and user_message:
                    await self._log_trajectory(
                        user_context,
                        user_message,
                        final_content,  # Fixed: use final_content parameter
                        selected_skill_id
                    )
            
            # Don't clean up here - let the LLM response handler clean up
            # This prevents race condition where LLM response arrives after cleanup
            
        except Exception as e:
            print(f"💬 [CONVERSATION_ENGINE] ❌ Error finalizing streaming response: {e}")
            self.logger.error(f"Error finalizing streaming response for {request_id}: {e}")
    
    def _build_system_prompt(self, user_context: UserContext, memory_context: Optional[Dict[str, Any]], skill_id: Optional[str] = None) -> str:
        """Build system prompt with memory context and optional skill template
        
        NOTE: Character personality is defined in the Modelfile (e.g., Modelfile.eve).
        This method only adds contextual information like memory facts, NOT character definition.
        
        Returns empty string if there's no contextual information to add, allowing the
        Modelfile's SYSTEM instruction to be the sole system prompt.
        """
        # DO NOT define character here - that's in the Modelfile
        # Only add contextual information that helps with the current conversation
        prompt_parts = []
        
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
                                self.logger.info(f"🎯 [SKILL] Injected skill template: {skill.skill_name}")
                    except RuntimeError:
                        # No event loop, create one
                        skill = asyncio.run(memory_manager._skill_store.get_skill(skill_id))
                        if skill:
                            prompt_parts.append(f"Interaction style:\n{skill.procedure_template}")
                            self.logger.info(f"🎯 [SKILL] Injected skill template: {skill.skill_name}")
            except Exception as e:
                self.logger.warning(f"🎯 [SKILL] Failed to inject skill template: {e}")
        
        # Add identity context - CRITICAL for LLM to know who it is and who it's talking to
        identity_parts = []
        
        # CRITICAL: Tell the LLM its character name (e.g., "Eve" from model "eve:latest")
        # This prevents the LLM from defaulting to its base model name (e.g., "Qwen")
        if self.model_name:
            # Extract character name from model (e.g., "eve" from "eve:latest")
            character_name = self.model_name.split(':')[0].capitalize()
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
        
        # Add memory context if available
        if memory_context:
            memory_data = memory_context.get("memory_context", {})
            user_facts = memory_data.get("user_facts", [])
            recent_context = memory_data.get("recent_context", [])
            kg_data = memory_context.get("knowledge_graph", {})
            
            self.logger.debug(f"Building system prompt: {len(user_facts)} facts, {len(recent_context)} messages")
            
            # Add knowledge graph context (relationships only)
            print(f"🔍 [PROMPT_DEBUG] kg_data type: {type(kg_data)}, content: {kg_data}")
            if kg_data:
                entities = kg_data.get("entities", [])
                relationships = kg_data.get("relationships", [])
                print(f"🔍 [PROMPT_DEBUG] Found {len(entities)} entities, {len(relationships)} relationships")
                
                # Add relationships as facts (entities are filtered at extraction time)
                if relationships:
                    kg_parts = []
                    rel_lines = []
                    for r in relationships:
                        # Use actual entity text, not type names
                        source = r.get('source', '')
                        target = r.get('target', '')
                        relation = r.get('relation', '')
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
                # NOTE: Empty system prompt is OK - conversation history is in messages array (Ollama standard)
                self.logger.debug(f"No user facts - system prompt empty (history in messages array)")
        else:
            self.logger.warning(f"⚠️ [PROMPT_BUILD] NO memory_context provided")
        
        # Only return a prompt if we have contextual information to add
        # Otherwise return empty string to let Modelfile's SYSTEM be the only system instruction
        prompt = "\n\n".join(prompt_parts) if prompt_parts else ""
        
        if prompt:
            self.logger.debug(f"🔍 [PROMPT_DEBUG] Final system prompt:\n{prompt}")
            print(f"🔍 [PROMPT_DEBUG] ===== FINAL SYSTEM PROMPT =====")
            print(prompt)
            print(f"🔍 [PROMPT_DEBUG] ===== END SYSTEM PROMPT =====")
        else:
            self.logger.debug(f"🔍 [PROMPT_DEBUG] No system prompt - using Modelfile's SYSTEM instruction only")
            print(f"🔍 [PROMPT_DEBUG] ⚠️ NO SYSTEM PROMPT - using Modelfile only")
        
        return prompt
    
    async def _handle_llm_response(self, response) -> None:
        """Handle LLM completion response and deliver final response"""
        try:
            import time
            timestamp = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 🎉 RECEIVED LLM RESPONSE! [{timestamp:.6f}]")
            print(f"💬 [CONVERSATION_ENGINE] Response type: {type(response)}")
            self.logger.info(f"🔍 [ENGINE_FLOW] LLM response received, processing...")
            print(f"💬 [CONVERSATION_ENGINE] 🔍 Unpacking CompletionsResponse...")
            
            # Unpack the LLM response from AicoMessage envelope
            from aico.proto.aico_modelservice_pb2 import CompletionsResponse
            
            # Debug the response structure
            self.logger.debug(f"Received LLM response structure: {type(response)}")
            
            # Unpack the CompletionsResponse from the AicoMessage envelope
            completions_response = CompletionsResponse()
            response.any_payload.Unpack(completions_response)
            
            print(f"💬 [CONVERSATION_ENGINE] ✅ CompletionsResponse unpacked successfully")
            
            # Extract correlation ID from response for proper matching
            correlation_id = None
            try:
                # Get correlation ID from envelope metadata
                correlation_id = response.metadata.attributes.get("correlation_id")
                print(f"💬 [CONVERSATION_ENGINE] 🆔 Extracted correlation_id: {correlation_id}")
                self.logger.info(f"🔍 [ENGINE_FLOW] LLM response correlation_id: {correlation_id}")
                self.logger.debug(f"Received LLM response with correlation_id: {correlation_id}")
            except Exception as e:
                print(f"💬 [CONVERSATION_ENGINE] ❌ Failed to extract correlation_id: {e}")
                self.logger.error(f"Failed to extract correlation_id from LLM response: {e}")
                return
            
            print(f"💬 [CONVERSATION_ENGINE] 🔍 Checking pending responses for {correlation_id}")
            print(f"💬 [CONVERSATION_ENGINE] 📋 Pending requests: {list(self.pending_responses.keys())}")
            
            # Find matching request using correlation ID
            if correlation_id and correlation_id in self.pending_responses:
                print(f"💬 [CONVERSATION_ENGINE] ✅ Found matching request for {correlation_id}")
                self.logger.info(f"🔍 [ENGINE_FLOW] ✅ Found matching request for correlation_id: {correlation_id}")
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
                memory_manager = ai_registry.get("memory")
                if memory_manager:
                    try:
                        await memory_manager.store_message(
                            user_message.user_id, 
                            user_message.message.conversation_id, 
                            response_text, 
                            "assistant"
                        )
                        self.logger.debug(f"AI response stored in semantic memory")
                    except Exception as e:
                        self.logger.error(f"Failed to store AI response in memory: {e}")
                
                self.logger.info(f"🔍 [ENGINE_FLOW] ✅ Response processing complete for correlation_id: {correlation_id}")
                
                # Clean up (but only if not being used by direct API)
                if request_id in self.pending_responses and not self.pending_responses[request_id].get("direct_api_call"):
                    print(f"💬 [CONVERSATION_ENGINE] 🧹 Cleaning up completed request {request_id}")
                    await self._cleanup_request(request_id)
                else:
                    print(f"💬 [CONVERSATION_ENGINE] 🔒 Keeping request {request_id} (direct_api_call or already cleaned)")
            else:
                self.logger.error(f"🔍 [ENGINE_FLOW] ❌ NO MATCHING REQUEST for correlation_id: {correlation_id}")
                self.logger.error(f"🔍 [ENGINE_FLOW] Available pending requests: {list(self.pending_responses.keys())}")
                self.logger.warning(f"No matching request found for correlation_id: {correlation_id}")
                self.logger.debug(f"Pending requests: {list(self.pending_responses.keys())}")
                    
        except Exception as e:
            self.logger.error(f"Error handling LLM response: {e}")

    # Embodiment system removed - focusing on core conversation functionality
    async def _response_timeout_handler(self, request_id: str) -> None:
        """Handle response timeout for a specific request"""
        try:
            self.logger.info(f"🔍 [ENGINE_TIMEOUT] Starting timeout handler for request: {request_id}")
            await asyncio.sleep(self.response_timeout)
            
            # Check if request is still pending after timeout
            if request_id in self.pending_responses:
                self.logger.error(f"🔍 [ENGINE_TIMEOUT] ❌ REQUEST TIMED OUT after {self.response_timeout}s: {request_id}")
                await self._cleanup_request(request_id)
            else:
                self.logger.info(f"🔍 [ENGINE_TIMEOUT] ✅ Request completed before timeout: {request_id}")
                
        except Exception as e:
            self.logger.error(f"Error in timeout handler for {request_id}: {e}")
    
    async def _cleanup_request(self, request_id: str) -> None:
        """Clean up completed request"""
        if request_id in self.pending_responses:
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
            if not memory_manager or not hasattr(memory_manager, '_behavioral_enabled') or not memory_manager._behavioral_enabled:
                return None
            
            # Get Thompson Sampling selector
            if not hasattr(memory_manager, '_thompson_sampling') or not memory_manager._thompson_sampling:
                return None
            
            thompson_sampling = memory_manager._thompson_sampling
            skill_store = memory_manager._skill_store
            
            # Get available skills
            candidate_skills = await skill_store.list_skills(skill_type=None, limit=100)
            if not candidate_skills:
                self.logger.warning("🎯 [SKILL] No skills available for selection")
                return None
            
            # Build context for selection (simplified - could be enhanced with intent detection)
            context = {
                "intent": "general",  # Could use NLP to detect intent
                "sentiment": "neutral",  # Could use emotion analysis
                "time_of_day": "any"
            }
            
            # Select skill using Thompson Sampling
            selected_skill_id = await thompson_sampling.select_skill(
                user_id=user_context.user_id,
                context=context,
                candidate_skills=candidate_skills
            )
            
            return selected_skill_id
            
        except Exception as e:
            self.logger.error(f"🎯 [SKILL] Failed to select skill: {e}")
            return None
    
    async def _log_trajectory(self, user_context: UserContext, user_message: ConversationMessage, ai_response: str, selected_skill_id: Optional[str]) -> None:
        """
        Log conversation trajectory for behavioral learning.
        
        Args:
            user_context: User context
            user_message: User message
            ai_response: AI response text
            selected_skill_id: ID of skill that was applied
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
            
            # Get database connection
            if not hasattr(memory_manager, '_db_connection') or not memory_manager._db_connection:
                return
            
            db = memory_manager._db_connection
            
            # Generate trajectory ID
            import uuid
            trajectory_id = str(uuid.uuid4())
            
            # Get turn number (count messages in conversation)
            conversation_id = user_message.message.conversation_id
            turn_number = db.execute(
                "SELECT COUNT(*) FROM trajectories WHERE user_id = ? AND conversation_id = ?",
                (user_context.user_id, conversation_id)
            ).fetchone()[0] + 1
            
            # Insert trajectory with message_id for feedback linking
            db.execute(
                """INSERT INTO trajectories (
                    trajectory_id, user_id, conversation_id, turn_number,
                    user_input, selected_skill_id, ai_response, message_id, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trajectory_id,
                    user_context.user_id,
                    conversation_id,
                    turn_number,
                    user_message.message.text,
                    selected_skill_id,
                    ai_response,
                    user_message.message_id,  # Use message_id from ConversationMessage (not message.id)
                    datetime.utcnow().isoformat()
                )
            )
            db.commit()
            
            self.logger.info(f"📝 [TRAJECTORY] Logged turn {turn_number} for conversation {conversation_id}")
            
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
                self.logger.info("Memory manager shutdown completed")
            
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
            raise
