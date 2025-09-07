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
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.core.config import ConfigurationManager
from aico.proto.aico_conversation_pb2 import (
    ConversationMessage, Message, MessageAnalysis,
    ConversationContext, Context, RecentHistory,
    ResponseRequest, ResponseParameters
)
from aico.proto.aico_modelservice_pb2 import CompletionsRequest, ConversationMessage as ModelConversationMessage
from google.protobuf.timestamp_pb2 import Timestamp

from backend.core.service_container import BaseService


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
    
    def __init__(self, config: ConfigurationManager, zmq_context=None):
        super().__init__()
        self.config = config
        self.zmq_context = zmq_context
        self.logger = get_logger("backend", "conversation_engine")
        
        # Core components
        self.bus_client: Optional[MessageBusClient] = None
        self.user_contexts: Dict[str, UserContext] = {}  # user_id -> UserContext
        self.active_threads: Dict[str, ConversationThread] = {}  # thread_id -> ConversationThread
        self.pending_responses: Dict[str, Dict[str, Any]] = {}  # request_id -> response data
        
        # Configuration
        engine_config = config.get("conversation_engine", {})
        self.max_context_messages = engine_config.get("max_context_messages", 10)
        self.response_timeout = engine_config.get("response_timeout_seconds", 30.0)
        self.default_response_mode = ResponseMode(engine_config.get("default_response_mode", "text_only"))
        
        # Feature flags for gradual implementation
        self.enable_emotion_integration = engine_config.get("enable_emotion_integration", False)
        self.enable_personality_integration = engine_config.get("enable_personality_integration", False)
        self.enable_memory_integration = engine_config.get("enable_memory_integration", False)
        self.enable_embodiment = engine_config.get("enable_embodiment", False)
        self.enable_agency = engine_config.get("enable_agency", False)
    
    async def start(self) -> None:
        """Start the conversation engine service"""
        try:
            self.logger.info("Starting Conversation Engine...")
            
            # Connect to message bus
            self.bus_client = MessageBusClient("conversation_engine")
            await self.bus_client.connect()
            
            # Subscribe to conversation topics
            await self._setup_subscriptions()
            
            self.logger.info("Conversation Engine started successfully", extra={
                "features": {
                    "emotion": self.enable_emotion_integration,
                    "personality": self.enable_personality_integration,
                    "memory": self.enable_memory_integration,
                    "embodiment": self.enable_embodiment,
                    "agency": self.enable_agency
                }
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start Conversation Engine: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the conversation engine service"""
        try:
            self.logger.info("Stopping Conversation Engine...")
            
            if self.bus_client:
                await self.bus_client.disconnect()
                self.bus_client = None
            
            # Clear states
            self.user_contexts.clear()
            self.active_threads.clear()
            self.pending_responses.clear()
            
            self.logger.info("Conversation Engine stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Conversation Engine: {e}")
    
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
    
    async def _handle_user_input(self, topic: str, message: ConversationMessage) -> None:
        """Handle incoming user input message"""
        try:
            thread_id = message.message.thread_id
            user_id = message.source
            
            self.logger.info(f"Processing user input", extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "message_type": message.message.type
            })
            
            # Get or create user context and conversation thread
            user_context = self._get_or_create_user_context(user_id)
            thread = self._get_or_create_thread(thread_id, user_context)
            
            # Update thread state
            thread.turn_number += 1
            thread.last_activity = datetime.utcnow()
            thread.message_history.append(message)
            
            # Keep history manageable
            if len(thread.message_history) > self.max_context_messages:
                thread.message_history = thread.message_history[-self.max_context_messages:]
            
            # Analyze message and update context
            await self._analyze_message(thread, message)
            
            # Generate response
            await self._generate_response(thread, message)
            
        except Exception as e:
            self.logger.error(f"Error handling user input: {e}", extra={
                "topic": topic,
                "thread_id": getattr(message.message, 'thread_id', 'unknown')
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
        if thread_id not in self.active_threads:
            self.active_threads[thread_id] = ConversationThread(
                thread_id=thread_id,
                user_context=user_context
            )
            
            self.logger.info(f"Created new conversation thread", extra={
                "thread_id": thread_id,
                "user_id": user_context.user_id
            })
        
        return self.active_threads[thread_id]
    
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
        """Request emotion analysis (scaffolding for future implementation)"""
        # Placeholder: Simulate emotion analysis
        self.logger.debug(f"Requesting emotion analysis", extra={
            "request_id": request_id,
            "thread_id": thread.thread_id
        })
        
        # Simulate response (will be real emotion engine later)
        await asyncio.sleep(0.1)
        await self._handle_emotion_response("emotion/analysis/response/v1", {
            "request_id": request_id,
            "emotion": "neutral",
            "confidence": 0.8,
            "valence": 0.0,
            "arousal": 0.0
        })
    
    async def _request_personality_expression(self, request_id: str, thread: ConversationThread, message: ConversationMessage) -> None:
        """Request personality expression (scaffolding for future implementation)"""
        self.logger.debug(f"Requesting personality expression", extra={
            "request_id": request_id,
            "thread_id": thread.thread_id
        })
        
        # Simulate response (will be real personality engine later)
        await asyncio.sleep(0.1)
        await self._handle_personality_response("personality/expression/response/v1", {
            "request_id": request_id,
            "personality_traits": {"openness": 0.7, "conscientiousness": 0.8},
            "response_style": "warm_and_helpful",
            "behavioral_parameters": {"formality": 0.3, "enthusiasm": 0.7}
        })
    
    async def _request_memory_retrieval(self, request_id: str, thread: ConversationThread, message: ConversationMessage) -> None:
        """Request memory retrieval (scaffolding for future implementation)"""
        self.logger.debug(f"Requesting memory retrieval", extra={
            "request_id": request_id,
            "thread_id": thread.thread_id
        })
        
        # Simulate response (will be real memory system later)
        await asyncio.sleep(0.1)
        await self._handle_memory_response("memory/retrieve/response/v1", {
            "request_id": request_id,
            "memories": [],
            "context": "No relevant memories found",
            "relevance_scores": []
        })
    
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
            
            # Create completions request
            completions_request = CompletionsRequest(
                model="llama3.2:3b",
                messages=messages,
                stream=False,
                temperature=0.7,
                max_tokens=512
            )
            
            # Publish to modelservice
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
                completions_request
            )
            
            # Mark LLM request sent
            self.pending_responses[request_id]["llm_request_sent"] = True
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}")
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
    
    async def _handle_llm_response(self, topic: str, response: Any) -> None:
        """Handle LLM completion response and deliver final response"""
        try:
            # Find matching request (simplified correlation)
            for request_id, pending_data in list(self.pending_responses.items()):
                if pending_data.get("llm_request_sent"):
                    thread = pending_data["thread"]
                    
                    # Extract response text
                    response_text = "I'm here to help!"  # Default
                    if hasattr(response, 'result') and hasattr(response.result, 'message'):
                        response_text = response.result.message.content
                    elif isinstance(response, dict) and "content" in response:
                        response_text = response["content"]
                    
                    # Create response components
                    response_components = ResponseComponents(
                        text=response_text,
                        avatar_actions=self._generate_avatar_actions(thread, response_text) if self.enable_embodiment else None,
                        voice_synthesis=self._generate_voice_parameters(thread, response_text) if self.enable_embodiment else None
                    )
                    
                    # Deliver response
                    await self._deliver_response(thread, response_components)
                    
                    # Cleanup
                    await self._cleanup_request(request_id)
                    break
                    
        except Exception as e:
            self.logger.error(f"Error handling LLM response: {e}")
    
    # ============================================================================
    # EMBODIMENT SYSTEM (SCAFFOLDING)
    # ============================================================================
    
    def _generate_avatar_actions(self, thread: ConversationThread, response_text: str) -> Dict[str, Any]:
        """Generate avatar actions for embodied response (scaffolding)"""
        # Placeholder for avatar system integration
        return {
            "facial_expression": "friendly",
            "gesture": "subtle_nod",
            "eye_contact": True,
            "lip_sync_data": None  # Will be generated by TTS system
        }
    
    def _generate_voice_parameters(self, thread: ConversationThread, response_text: str) -> Dict[str, Any]:
        """Generate voice synthesis parameters (scaffolding)"""
        # Placeholder for voice synthesis integration
        return {
            "voice_model": "default",
            "emotion_tone": "neutral",
            "speaking_rate": 1.0,
            "pitch_variation": 0.1,
            "emphasis_words": []
        }
    
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
