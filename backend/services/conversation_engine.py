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


@dataclass
class ConversationThread:
    """Individual conversation thread state"""
    thread_id: str
    user_context: UserContext
    turn_number: int = 0
    current_topic: str = "general"
    conversation_phase: str = "active"
    session_start: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_history: List[ConversationMessage] = field(default_factory=list)
    
    # Context for AI components
    emotion_context: Dict[str, Any] = field(default_factory=dict)
    personality_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    
    # Embodiment state (scaffolding)
    avatar_state: Dict[str, Any] = field(default_factory=dict)
    voice_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseComponents:
    """Components of a multimodal response"""
    text: str
    avatar_actions: Optional[Dict[str, Any]] = None  # Gestures, expressions (future)
    voice_synthesis: Optional[Dict[str, Any]] = None  # TTS parameters (future)
    proactive_triggers: Optional[List[str]] = None   # Agency triggers (future)


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
        
        # Conversation state
        self.user_contexts: Dict[str, UserContext] = {}
        self.conversation_threads: Dict[str, ConversationThread] = {}
        
        # AI processing coordination
        self.pending_responses: Dict[str, Dict[str, Any]] = {}  # request_id -> response data

        # Configuration - access via core.conversation path (like other services)
        engine_config = self.container.config.get("core.conversation", {})
        features_config = engine_config.get("features", {})
        
        # Feature flags for gradual implementation
        self.enable_emotion_integration = features_config.get("enable_emotion_integration", False)
        self.enable_personality_integration = features_config.get("enable_personality_integration", False)
        self.enable_memory_integration = features_config.get("enable_memory_integration", False)
        self.enable_embodiment = features_config.get("enable_embodiment", False)
        self.enable_agency = features_config.get("enable_agency", False)
        
        
        self.max_context_messages = engine_config.get("max_context_messages", 10)
        self.response_timeout = engine_config.get("response_timeout_seconds", 30.0)
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
        
        if self.enable_memory_integration:
            await self.bus_client.subscribe(
                AICOTopics.MEMORY_RETRIEVE_RESPONSE,
                self._handle_memory_response
            )
        
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
            print(f"💬 [CONVERSATION_ENGINE] 🔥 RECEIVED USER INPUT MESSAGE!")
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
            thread_id = conv_message.message.thread_id
            print(f"💬 [CONVERSATION_ENGINE] 📋 User ID: {user_id}, Thread ID: {thread_id}")
            
            # Use the actual user_id field if available
            if hasattr(conv_message, 'user_id') and conv_message.user_id:
                user_id = conv_message.user_id
            
            self.logger.info(f"[DEBUG] ConversationEngine: Received user input.", extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "message_type": conv_message.message.type
            })
            
            # Get or create user context and conversation thread
            user_context = self._get_or_create_user_context(user_id)
            thread = self._get_or_create_thread(thread_id, user_context)
            
            # Update thread state
            thread.turn_number += 1
            thread.last_activity = datetime.utcnow()
            thread.message_history.append(conv_message)
            
            # Keep history manageable
            if len(thread.message_history) > self.max_context_messages:
                thread.message_history = thread.message_history[-self.max_context_messages:]
            
            # Analyze message and update context
            print(f"💬 [CONVERSATION_ENGINE] 🔍 Analyzing message...")
            await self._analyze_message(thread, conv_message)
            
            # Generate response
            print(f"💬 [CONVERSATION_ENGINE] 🤖 Generating response...")
            await self._generate_response(thread, conv_message)
            
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
    
    def _get_or_create_thread(self, thread_id: str, user_context: UserContext) -> ConversationThread:
        """Get or create conversation thread"""
        if thread_id not in self.conversation_threads:
            self.conversation_threads[thread_id] = ConversationThread(
                thread_id=thread_id,
                user_context=user_context
            )
            
            self.logger.info(f"Created new conversation thread", extra={
                "thread_id": thread_id,
                "user_id": user_context.user_id
            })
        
        return self.conversation_threads[thread_id]
    
    # ============================================================================
    # MESSAGE ANALYSIS & RESPONSE GENERATION
    # ============================================================================
    
    async def _analyze_message(self, thread: ConversationThread, message: ConversationMessage) -> None:
        """Analyze message content and update conversation context"""
        try:
            text = message.message.text.lower()
            
            # Simple topic detection (will be more sophisticated later)
            if any(word in text for word in ["hello", "hi", "hey"]):
                thread.current_topic = "greeting"
                thread.conversation_phase = "greeting"
            elif any(word in text for word in ["help", "support", "problem"]):
                thread.current_topic = "support"
                thread.conversation_phase = "problem_solving"
            elif any(word in text for word in ["bye", "goodbye", "see you"]):
                thread.current_topic = "farewell"
                thread.conversation_phase = "closing"
            else:
                thread.current_topic = "general"
                thread.conversation_phase = "conversation"
            
            self.logger.debug(f"Message analyzed", extra={
                "thread_id": thread.thread_id,
                "topic": thread.current_topic,
                "phase": thread.conversation_phase
            })
            
        except Exception as e:
            self.logger.error(f"Error analyzing message: {e}")
    
    async def _generate_response(self, thread: ConversationThread, user_message: ConversationMessage) -> None:
        """Generate and deliver response based on enabled features"""
        try:
            request_id = str(uuid.uuid4())
            print(f"💬 [CONVERSATION_ENGINE] 🎯 Request ID: {request_id}")
            
            # Initialize response tracking
            self.pending_responses[request_id] = {
                "thread": thread,
                "user_message": user_message,
                "components_needed": [],
                "components_ready": {},
                "started_at": datetime.utcnow()
            }
            
            # Determine what components we need
            components_needed = []
            print(f"💬 [CONVERSATION_ENGINE] 🔧 Checking enabled features...")
            
            if self.enable_emotion_integration:
                components_needed.append("emotion")
                await self._request_emotion_analysis(request_id, thread, user_message)
            
            if self.enable_personality_integration:
                components_needed.append("personality")
                await self._request_personality_expression(request_id, thread, user_message)
            
            if self.enable_memory_integration:
                self.logger.info(f"[DEBUG] ConversationEngine: Memory integration enabled, requesting memory retrieval for request {request_id}")
                components_needed.append("memory")
                await self._request_memory_retrieval(request_id, thread, user_message)
            else:
                self.logger.info(f"[DEBUG] ConversationEngine: Memory integration disabled (enable_memory_integration={self.enable_memory_integration})")
            
            self.pending_responses[request_id]["components_needed"] = components_needed
            print(f"💬 [CONVERSATION_ENGINE] 📝 Components needed: {components_needed}")
            
            # If no components needed, generate LLM response directly
            if not components_needed:
                print(f"💬 [CONVERSATION_ENGINE] ⚡ No components needed, generating LLM response directly")
                await self._generate_llm_response(request_id, thread, user_message, {})
            else:
                print(f"💬 [CONVERSATION_ENGINE] ⏳ Waiting for {len(components_needed)} components to complete")
            
            # Set timeout - normal responses should be 1-6 seconds
            asyncio.create_task(self._response_timeout_handler(request_id))
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}", extra={
                "thread_id": thread.thread_id
            })
    
    # ============================================================================
    # AI COMPONENT INTEGRATION (SCAFFOLDING)
    # ============================================================================
    
    async def _request_emotion_analysis(self, request_id: str, thread: ConversationThread, message: ConversationMessage) -> None:
        """Request emotion analysis - ready for future AI processor integration"""
        # Check if emotion processor is available
        emotion_processor = ai_registry.get("emotion")
        
        if emotion_processor:
            # Create processing context for emotion analysis
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=request_id,
                message_content=message.content,
                message_type="text",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style
            )
            
            try:
                # Process emotion analysis
                result = await emotion_processor.analyze_emotion(context)
                if request_id in self.pending_responses:
                    self.pending_responses[request_id]["emotion_data"] = result
                    self.logger.debug(f"Emotion analysis completed for {request_id}")
            except Exception as e:
                self.logger.error(f"Emotion analysis failed for {request_id}: {e}")
        
        # Always mark as ready (no blocking)
        if request_id in self.pending_responses:
            self.pending_responses[request_id]["emotion_ready"] = True
            await self._check_response_completion(request_id)
    
    async def _request_personality_expression(self, request_id: str, thread: ConversationThread, message: ConversationMessage) -> None:
        """Request personality expression - ready for future AI processor integration"""
        # Check if personality processor is available
        personality_processor = ai_registry.get("personality")
        
        if personality_processor:
            # Create processing context for personality expression
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=request_id,
                message_content=message.content,
                message_type="text",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style
            )
            
            try:
                # Process personality expression
                result = await personality_processor.express_personality(context)
                if request_id in self.pending_responses:
                    self.pending_responses[request_id]["personality_data"] = result
                    self.logger.debug(f"Personality expression completed for {request_id}")
            except Exception as e:
                self.logger.error(f"Personality expression failed for {request_id}: {e}")
        
        # Always mark as ready (no blocking)
        if request_id in self.pending_responses:
            self.pending_responses[request_id]["personality_ready"] = True
            await self._check_response_completion(request_id)
    
    async def _request_memory_retrieval(self, request_id: str, thread: ConversationThread, message: ConversationMessage) -> None:
        """Request memory retrieval - ready for future AI processor integration"""
        import time
        start_time = time.time()
        print(f"💬 [CONVERSATION_ENGINE] 🧠 REQUESTING MEMORY RETRIEVAL for {request_id} at {start_time}")
        
        # Check if memory processor is available
        memory_processor = ai_registry.get("memory")
        print(f"💬 [CONVERSATION_ENGINE] 🔍 Memory processor found: {memory_processor is not None}")
        
        self.logger.info(f"[DEBUG] ConversationEngine: Requesting memory retrieval. Memory processor found: {memory_processor is not None}")
        if memory_processor:
            # Create processing context for memory retrieval
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=request_id,
                message_content=message.message.text, # Correctly access the text content
                message_type="user_input",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style,
                shared_state={}
            )
            
            try:
                print(f"💬 [CONVERSATION_ENGINE] ⚡ Calling memory_processor.process() for {request_id}")
                process_start = time.time()
                
                # CRITICAL: Add timeout to prevent deadlocks
                try:
                    # Process memory operations (store and retrieve) with timeout
                    self.logger.info(f"[MEMORY_DEBUG] Calling memory_processor.process() for request {request_id}")
                    result = await asyncio.wait_for(memory_processor.process(context), timeout=10.0)
                    
                    process_end = time.time()
                    process_duration = process_end - process_start
                    print(f"💬 [CONVERSATION_ENGINE] ✅ Memory processor completed: success={getattr(result, 'success', 'NO_SUCCESS_ATTR')} in {process_duration:.2f}s")
                    self.logger.info(f"[MEMORY_DEBUG] Memory processor result: success={getattr(result, 'success', 'NO_SUCCESS_ATTR')}, type={type(result)}, duration={process_duration:.2f}s")
                    
                except asyncio.TimeoutError:
                    process_end = time.time()
                    process_duration = process_end - process_start
                    print(f"💬 [CONVERSATION_ENGINE] ⚠️ Memory processor TIMEOUT after {process_duration:.2f}s for {request_id}")
                    self.logger.error(f"[MEMORY_DEBUG] Memory processor timeout after {process_duration:.2f}s for request {request_id}")
                    result = None
                
                if request_id in self.pending_responses:
                    if hasattr(result, 'success') and result.success:
                        # The result data is now in context.shared_state
                        memory_context = context.shared_state.get("memory_context")
                        self.pending_responses[request_id]["memory_data"] = memory_context
                        self.logger.info(f"[MEMORY_DEBUG] Memory processing completed for {request_id}. Memory context: {type(memory_context)}, keys: {list(memory_context.keys()) if isinstance(memory_context, dict) else 'NOT_DICT'}")
                    else:
                        self.logger.error(f"[MEMORY_DEBUG] Memory processing failed for {request_id}: result.success={getattr(result, 'success', 'NO_SUCCESS_ATTR')}")
                        # Store empty memory data to prevent blocking
                        self.pending_responses[request_id]["memory_data"] = {}
                else:
                    self.logger.error(f"[MEMORY_DEBUG] Request {request_id} not found in pending_responses after memory processing")
            except Exception as e:
                self.logger.error(f"[MEMORY_DEBUG] Memory processing exception for {request_id}: {e}", exc_info=True)
                # Store empty memory data to prevent blocking
                if request_id in self.pending_responses:
                    self.pending_responses[request_id]["memory_data"] = {}
        
        # Always mark as ready (no blocking) - add to components_ready like other components
        if request_id in self.pending_responses:
            # Get the memory data we stored earlier (or empty dict if failed)
            memory_data = self.pending_responses[request_id].get("memory_data", {})
            self.pending_responses[request_id]["components_ready"]["memory"] = memory_data
            
            end_time = time.time()
            total_duration = end_time - start_time
            print(f"💬 [CONVERSATION_ENGINE] ✅ Memory component marked as ready for {request_id} (total: {total_duration:.2f}s)")
            print(f"💬 [CONVERSATION_ENGINE] 🔄 Checking response completion for {request_id}")
            await self._check_response_completion(request_id)
        else:
            end_time = time.time()
            total_duration = end_time - start_time
            print(f"💬 [CONVERSATION_ENGINE] ❌ Request {request_id} not found in pending_responses! (total: {total_duration:.2f}s)")
    
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
    
    async def _handle_memory_response(self, topic: str, response: Any) -> None:
        """Handle memory retrieval response"""
        try:
            request_id = response.get("request_id") if isinstance(response, dict) else None
            if request_id and request_id in self.pending_responses:
                self.pending_responses[request_id]["components_ready"]["memory"] = response
                await self._check_response_completion(request_id)
        except Exception as e:
            self.logger.error(f"Error handling memory response: {e}")
    
    async def _check_response_completion(self, request_id: str) -> None:
        """Check if all components are ready and generate final response"""
        try:
            print(f"💬 [CONVERSATION_ENGINE] 🔍 Checking response completion for {request_id}")
            
            if request_id not in self.pending_responses:
                print(f"💬 [CONVERSATION_ENGINE] ❌ Request {request_id} not found in pending_responses")
                return
            
            pending_data = self.pending_responses[request_id]
            needed = set(pending_data["components_needed"])
            ready = set(pending_data["components_ready"].keys())
            
            print(f"💬 [CONVERSATION_ENGINE] 📊 Components needed: {needed}, ready: {ready}")
            
            if needed.issubset(ready):
                print(f"💬 [CONVERSATION_ENGINE] ✅ All components ready! Generating LLM response...")
                # All components ready, generate LLM response
                thread = pending_data["thread"]
                user_message = pending_data["user_message"]
                context = pending_data["components_ready"]
                
                await self._generate_llm_response(request_id, thread, user_message, context)
            else:
                print(f"💬 [CONVERSATION_ENGINE] ⏳ Still waiting for components: {needed - ready}")
                
        except Exception as e:
            self.logger.error(f"Error checking response completion: {e}")
    
    # ============================================================================
    # LLM INTEGRATION & RESPONSE DELIVERY
    # ============================================================================
    
    async def _generate_llm_response(self, request_id: str, thread: ConversationThread, user_message: ConversationMessage, context: Dict[str, Any]) -> None:
        """Generate LLM response with integrated context"""
        try:
            import time
            llm_start_time = time.time()
            print(f"💬 [CONVERSATION_ENGINE] 🧠 GENERATING LLM RESPONSE for {request_id} at {llm_start_time}")
            
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
            system_prompt = self._build_system_prompt(thread, context)
            messages.append(ModelConversationMessage(role="system", content=system_prompt))
            
            # CRITICAL FIX: PROPER SEPARATION - Context in system prompt, current input isolated
            current_content = user_message.message.text.strip()
            
            # ENHANCED CONTEXT USAGE: Use more memory items and include semantic facts
            context_xml = ""
            user_facts_xml = ""
            
            if "memory" in context and context["memory"]:
                print(f"💬 [CONVERSATION_ENGINE] 🧠 Processing memory context...")
                memory_data = context["memory"]
                print(f"💬 [CONVERSATION_ENGINE] 📋 Memory data type: {type(memory_data)}")
                memories = memory_data.get("memories", [])
                print(f"💬 [CONVERSATION_ENGINE] 📊 Available memory items: {len(memories)}")
                self.logger.info(f"[CONTEXT_DEBUG] Available memory items: {len(memories)}")
                
                if memories:
                    print(f"💬 [CONVERSATION_ENGINE] 🔄 Processing {len(memories)} memory items...")
                    # Separate conversation messages from user facts
                    conversation_items = []
                    user_facts = []
                    
                    # Use more recent memories (up to 8 instead of 2)
                    recent_memories = memories[-8:] if len(memories) > 8 else memories
                    
                    for memory_item in recent_memories:
                        if isinstance(memory_item, dict):
                            content = memory_item.get("content", "").strip()
                            metadata = memory_item.get("metadata", {})
                            source_tier = memory_item.get("source_tier", "unknown")
                            
                            if not content:
                                continue
                                
                            # Separate semantic facts from conversation messages
                            if source_tier == "semantic":
                                # These are user facts - extract key information
                                category = metadata.get("category", "unknown")
                                if len(content) < 200:  # Reasonable fact length
                                    user_facts.append(f"- {content}")
                            elif source_tier == "working" and len(content) < 200:
                                # These are conversation messages
                                role = metadata.get("role", "unknown")
                                clean_content = content.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
                                conversation_items.append(f'<message role="{role}">{clean_content}</message>')
                    
                    # Build conversation history XML
                    if conversation_items:
                        context_xml = f"""
<conversation_history>
{chr(10).join(conversation_items)}
</conversation_history>"""
                        self.logger.info(f"[CONTEXT_DEBUG] Built conversation context with {len(conversation_items)} messages")
                    
                    # Build user facts XML
                    if user_facts:
                        user_facts_xml = f"""
<user_facts>
{chr(10).join(user_facts)}
</user_facts>"""
                        self.logger.info(f"[CONTEXT_DEBUG] Built user facts context with {len(user_facts)} facts")
                
                print(f"💬 [CONVERSATION_ENGINE] ✅ Memory processing completed")
            else:
                print(f"💬 [CONVERSATION_ENGINE] ℹ️ No memory context available")
            
            # MODERN BEST PRACTICE: Enhanced system prompt with clear structure and instructions
            if context_xml or user_facts_xml:
                enhanced_system_prompt = f"""{system_prompt}

{user_facts_xml}{context_xml}

<instructions>
- Use the user_facts above to personalize your response and remember important details about the user
- The conversation_history provides recent context for natural conversation flow
- Respond directly to the user's current message below using relevant information from the context
- Be helpful, personalized, and natural in your response
- Reference user facts when relevant (e.g., their name, preferences, pets, job, etc.)
</instructions>"""
                messages[0] = ModelConversationMessage(role="system", content=enhanced_system_prompt)
                self.logger.info(f"[CONTEXT_DEBUG] Enhanced system prompt with user facts ({len(user_facts) if 'user_facts' in locals() else 0}) and conversation context ({len(conversation_items) if 'conversation_items' in locals() else 0})")
            else:
                # Add clear instructions even without context
                enhanced_system_prompt = f"""{system_prompt}

<instructions>
- Respond directly to the user's message below
- Be helpful and natural in your response
</instructions>"""
                messages[0] = ModelConversationMessage(role="system", content=enhanced_system_prompt)
            
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
            
            # Create completions request with ultra-focused parameters
            completions_request = CompletionsRequest(
                model=conversation_model,
                messages=messages,
                stream=False,
                temperature=0.3,  # CRITICAL FIX: Lower temperature for more focused responses
                max_tokens=150    # CRITICAL FIX: Even shorter responses to prevent rambling
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
            
            llm_end_time = time.time()
            llm_total_duration = llm_end_time - llm_start_time
            print(f"💬 [CONVERSATION_ENGINE] 🏁 LLM request generation completed for {request_id} in {llm_total_duration:.2f}s")
            
        except Exception as e:
            print(f"💬 [CONVERSATION_ENGINE] ❌ EXCEPTION in _generate_llm_response: {e}")
            self.logger.error(f"Error generating LLM response: {e}", exc_info=True)
            await self._cleanup_request(request_id)
    
    def _build_system_prompt(self, thread: ConversationThread, context: Dict[str, Any]) -> str:
        """Build clean, focused system prompt for optimal LLM performance"""
        user = thread.user_context
        
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
            print(f"💬 [CONVERSATION_ENGINE] 🎉 RECEIVED LLM RESPONSE!")
            print(f"💬 [CONVERSATION_ENGINE] Response type: {type(response)}")
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
                request_id = correlation_id
                pending_data = self.pending_responses[request_id]
                thread = pending_data["thread"]
                
                # Extract response text from the completion response
                response_text = "I'm here to help!"  # Default fallback
                
                if completions_response.success and completions_response.result:
                    # Get the message content from the result
                    if completions_response.result.message and completions_response.result.message.content:
                        response_text = completions_response.result.message.content
                elif completions_response.error:
                    self.logger.error(f"LLM completion error: {completions_response.error}")
                    response_text = "I apologize, but I encountered an error generating a response."
                
                # Store response for delivery
                response_components = ResponseComponents(
                    text=response_text,
                    avatar_actions=None,
                    voice_synthesis=None,
                    proactive_triggers=None
                )
                
                # Store response text for direct API access
                if request_id in self.pending_responses:
                    self.pending_responses[request_id]["response_text"] = response_text
                    self.pending_responses[request_id]["response_ready"] = True
                
                # CRITICAL FIX: Store AI response in memory BEFORE delivery to prevent race condition
                # This ensures the AI's response is available for context in the next user message
                memory_processor = ai_registry.get("memory")
                self.logger.info(f"[DEBUG] ConversationEngine: Storing AI response in memory BEFORE delivery. Memory processor found: {memory_processor is not None}")
                if memory_processor:
                    try:
                        ai_context = ProcessingContext(
                            thread_id=thread.thread_id,
                            user_id=thread.user_context.user_id,
                            request_id=f"ai_response_{thread.thread_id}_{thread.turn_number}",
                            message_content=response_text,
                            message_type="ai_response",
                            turn_number=thread.turn_number,
                            conversation_phase=thread.conversation_phase
                        )
                        self.logger.info(f"[DEBUG] ConversationEngine: Calling memory_processor.process() for AI response BEFORE delivery")
                        await memory_processor.process(ai_context)
                        self.logger.info(f"[DEBUG] ConversationEngine: AI response memory storage completed successfully BEFORE delivery")
                    except Exception as e:
                        self.logger.error(f"Failed to store AI response in memory: {e}")
                        import traceback
                        self.logger.error(f"Full traceback: {traceback.format_exc()}")
                else:
                    self.logger.warning(f"[DEBUG] ConversationEngine: Memory processor not found for AI response storage!")
                
                # Deliver response
                await self._deliver_response(thread, response_components)
                
                # Clean up (but only if not being used by direct API)
                if request_id in self.pending_responses and not self.pending_responses[request_id].get("direct_api_call"):
                    print(f"💬 [CONVERSATION_ENGINE] 🧹 Cleaning up completed request {request_id}")
                    await self._cleanup_request(request_id)
                else:
                    print(f"💬 [CONVERSATION_ENGINE] 🔒 Keeping request {request_id} (direct_api_call or already cleaned)")
            else:
                self.logger.warning(f"No matching request found for correlation_id: {correlation_id}")
                self.logger.debug(f"Pending requests: {list(self.pending_responses.keys())}")
                    
        except Exception as e:
            self.logger.error(f"Error handling LLM response: {e}")

    # ============================================================================
    # EMBODIMENT SYSTEM (SCAFFOLDING)
    # ============================================================================
    
    async def _generate_avatar_actions(self, thread: ConversationThread, response_text: str) -> Optional[Dict[str, Any]]:
        """Generate avatar actions for embodied response"""
        # Check if embodiment processor is available
        embodiment_processor = self.ai_processors.get("embodiment")
        
        if embodiment_processor:
            # Create processing context for avatar generation
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=str(uuid.uuid4()),
                message_content=response_text,
                message_type="response",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style
            )
            
            try:
                # Generate avatar actions
                result = await embodiment_processor.generate_avatar_actions(context)
                self.logger.debug(f"Avatar actions generated for thread {thread.thread_id}")
                return result
            except Exception as e:
                self.logger.error(f"Avatar action generation failed: {e}")
        
        return None
    
    async def _generate_voice_parameters(self, thread: ConversationThread, response_text: str) -> Optional[Dict[str, Any]]:
        """Generate voice synthesis parameters for embodied response"""
        # Check if embodiment processor is available
        embodiment_processor = self.ai_processors.get("embodiment")
        
        if embodiment_processor:
            # Create processing context for voice generation
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=str(uuid.uuid4()),
                message_content=response_text,
                message_type="response",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style
            )
            
            try:
                # Generate voice parameters
                result = await embodiment_processor.generate_voice_parameters(context)
                self.logger.debug(f"Voice parameters generated for thread {thread.thread_id}")
                return result
            except Exception as e:
                self.logger.error(f"Voice parameter generation failed: {e}")
        
        return None
    
    async def _deliver_response(self, thread: ConversationThread, response_components: ResponseComponents) -> None:
        """Deliver multimodal response to user"""
        try:
            print(f"💬 [CONVERSATION_ENGINE] 📤 DELIVERING RESPONSE!")
            print(f"💬 [CONVERSATION_ENGINE] Response text: {response_components.text[:100]}...")
            
            # Create AI response message
            ai_message = ConversationMessage()
            ai_message.timestamp.GetCurrentTime()
            ai_message.source = "conversation_engine"
            
            ai_message.message.text = response_components.text
            ai_message.message.type = Message.MessageType.SYSTEM_RESPONSE
            ai_message.message.thread_id = thread.thread_id
            ai_message.message.turn_number = thread.turn_number
            
            ai_message.analysis.intent = "response"
            ai_message.analysis.urgency = MessageAnalysis.Urgency.LOW
            ai_message.analysis.requires_response = False
            
            # Publish AI response to conversation topic
            await self.bus_client.publish(AICOTopics.CONVERSATION_AI_RESPONSE, ai_message)
            
            # Update thread state
            thread.turn_number += 1
            thread.last_activity = datetime.utcnow()
            thread.message_history.append(ai_message)
            
            # Optional multimodal components
            if self.enable_embodiment and response_components.avatar_actions:
                # TODO: Publish to avatar system topic
                pass
            
            if self.enable_embodiment and response_components.voice_synthesis:
                # TODO: Publish to voice synthesis topic
                pass
            
            self.logger.info(f"✅ Response delivered to conversation/ai/response/v1", extra={
                "thread_id": thread.thread_id,
                "response_length": len(response_components.text),
                "multimodal": self.enable_embodiment
            })
            
        except Exception as e:
            self.logger.error(f"Error delivering response: {e}")
    
    # ============================================================================
 
    
    async def _response_timeout_handler(self, request_id: str) -> None:
        """Handle response timeout"""
        await asyncio.sleep(self.response_timeout)
        
        if request_id in self.pending_responses:
            self.logger.warning(f"Response timeout for request {request_id}")
            await self._cleanup_request(request_id)
    
    async def _cleanup_request(self, request_id: str) -> None:
        """Clean up completed or timed out request"""
        if request_id in self.pending_responses:
            del self.pending_responses[request_id]
    

    async def health_check(self) -> Dict[str, Any]:
        """Health check for conversation engine"""
        return {
            "status": "healthy" if self.bus_client else "disconnected",
            "active_users": len(self.user_contexts),
            "active_threads": len(self.active_threads),
            "pending_responses": len(self.pending_responses),
            "features_enabled": {
                "emotion": self.enable_emotion_integration,
                "personality": self.enable_personality_integration,
                "memory": self.enable_memory_integration,
                "embodiment": self.enable_embodiment,
                "agency": self.enable_agency
            }
        }
