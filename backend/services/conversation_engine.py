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
            user_id = conv_message.source  # This should be the authenticated user ID
            conversation_id = conv_message.message.conversation_id
            print(f"💬 [CONVERSATION_ENGINE] 📋 User ID: {user_id}, Conversation ID: {conversation_id}")
            
            # Use the actual user_id field if available
            if hasattr(conv_message, 'user_id') and conv_message.user_id:
                user_id = conv_message.user_id
            
            self.logger.info(f"[DEBUG] ConversationEngine: Received user input.", extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "message_type": conv_message.message.type
            })
            
            # Get user context (simplified)
            user_context = self._get_or_create_user_context(user_id)
            
            
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
    
    def _get_or_create_user_context(self, user_id: str) -> UserContext:
        """Get or create user context for authenticated user"""
        if user_id not in self.user_contexts:
            # TODO: Load user preferences from database
            self.user_contexts[user_id] = UserContext(
                user_id=user_id,
                username=f"User_{user_id[:8]}",  # Placeholder
                relationship_type="user",
                conversation_style="friendly",
                last_seen=datetime.utcnow()
            )
            
            self.logger.info(f"Created new user context", extra={
                "user_id": user_id,
                "username": self.user_contexts[user_id].username
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
            
            # Simplified approach - start memory processing in background, generate LLM immediately
            if self.enable_memory_integration:
                self.logger.info(f"[DEBUG] ConversationEngine: Memory integration enabled, starting background memory processing for request {request_id}")
                # Start memory processing in background (non-blocking)
                import asyncio
                asyncio.create_task(self._process_memory_background(request_id, user_context, user_message))
                # Generate LLM response immediately with empty context
                await self._generate_llm_response(request_id, user_context, user_message, {"memory_context": {"user_facts": [], "recent_context": []}, "metadata": {}})
            else:
                self.logger.info(f"[DEBUG] ConversationEngine: Memory integration disabled, generating LLM response directly")
                # If memory is disabled, generate LLM response immediately
                await self._generate_llm_response(request_id, user_context, user_message, {})
            
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
    
    
    async def _process_memory_background(self, request_id: str, user_context: UserContext, message: ConversationMessage):
        """Process memory in background without blocking conversation - RESTORED NON-BLOCKING PATTERN"""
        try:
            start_time = time.time()
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                self.logger.error(f"🔍 [MEMORY_BACKGROUND] Memory manager not available for {request_id}")
                return
            
            user_id = user_context.user_id
            conversation_id = message.message.conversation_id
            message_text = message.message.text
            
            self.logger.info(f"🔍 [MEMORY_BACKGROUND] Starting background memory processing for {request_id}")
            
            # Store user message (let it take as long as needed - it's background)
            try:
                await memory_manager.store_message(user_id, conversation_id, message_text, "user")
                self.logger.info(f"🔍 [MEMORY_BACKGROUND] ✅ User message stored for {request_id}")
            except Exception as e:
                self.logger.error(f"🔍 [MEMORY_BACKGROUND] ❌ Storage failed for {request_id}: {e}")
            
            # Get context (let it take as long as needed - it's background)
            try:
                context = await memory_manager.assemble_context(user_id, message_text)
                memory_context = context.get("memory_context", {})
                user_facts = memory_context.get("user_facts", [])
                
                total_duration = time.time() - start_time
                self.logger.info(f"🔍 [MEMORY_BACKGROUND] ✅ Background processing completed in {total_duration:.3f}s for {request_id} - found {len(user_facts)} facts")
                
                # Memory processing complete - this could be used for future requests or analytics
                
            except Exception as e:
                total_duration = time.time() - start_time
                self.logger.error(f"🔍 [MEMORY_BACKGROUND] ❌ Context assembly failed after {total_duration:.3f}s for {request_id}: {e}")
                
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
    
    async def _generate_llm_response(self, request_id: str, user_context: UserContext, user_message: ConversationMessage, context: Dict[str, Any]) -> None:
        """Generate LLM response with integrated context"""
        from aico.core.topics import AICOTopics
        try:
            # Check if LLM request already sent to prevent duplicates
            if request_id in self.pending_responses and self.pending_responses[request_id].get("llm_request_sent"):
                print(f"💬 [CONVERSATION_ENGINE] ⚠️ LLM request already sent for {request_id}, skipping duplicate")
                print(f"💬 [CONVERSATION_ENGINE] 🔍 Duplicate call stack info - this should help identify the source")
                import traceback
                print(f"💬 [CONVERSATION_ENGINE] 📋 Call stack: {traceback.format_stack()[-3:-1]}")
                return
            
            import time
            llm_start_time = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 🧠 GENERATING LLM RESPONSE for {request_id} at {llm_start_time} [{llm_start_time:.6f}]")
            
            # Include memory data in context if available
            if request_id in self.pending_responses and "memory_data" in self.pending_responses[request_id]:
                memory_data = self.pending_responses[request_id]["memory_data"]
                print(f"💬 [CONVERSATION_ENGINE] 📚 Using memory data from pending responses")
                self.logger.info(f"[MEMORY_DEBUG] Found memory_data for request {request_id}: type={type(memory_data)}, keys={list(memory_data.keys()) if isinstance(memory_data, dict) else 'NOT_DICT'}")
                if memory_data:
                    context["memory"] = memory_data
                    self.logger.info(f"[MEMORY_DEBUG] Added memory data to LLM context for request {request_id}")
                else:
                    self.logger.warning(f"[MEMORY_DEBUG] Memory data exists but is empty for request {request_id}")
            else:
                self.logger.warning(f"[MEMORY_DEBUG] No memory data found for request {request_id}. Pending responses keys: {list(self.pending_responses.get(request_id, {}).keys()) if request_id in self.pending_responses else 'REQUEST_NOT_FOUND'}")
            
            # Build conversation history for LLM
            messages = []
            
            # System prompt with context
            system_prompt = self._build_system_prompt(user_context, context)
            messages.append(ModelConversationMessage(role="system", content=system_prompt))
            
            # CRITICAL FIX: PROPER SEPARATION - Context in system prompt, current input isolated
            current_content = user_message.message.text.strip()
            
            # Simple context integration - no XML processing
            if "memory" in context and context["memory"]:
                memory_context = context["memory"].get("memory_context", {})
                
                # Debug: Log what we're receiving
                self.logger.info(f"🔍 [LLM_DEBUG] Memory context keys: {list(context['memory'].keys())}")
                self.logger.info(f"🔍 [LLM_DEBUG] Memory_context keys: {list(memory_context.keys())}")
                
                # Simple fact integration
                user_facts = memory_context.get("user_facts", [])
                recent_context = memory_context.get("recent_context", [])
                
                self.logger.info(f"🔍 [LLM_DEBUG] Retrieved: {len(user_facts)} user_facts, {len(recent_context)} recent_context")
                
                if user_facts or recent_context:
                    facts_text = "\n".join([f"- {fact.get('content', '')}" for fact in user_facts[-5:]])
                    recent_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_context[-3:]])
                    
                    enhanced_system_prompt = f"""{system_prompt}

User Facts:
{facts_text}

Recent Context:
{recent_text}

Respond naturally using relevant context."""
                    messages[0] = ModelConversationMessage(role="system", content=enhanced_system_prompt)
                else:
                    messages[0] = ModelConversationMessage(role="system", content=system_prompt)
            else:
                messages[0] = ModelConversationMessage(role="system", content=system_prompt)
            
            # MODERN BEST PRACTICE: Clean, isolated current user input
            if current_content:
                # Clean and validate user input
                clean_current_content = current_content.strip()
                if len(clean_current_content) > 2000:  # Prevent token overflow
                    clean_current_content = clean_current_content[:2000] + "..."
                    self.logger.warning(f"[CURRENT_MESSAGE] Truncated long user input to 2000 chars")
                
                messages.append(ModelConversationMessage(role="user", content=clean_current_content))
                self.logger.info(f"[CURRENT_MESSAGE] Added clean isolated current input: '{clean_current_content[:50]}...'")
            else:
                self.logger.error("[CURRENT_MESSAGE] No current user content found!")
                
            # NO message limit needed - we only have system + current user message
            
            # Log final messages being sent to LLM
            self.logger.info(f"[DEBUG] Sending {len(messages)} messages to LLM:")
            for i, msg in enumerate(messages):
                self.logger.info(f"[DEBUG] Message {i}: role={msg.role}, content='{msg.content[:100]}...'")
            
            print(f"💬 [CONVERSATION_ENGINE] 🎯 Creating completions request...")
            
            # CRITICAL FIX: ServiceContainer doesn't have config_manager - use hardcoded model
            conversation_model = "hermes3:8b"
            print(f"💬 [CONVERSATION_ENGINE] 🤖 Using model: {conversation_model} (fixed - no config_manager)")
            
            print(f"💬 [CONVERSATION_ENGINE] 🔨 Creating CompletionsRequest object...")
            
            # Create completions request with streaming enabled
            completions_request = CompletionsRequest(
                model=conversation_model,
                messages=messages,
                stream=True,  # Enable streaming
                temperature=0.3,
                max_tokens=150
            )
            
            print(f"💬 [CONVERSATION_ENGINE] ✅ CompletionsRequest created successfully")
            
            # Publish to modelservice with correlation ID for proper response matching
            self.logger.info(f"💬 [CONVERSATION_ENGINE] Sending chat request to modelservice with correlation_id: {request_id}")
            self.logger.info(f"💬 [CONVERSATION_ENGINE] Model: {conversation_model}, Messages: {len(completions_request.messages)}")
            self.logger.info(f"💬 [CONVERSATION_ENGINE] Topic: {AICOTopics.MODELSERVICE_CHAT_REQUEST}")
            
            print(f"💬 [CONVERSATION_ENGINE] 📡 PUBLISHING LLM REQUEST to {AICOTopics.MODELSERVICE_CHAT_REQUEST}")
            print(f"💬 [CONVERSATION_ENGINE] 🆔 Correlation ID: {request_id}")
            print(f"💬 [CONVERSATION_ENGINE] 📝 Messages count: {len(completions_request.messages)}")
            
            publish_start = time.time()
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_CHAT_REQUEST,
                completions_request,
                correlation_id=request_id
            )
            publish_end = time.time()
            publish_duration = publish_end - publish_start
            
            print(f"💬 [CONVERSATION_ENGINE] ✅ Chat request published to modelservice in {publish_duration:.3f}s")
            self.logger.info(f"💬 [CONVERSATION_ENGINE] ✅ Chat request published to modelservice")
            
            # Mark LLM request sent
            self.pending_responses[request_id]["llm_request_sent"] = True
            
            # Subscribe to streaming chunks from modelservice using proper topic
            print(f"💬 [CONVERSATION_ENGINE] 📡 Subscribing to streaming chunks: {AICOTopics.MODELSERVICE_COMPLETIONS_STREAM}")
            
            # Start streaming handler as background task
            asyncio.create_task(self._handle_streaming_response(request_id, AICOTopics.MODELSERVICE_COMPLETIONS_STREAM))
            
            llm_end_time = time.time()
            llm_total_duration = llm_end_time - llm_start_time
            print(f"💬 [CONVERSATION_ENGINE] 🏁 LLM request generation completed for {request_id} in {llm_total_duration:.2f}s")
            
        except Exception as e:
            print(f"💬 [CONVERSATION_ENGINE] ❌ EXCEPTION in _generate_llm_response: {e}")
            self.logger.error(f"Error generating LLM response: {e}")
            await self._cleanup_request(request_id)
    
    async def _handle_streaming_response(self, request_id: str, stream_topic: str) -> None:
        """Handle streaming chunks from modelservice and forward to API layer"""
        try:
            print(f"💬 [CONVERSATION_ENGINE] 🔄 Starting streaming handler for {request_id}")
            accumulated_content = ""
            
            # Subscribe to streaming chunks with callback
            async def handle_chunk(envelope):
                nonlocal accumulated_content
                try:
                    # Extract StreamingChunk from protobuf envelope
                    from aico.proto.aico_modelservice_pb2 import StreamingChunk
                    streaming_chunk = StreamingChunk()
                    envelope.any_payload.Unpack(streaming_chunk)
                    
                    # Only process chunks for our specific request
                    if streaming_chunk.request_id != request_id:
                        return False  # Not for us, continue listening
                    
                    print(f"💬 [CONVERSATION_ENGINE] 📦 Received streaming chunk for {request_id}")
                    
                    # Extract chunk content from protobuf
                    chunk_content = streaming_chunk.content
                    accumulated_content = streaming_chunk.accumulated_content
                    is_done = streaming_chunk.done
                    
                    # Publish streaming chunk directly to API layer via message bus
                    if request_id in self.pending_responses:
                        from aico.proto.aico_conversation_pb2 import StreamingResponse
                        import time
                        
                        # Create proper protobuf streaming response
                        streaming_response = StreamingResponse()
                        streaming_response.request_id = request_id
                        streaming_response.content = chunk_content
                        streaming_response.accumulated_content = accumulated_content
                        streaming_response.done = is_done
                        streaming_response.timestamp = int(time.time() * 1000)  # milliseconds
                        
                        # Publish directly to API streaming topic
                        await self.bus_client.publish(
                            AICOTopics.CONVERSATION_STREAM,
                            streaming_response,
                            correlation_id=request_id
                        )
                        print(f"💬 [CONVERSATION_ENGINE] 📡 Published chunk to API: content='{chunk_content}', done={is_done}")
                    
                    print(f"💬 [CONVERSATION_ENGINE] 📝 Accumulated content length: {len(accumulated_content)}")
                    
                    # If this is the final chunk, handle completion
                    if is_done:
                        print(f"💬 [CONVERSATION_ENGINE] ✅ Streaming complete for {request_id}")
                        await self._finalize_streaming_response(request_id, accumulated_content)
                        return True  # Signal to stop subscription
                    return False
                    
                except Exception as e:
                    print(f"💬 [CONVERSATION_ENGINE] ❌ Error processing streaming chunk: {e}")
                    return False
            
            # Subscribe with proper callback
            await self.bus_client.subscribe(stream_topic, handle_chunk)
                    
        except Exception as e:
            print(f"💬 [CONVERSATION_ENGINE] ❌ Error in streaming handler: {e}")
            # Remove exc_info parameter - not supported by AICOLogger
            self.logger.error(f"Streaming handler error for {request_id}: {e}")
    
    async def _finalize_streaming_response(self, request_id: str, final_content: str) -> None:
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
            
            # Store AI response in semantic memory (following current architecture)
            memory_manager = ai_registry.get("memory")
            if memory_manager:
                try:
                    await memory_manager.store_message(user_id, conversation_id, final_content, "assistant")
                    print(f"💬 [CONVERSATION_ENGINE] 💾 Stored AI response in semantic memory")
                except Exception as e:
                    self.logger.error(f"Failed to store AI response in memory: {e}")
            
            # Create final response message for API layer
            ai_message = Message()
            ai_message.conversation_id = conversation_id
            ai_message.type = Message.MessageType.SYSTEM_RESPONSE
            ai_message.text = final_content
            ai_message.turn_number = 1  # Simple turn tracking
            
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
            
            print(f"💬 [CONVERSATION_ENGINE] ✅ Final response delivered for {request_id}")
            
            # Don't clean up here - let the LLM response handler clean up
            # This prevents race condition where LLM response arrives after cleanup
            
        except Exception as e:
            print(f"💬 [CONVERSATION_ENGINE] ❌ Error finalizing streaming response: {e}")
            self.logger.error(f"Error finalizing streaming response for {request_id}: {e}")
    
    def _build_system_prompt(self, user_context: UserContext, context: Dict[str, Any]) -> str:
        """Build clean, focused system prompt for optimal LLM performance"""
        user = user_context
        
        # Core identity and behavior - clean and direct
        prompt_parts = [
            "You are AICO, an AI companion.",
            "Respond directly to the user's current message.",
            "Be helpful, concise, and natural."
        ]
        
        # User context - minimal and relevant
        if user.username and not user.username.startswith("User_"):
            prompt_parts.append(f"User: {user.username}")
        
        # Conversation style hint - only if not default
        if user.conversation_style and user.conversation_style != "friendly":
            prompt_parts.append(f"Style: {user.conversation_style}")
        
        # Memory context - removed restrictive limitations
        if "memory" in context and context["memory"]:
            memory_data = context["memory"]
            
            # Add context summary if available (removed length restriction)
            context_summary = memory_data.get("context_summary", "")
            if context_summary:
                # Clean up the summary to avoid redundant info
                if "conversation messages" not in context_summary.lower():
                    prompt_parts.append(f"Context: {context_summary}")
        
        return "\n".join(prompt_parts)
    
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
        """Clean up completed or timed out request"""
        if request_id in self.pending_responses:
            del self.pending_responses[request_id]
            print(f"💬 [CONVERSATION_ENGINE] 🧹 Request {request_id} cleaned up")
            print(f"💬 [CONVERSATION_ENGINE] 📋 Remaining pending requests: {len(self.pending_responses)}")
        else:
            print(f"💬 [CONVERSATION_ENGINE] ⚠️ Attempted to clean up non-existent request: {request_id}")
    
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
