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
        
        # Configuration
        engine_config = self.config.get("conversation_engine", {})
        self.max_context_messages = engine_config.get("max_context_messages", 10)
        self.response_timeout = engine_config.get("response_timeout_seconds", 30.0)
        self.default_response_mode = ResponseMode(engine_config.get("default_response_mode", "text_only"))
        
        # Feature flags for gradual implementation
        self.enable_emotion_integration = engine_config.get("enable_emotion_integration", False)
        self.enable_personality_integration = engine_config.get("enable_personality_integration", False)
        self.enable_memory_integration = engine_config.get("enable_memory_integration", False)
        self.enable_embodiment = engine_config.get("enable_embodiment", False)
        self.enable_agency = engine_config.get("enable_agency", False)
    
    async def initialize(self) -> None:
        """Initialize service resources - called once during startup"""
        pass
    
    async def start(self) -> None:
        """Start the conversation engine service"""
        try:
            self.logger.info("Starting conversation engine...")
            
            # Initialize message bus client
            self.bus_client = MessageBusClient("conversation_engine")
            await self.bus_client.connect()
            
            # AI processors will be registered here when implemented
            # No initialization needed for empty registry
            
            # Subscribe to conversation topics
            await self.bus_client.subscribe(
                AICOTopics.CONVERSATION_USER_INPUT,
                self._handle_user_input
            )
            
            # Subscribe to LLM response topics
            await self.bus_client.subscribe(
                AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
                self._handle_llm_response
            )
            
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
        await self.bus_client.subscribe(
            AICOTopics.CONVERSATION_USER_INPUT,
            self._handle_user_input
        )
        
        # LLM responses (always enabled)
        await self.bus_client.subscribe(
            AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE,
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
            # The message is an AicoMessage envelope, need to unpack the ConversationMessage
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            
            # Unpack the ConversationMessage from the AicoMessage envelope
            conv_message = ConversationMessage()
            message.any_payload.Unpack(conv_message)
            
            # Extract data from the ConversationMessage protobuf
            thread_id = conv_message.message.thread_id
            user_id = conv_message.source
            
            self.logger.info(f"Processing user input", extra={
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
            await self._analyze_message(thread, conv_message)
            
            # Generate response
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
            
            if self.enable_emotion_integration:
                components_needed.append("emotion")
                await self._request_emotion_analysis(request_id, thread, user_message)
            
            if self.enable_personality_integration:
                components_needed.append("personality")
                await self._request_personality_expression(request_id, thread, user_message)
            
            if self.enable_memory_integration:
                components_needed.append("memory")
                await self._request_memory_retrieval(request_id, thread, user_message)
            
            self.pending_responses[request_id]["components_needed"] = components_needed
            
            # If no components needed, generate LLM response directly
            if not components_needed:
                await self._generate_llm_response(request_id, thread, user_message, {})
            
            # Set timeout
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
        # Check if memory processor is available
        memory_processor = ai_registry.get("memory")
        
        if memory_processor:
            # Create processing context for memory retrieval
            context = ProcessingContext(
                thread_id=thread.thread_id,
                user_id=thread.user_context.user_id,
                request_id=request_id,
                message_content=message.message.text, # Correctly access the text content
                message_type="text",
                turn_number=thread.turn_number,
                conversation_phase=thread.conversation_phase,
                user_name=thread.user_context.username,
                relationship_type=thread.user_context.relationship_type,
                conversation_style=thread.user_context.conversation_style,
                shared_state={}
            )
            
            try:
                # Process memory operations (store and retrieve)
                result = await memory_processor.process(context)
                if request_id in self.pending_responses and result.success:
                    # The result data is now in context.shared_state
                    self.pending_responses[request_id]["memory_data"] = context.shared_state.get("memory_context")
                    self.logger.debug(f"Memory processing completed for {request_id}")
            except Exception as e:
                self.logger.error(f"Memory processing failed for {request_id}: {e}")
        
        # Always mark as ready (no blocking)
        if request_id in self.pending_responses:
            self.pending_responses[request_id]["memory_ready"] = True
            await self._check_response_completion(request_id)
    
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
            if request_id not in self.pending_responses:
                return
            
            pending_data = self.pending_responses[request_id]
            needed = set(pending_data["components_needed"])
            ready = set(pending_data["components_ready"].keys())
            
            if needed.issubset(ready):
                # All components ready, generate LLM response
                thread = pending_data["thread"]
                user_message = pending_data["user_message"]
                context = pending_data["components_ready"]
                
                await self._generate_llm_response(request_id, thread, user_message, context)
                
        except Exception as e:
            self.logger.error(f"Error checking response completion: {e}")
    
    # ============================================================================
    # LLM INTEGRATION & RESPONSE DELIVERY
    # ============================================================================
    
    async def _generate_llm_response(self, request_id: str, thread: ConversationThread, user_message: ConversationMessage, context: Dict[str, Any]) -> None:
        """Generate LLM response with integrated context"""
        try:
            self.logger.info(f"Generating LLM response", extra={
                "request_id": request_id,
                "thread_id": thread.thread_id,
                "context_components": list(context.keys())
            })
            
            # Build conversation history for LLM
            messages = []
            
            # System prompt with context
            system_prompt = self._build_system_prompt(thread, context)
            messages.append(ModelConversationMessage(role="system", content=system_prompt))
            
            # Add recent conversation history
            for msg in thread.message_history[-5:]:
                role = "user" if msg.message.type == Message.MessageType.USER_INPUT else "assistant"
                messages.append(ModelConversationMessage(role=role, content=msg.message.text))
            
            # Get conversation model from config
            conversation_model = self.config.get("modelservice.ollama.default_models.conversation.name", "hermes3:8b")
            
            # Create completions request
            completions_request = CompletionsRequest(
                model=conversation_model,
                messages=messages,
                stream=False,
                temperature=0.7,
                max_tokens=512
            )
            
            # Publish to modelservice with correlation ID for proper response matching
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
                completions_request,
                correlation_id=request_id
            )
            
            # Mark LLM request sent
            self.pending_responses[request_id]["llm_request_sent"] = True
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}", exc_info=True)
            await self._cleanup_request(request_id)
    
    def _build_system_prompt(self, thread: ConversationThread, context: Dict[str, Any]) -> str:
        """Build system prompt with user and AI component context"""
        user = thread.user_context
        
        prompt_parts = [
            "You are AICO, an AI companion designed to be helpful, empathetic, and engaging.",
            f"You are talking to {user.username} ({user.relationship_type}).",
            f"Current conversation topic: {thread.current_topic}",
            f"Conversation phase: {thread.conversation_phase}",
            f"User's preferred conversation style: {user.conversation_style}"
        ]
        
        # Add emotion context
        if "emotion" in context:
            emotion_data = context["emotion"]
            prompt_parts.append(f"User's detected emotion: {emotion_data.get('emotion', 'neutral')}")
        
        # Add personality context
        if "personality" in context:
            personality_data = context["personality"]
            style = personality_data.get("response_style", "friendly")
            prompt_parts.append(f"Respond in a {style} manner")
        
        # Add memory context
        if "memory" in context:
            memory_data = context["memory"]
            if memory_data.get("memories"):
                prompt_parts.append("Relevant memories: " + str(memory_data["memories"]))
        
        return "\n".join(prompt_parts)
    
    async def _handle_llm_response(self, response) -> None:
        """Handle LLM completion response and deliver final response"""
        try:
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
            if correlation_id and correlation_id in self.pending_responses:
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
                    self.logger.error(f"LLM error: {completions_response.error}")
                    response_text = "I apologize, but I'm having trouble processing your request right now."
                
                self.logger.debug(f"Extracted response text: {response_text}")
                
                # Create response components
                response_components = ResponseComponents(
                    text=response_text,
                    avatar_actions=await self._generate_avatar_actions(thread, response_text) if self.enable_embodiment else None,
                    voice_synthesis=await self._generate_voice_parameters(thread, response_text) if self.enable_embodiment else None
                )
                
                # Deliver response
                await self._deliver_response(thread, response_components)
                
                # Cleanup
                await self._cleanup_request(request_id)
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
            
            # Add to thread history
            thread.message_history.append(ai_message)
            
            # Publish text response
            await self.bus_client.publish(
                AICOTopics.CONVERSATION_AI_RESPONSE,
                ai_message
            )
            
            # Publish embodiment data if enabled
            if self.enable_embodiment and response_components.avatar_actions:
                # TODO: Publish to avatar system topic
                pass
            
            if self.enable_embodiment and response_components.voice_synthesis:
                # TODO: Publish to voice synthesis topic
                pass
            
            self.logger.info(f"Response delivered", extra={
                "thread_id": thread.thread_id,
                "response_length": len(response_components.text),
                "multimodal": self.enable_embodiment
            })
            
        except Exception as e:
            self.logger.error(f"Error delivering response: {e}")
    
    # ============================================================================
    # UTILITY METHODS
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
