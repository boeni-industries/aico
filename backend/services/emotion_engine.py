"""
AICO Emotion Engine

Implements AICO's internal emotion simulation using AppraisalCloudPCT and CPM.
Generates emotional states that condition LLM responses and coordinate expression.

Phase 1: Core emotion loop with 4-stage appraisal and CPM state generation.
Future: User emotion detection integration, multimodal expression coordination.

Design Principles:
- Follow BaseService pattern for lifecycle management
- Use message bus for loose coupling
- Generate compact emotional states following emotion-messages.md spec
- Condition LLM responses via emotional context
- Simple, maintainable, extensible
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.core.logging import get_logger
from backend.core.service_container import BaseService
from aico.proto import aico_emotion_pb2
from google.protobuf import timestamp_pb2


# ============================================================================
# DATA MODELS
# ============================================================================

class EmotionLabel(str, Enum):
    """Canonical emotion labels for label.primary (from emotion-messages.md)"""
    NEUTRAL = "neutral"
    CALM = "calm"
    CURIOUS = "curious"
    PLAYFUL = "playful"
    WARM_CONCERN = "warm_concern"
    PROTECTIVE = "protective"
    FOCUSED = "focused"
    ENCOURAGING = "encouraging"
    REASSURING = "reassuring"
    APOLOGETIC = "apologetic"
    TIRED = "tired"
    REFLECTIVE = "reflective"


@dataclass
class AppraisalResult:
    """4-stage CPM appraisal results"""
    relevance: float  # 0.0-1.0: Does this matter?
    goal_impact: str  # "supportive_opportunity", "neutral", "challenging"
    coping_capability: str  # "high_capability", "moderate", "low"
    social_appropriateness: str  # "empathetic_response", "neutral", etc.
    
    # Metadata
    user_emotion_detected: Optional[str] = None
    crisis_indicators: bool = False


@dataclass
class EmotionalState:
    """
    CPM 5-component emotional state (internal representation).
    Maps to compact frontend projection defined in emotion-messages.md.
    """
    timestamp: datetime
    
    # CPM Components
    cognitive_component: AppraisalResult
    physiological_arousal: float  # 0.0-1.0
    motivational_tendency: str  # "approach", "withdraw", "engage"
    motor_expression: str  # "open", "tense", "relaxed"
    subjective_feeling: EmotionLabel
    
    # Compact projection fields (for frontend/LLM)
    mood_valence: float  # -1.0 to 1.0
    mood_arousal: float  # 0.0 to 1.0
    intensity: float  # 0.0 to 1.0
    
    # Style parameters
    warmth: float = 0.7
    energy: float = 0.5
    directness: float = 0.6
    formality: float = 0.3
    engagement: float = 0.7
    
    # Relationship context
    closeness: float = 0.5
    care_focus: float = 0.7
    
    def to_compact_dict(self) -> Dict[str, Any]:
        """Convert to compact frontend projection (emotion-messages.md)"""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "mood": {
                "valence": round(self.mood_valence, 2),
                "arousal": round(self.mood_arousal, 2)
            },
            "label": {
                "primary": self.subjective_feeling.value,
                "secondary": [],  # TODO: derive from appraisal
                "intensity": round(self.intensity, 2)
            },
            "style": {
                "warmth": round(self.warmth, 2),
                "energy": round(self.energy, 2),
                "directness": round(self.directness, 2),
                "formality": round(self.formality, 2),
                "engagement": round(self.engagement, 2)
            },
            "relationship": {
                "closeness": round(self.closeness, 2),
                "care_focus": round(self.care_focus, 2)
            }
        }


# ============================================================================
# EMOTION PROCESSOR SERVICE
# ============================================================================

class EmotionEngine(BaseService):
    """
    AICO's emotion simulation engine implementing AppraisalCloudPCT/CPM.
    
    Responsibilities:
    - Subscribe to conversation turn events
    - Perform 4-stage appraisal (relevance, implication, coping, normative)
    - Generate CPM-based emotional states
    - Publish compact emotional state for ConversationEngine and frontend
    - Maintain emotional state history
    
    Design: Simple, maintainable, follows AICO patterns
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        
        # Message bus client
        self.bus_client: Optional[MessageBusClient] = None
        
        # Database connection
        self.db_connection = self.container.get_service("database")
        
        # Configuration
        emotion_config = self.container.config.get("core.emotion", {})
        self.appraisal_sensitivity = emotion_config.get("appraisal_sensitivity", 0.7)
        self.regulation_strength = emotion_config.get("regulation_strength", 0.8)
        self.max_history_size = emotion_config.get("max_history_size", 100)
        
        # Emotional state tracking
        self.current_state: Optional[EmotionalState] = None
        self.state_history: List[Dict[str, Any]] = []  # Compact states for mood arc
        
        # Sentiment request tracking (correlation_id -> context for completing processing)
        self.pending_sentiment_requests: Dict[str, Dict[str, Any]] = {}
        
        # Feature flags
        self.enable_user_emotion_detection = emotion_config.get("enable_user_emotion_detection", False)
        self.enable_llm_conditioning = emotion_config.get("enable_llm_conditioning", True)
        
        self.logger.info(f"EmotionEngine initialized with sensitivity={self.appraisal_sensitivity}")
    
    async def initialize(self) -> None:
        """Initialize service resources"""
        # Load persisted state from database, or create neutral baseline
        await self._load_persisted_state()
        print(f"🎭 [EMOTION_ENGINE] Initialized with state: {self.current_state.subjective_feeling.value}")
        self.logger.info(f"Emotion processor initialized with state: {self.current_state.subjective_feeling.value}")
    
    async def start(self) -> None:
        """Start the emotion processor service"""
        try:
            print("🎭 [EMOTION_ENGINE] 🚀 STARTING EMOTION ENGINE...")
            self.logger.info("🎭 [EMOTION_PROCESSOR] Starting emotion processor...")
            
            # Initialize message bus client
            self.bus_client = MessageBusClient("emotion_processor")
            await self.bus_client.connect()
            print("🎭 [EMOTION_ENGINE] ✅ Message bus client connected")
            self.logger.info("🎭 [EMOTION_PROCESSOR] Message bus client connected")
            
            # Subscribe to conversation events
            await self._setup_subscriptions()
            print("🎭 [EMOTION_ENGINE] ✅ Subscriptions established")
            self.logger.info("🎭 [EMOTION_PROCESSOR] Subscriptions established")
            
            # Publish initial neutral state
            await self._publish_emotional_state(self.current_state)
            
            print("🎭 [EMOTION_ENGINE] 🎉 EMOTION ENGINE STARTED SUCCESSFULLY!")
            self.logger.info("🎭 [EMOTION_PROCESSOR] Emotion processor started successfully")
            
        except Exception as e:
            print(f"🎭 [EMOTION_ENGINE] ❌ Failed to start: {e}")
            self.logger.error(f"🎭 [EMOTION_PROCESSOR] Failed to start: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the emotion processor service"""
        try:
            self.logger.info("Stopping emotion processor...")
            
            if self.bus_client:
                await self.bus_client.disconnect()
            
            self.logger.info("Emotion processor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping emotion processor: {e}")
    
    # ============================================================================
    # MESSAGE BUS SETUP
    # ============================================================================
    
    async def _setup_subscriptions(self) -> None:
        """Set up message bus subscriptions"""
        # Subscribe to conversation user input (trigger for emotion processing)
        await self.bus_client.subscribe(
            AICOTopics.CONVERSATION_USER_INPUT,
            self._handle_conversation_turn
        )
        
        # Subscribe to ALL sentiment responses for this engine (wildcard)
        # This avoids per-request subscription overhead and race conditions
        sentiment_response_pattern = f"{AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE}/emotion_engine/"
        await self.bus_client.subscribe(
            sentiment_response_pattern,
            self._handle_sentiment_response
        )
        print(f"🎭 [EMOTION_ENGINE] 🎧 Subscribed to sentiment responses: {sentiment_response_pattern}")
        
        # Optional: Subscribe to user emotion detection results
        if self.enable_user_emotion_detection:
            # await self.bus_client.subscribe(
            #     "user/emotion/detected/v1",
            #     self._handle_user_emotion_detected
            # )
            pass
        
        self.logger.info("Message bus subscriptions established")
    
    # ============================================================================
    # MESSAGE HANDLERS
    # ============================================================================
    
    async def _handle_sentiment_response(self, envelope) -> None:
        """Handle sentiment analysis responses and complete emotional processing"""
        try:
            import time
            receive_time = time.time()
            
            # MessageBusClient stores correlation_id in metadata.attributes
            correlation_id = envelope.metadata.attributes.get("correlation_id", "")
            pending_keys = list(self.pending_sentiment_requests.keys())
            print(f"🎭 [EMOTION_ENGINE] 🔎 Sentiment response received with correlation_id={correlation_id}, pending={pending_keys}")
            
            if not correlation_id or correlation_id not in self.pending_sentiment_requests:
                print("🎭 [EMOTION_ENGINE] ↩️  No matching pending sentiment request for this response, ignoring")
                return
            
            # Get the pending request context
            request_context = self.pending_sentiment_requests[correlation_id]
            request_start = request_context["start_time"]
            total_latency = receive_time - request_start
            print(f"⏱️ [EMOTION_ENGINE] ✅ Response received after {total_latency:.3f}s total latency")
            
            # Parse sentiment response
            from aico.proto.aico_modelservice_pb2 import SentimentResponse
            sentiment_response = SentimentResponse()
            envelope.any_payload.Unpack(sentiment_response)
            
            sentiment_data = {
                "label": sentiment_response.sentiment,
                "score": sentiment_response.confidence,
                "valence": self._map_sentiment_to_valence(sentiment_response.sentiment)
            }
            
            print(f"🎭 [EMOTION_ENGINE] ✅ Sentiment: {sentiment_response.sentiment} (confidence={sentiment_response.confidence:.2f})")
            
            # Complete emotional processing with sentiment data
            await self._complete_emotional_processing(
                message_text=request_context["message_text"],
                user_id=request_context["user_id"],
                conversation_id=request_context["conversation_id"],
                sentiment_data=sentiment_data
            )
            
            # Clean up
            del self.pending_sentiment_requests[correlation_id]
            
        except Exception as e:
            self.logger.error(f"Error handling sentiment response: {e}")
    
    async def _handle_conversation_turn(self, message) -> None:
        """Handle incoming conversation turn - start async emotional processing"""
        try:
            print("🎭 [EMOTION_ENGINE] 📨 Received conversation turn event")
            self.logger.info("🎭 [EMOTION_PROCESSOR] Received conversation turn event")
            
            # Unpack ConversationMessage from envelope
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            conv_message = ConversationMessage()
            message.any_payload.Unpack(conv_message)
            
            user_id = conv_message.user_id if conv_message.user_id else conv_message.source
            message_text = conv_message.message.text
            conversation_id = conv_message.message.conversation_id
            
            self.logger.info(f"🎭 [EMOTION_PROCESSOR] Processing turn for user {user_id[:8]}...")
            
            # Start async sentiment analysis (non-blocking)
            await self._request_sentiment_analysis(
                message_text=message_text,
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            # Return immediately - processing continues when sentiment arrives
            
        except Exception as e:
            self.logger.error(f"Error handling conversation turn: {e}")
    
    # ============================================================================
    # APPRAISAL & EMOTION GENERATION
    # ============================================================================
    
    async def _process_emotional_response_with_sentiment(
        self,
        user_id: str,
        message_text: str,
        conversation_id: str,
        sentiment_data: Dict[str, Any],
        user_emotion: Optional[Dict[str, Any]] = None
    ) -> EmotionalState:
        """
        Process emotional response using 4-stage CPM appraisal with provided sentiment.
        
        Implements Klaus Scherer's Component Process Model.
        """
        
        # Stage 1: Relevance Assessment ("Does this matter to me?")
        relevance = await self._assess_relevance(message_text, user_emotion, sentiment_data)
        print(f"🎭 [EMOTION_ENGINE] Stage 1 - Relevance: {relevance:.2f}")
        self.logger.debug(f"🎭 Appraisal Stage 1 - Relevance: {relevance:.2f}")
        
        # Stage 2: Implication Check ("What does this mean for my goals?")
        goal_impact = await self._analyze_goal_impact(message_text, relevance, sentiment_data)
        print(f"🎭 [EMOTION_ENGINE] Stage 2 - Goal Impact: {goal_impact}")
        self.logger.debug(f"🎭 Appraisal Stage 2 - Goal Impact: {goal_impact}")
        
        # Stage 3: Coping Check ("Can I handle this?")
        coping_capability = await self._determine_coping_capability(message_text, goal_impact, sentiment_data)
        print(f"🎭 [EMOTION_ENGINE] Stage 3 - Coping: {coping_capability}")
        self.logger.debug(f"🎭 Appraisal Stage 3 - Coping: {coping_capability}")
        
        # Stage 4: Normative Check ("Is this socially appropriate?")
        social_appropriateness = await self._apply_social_regulation(goal_impact, coping_capability, sentiment_data)
        print(f"🎭 [EMOTION_ENGINE] Stage 4 - Social Appropriateness: {social_appropriateness}")
        self.logger.debug(f"🎭 Appraisal Stage 4 - Social Regulation: {social_appropriateness}")
        
        # Create appraisal result
        appraisal = AppraisalResult(
            relevance=relevance,
            goal_impact=goal_impact,
            coping_capability=coping_capability,
            social_appropriateness=social_appropriateness,
            user_emotion_detected=user_emotion.get("primary") if user_emotion else None,
            crisis_indicators=self._detect_crisis_indicators(message_text, sentiment_data)
        )
        
        # Generate CPM emotional state from appraisal
        emotional_state = self._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        print(f"🎭 [EMOTION_ENGINE] Generated state: {emotional_state.subjective_feeling.value} (v={emotional_state.mood_valence:.2f}, a={emotional_state.mood_arousal:.2f}, i={emotional_state.intensity:.2f})")
        self.logger.debug(f"🎭 Generated CPM state: {emotional_state.subjective_feeling.value} (valence={emotional_state.mood_valence:.2f}, arousal={emotional_state.mood_arousal:.2f})")
        
        return emotional_state
    
    async def _request_sentiment_analysis(
        self,
        message_text: str,
        user_id: str,
        conversation_id: str
    ) -> None:
        """Request sentiment analysis from modelservice (non-blocking)"""
        import time
        start_time = time.time()
        try:
            request_id = str(uuid.uuid4())
            
            # Create sentiment request
            from aico.proto.aico_modelservice_pb2 import SentimentRequest
            request = SentimentRequest()
            request.text = message_text
            
            print(f"🎭 [EMOTION_ENGINE] 🔍 Requesting sentiment analysis for: '{message_text[:50]}...'")
            print(f"🎭 [EMOTION_ENGINE] 📤 Publishing sentiment request ID: {request_id}")
            
            # Store context for completing processing when response arrives
            self.pending_sentiment_requests[request_id] = {
                "message_text": message_text,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "start_time": start_time
            }
            
            # Build response topic for reply_to
            response_topic = AICOTopics.build_response_topic(
                AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE,
                "emotion_engine",
                request_id
            )
            
            # Publish the request
            publish_start = time.time()
            print(f"🎭 [EMOTION_ENGINE] 🔍 Publishing to topic: {AICOTopics.MODELSERVICE_SENTIMENT_REQUEST}")
            print(f"🎭 [EMOTION_ENGINE] 🔍 With reply_to: {response_topic}")
            print(f"🎭 [EMOTION_ENGINE] 🔍 With correlation_id: {request_id}")
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_SENTIMENT_REQUEST, 
                request, 
                correlation_id=request_id,
                reply_to=response_topic
            )
            publish_time = time.time() - publish_start
            print(f"🎭 [EMOTION_ENGINE] 📨 Published request (took {publish_time*1000:.1f}ms)")
            print(f"🎭 [EMOTION_ENGINE] ⏳ Waiting for async response...")
            
            # Return immediately - response will be handled by callback
                
        except Exception as e:
            print(f"🎭 [EMOTION_ENGINE] ❌ Sentiment request ERROR: {e}")
            import traceback
            print(f"🎭 [EMOTION_ENGINE] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Sentiment request error: {e}")
            # Clean up
            if request_id in self.pending_sentiment_requests:
                del self.pending_sentiment_requests[request_id]
    
    async def _complete_emotional_processing(
        self,
        message_text: str,
        user_id: str,
        conversation_id: str,
        sentiment_data: Dict[str, Any]
    ) -> None:
        """Complete emotional processing with sentiment data (called from callback)"""
        try:
            # Run appraisal with sentiment data
            emotional_state = await self._process_emotional_response_with_sentiment(
                user_id=user_id,
                message_text=message_text,
                conversation_id=conversation_id,
                sentiment_data=sentiment_data
            )
            
            # Update current state
            previous_feeling = self.current_state.subjective_feeling if self.current_state else None
            self.current_state = emotional_state
            
            # Log state transition if significant change
            if previous_feeling and previous_feeling != emotional_state.subjective_feeling:
                print(f"🎭 [EMOTION_ENGINE] 🔄 State transition: {previous_feeling.value} → {emotional_state.subjective_feeling.value}")
                self.logger.info(f"🎭 Emotional state transition: {previous_feeling.value} → {emotional_state.subjective_feeling.value}")
            
            print(f"🎭 [EMOTION_ENGINE] 💭 Generated state: {emotional_state.subjective_feeling.value} (valence={emotional_state.mood_valence:.2f}, arousal={emotional_state.mood_arousal:.2f})")
            
            # Publish emotional state
            await self._publish_emotional_state(emotional_state)
            
            # Add to history (compact format)
            self._add_to_history(emotional_state.to_compact_dict())
            
            self.logger.info(f"🎭 [EMOTION_PROCESSOR] Generated emotional state: {emotional_state.subjective_feeling.value}")
            
        except Exception as e:
            self.logger.error(f"Error completing emotional processing: {e}")
    
    def _map_sentiment_to_valence(self, label: str) -> float:
        """Map sentiment label to valence score [-1.0, 1.0]"""
        # BERT multilingual sentiment uses star ratings
        label_lower = label.lower()
        if '5 star' in label_lower or '4 star' in label_lower:
            return 0.7  # Positive
        elif '1 star' in label_lower or '2 star' in label_lower:
            return -0.7  # Negative
        elif 'positive' in label_lower:
            return 0.7
        elif 'negative' in label_lower:
            return -0.7
        else:
            return 0.0  # Neutral
    
    async def _assess_relevance(
        self, 
        message_text: str, 
        user_emotion: Optional[Dict],
        sentiment_data: Dict[str, Any]
    ) -> float:
        """
        Stage 1: Relevance Check - "Does this event matter to me?"
        
        CPM Theory: Relevance is determined by novelty, intrinsic pleasantness,
        and goal relevance. For a companion AI, relevance increases with:
        - Emotional intensity (from sentiment analysis)
        - Detected user emotion
        - Message engagement indicators
        """
        # Base relevance from sentiment intensity
        sentiment_score = sentiment_data.get("score", 0.5)
        sentiment_intensity = abs(sentiment_score - 0.5) * 2.0  # Map [0,1] to intensity [0,1]
        
        # Emotional content detection (high relevance for emotional messages)
        emotional_keywords = [
            # Stress/anxiety
            'stress', 'worried', 'anxious', 'nervous', 'scared', 'afraid', 'panic',
            'overwhelm', 'pressure', 'tense', 'uncertain', 'doubt',
            # Sadness/distress  
            'sad', 'depressed', 'down', 'upset', 'hurt', 'pain', 'cry', 'tear',
            'lonely', 'alone', 'lost', 'hopeless', 'despair',
            # Anger/frustration
            'angry', 'mad', 'furious', 'annoyed', 'frustrated', 'irritated',
            # Joy/excitement
            'happy', 'excited', 'joy', 'great', 'wonderful', 'amazing', 'love',
            'celebrate', 'proud', 'grateful', 'thankful',
            # Crisis indicators
            'help', 'crisis', 'emergency', 'urgent', 'serious', 'problem',
            'can\'t', 'unable', 'impossible', 'fail', 'lose', 'losing'
        ]
        
        message_lower = message_text.lower()
        emotional_word_count = sum(1 for keyword in emotional_keywords if keyword in message_lower)
        emotional_density = min(emotional_word_count / 3.0, 1.0)  # Normalize
        
        # Combine factors
        base_relevance = (
            sentiment_intensity * 0.4 +  # Sentiment intensity
            emotional_density * 0.4 +     # Emotional keyword density
            0.2                            # Base engagement (always somewhat relevant)
        )
        
        # Boost for detected user emotion (Phase 2+ feature)
        if user_emotion:
            base_relevance = min(base_relevance + 0.2, 1.0)
        
        # Apply appraisal sensitivity configuration
        return base_relevance * self.appraisal_sensitivity
    
    async def _analyze_goal_impact(
        self,
        message_text: str,
        relevance: float,
        sentiment_data: Dict[str, Any]
    ) -> str:
        """
        Stage 2: Implication Check - "What does this mean for my companion goals?"
        
        CPM Theory: Evaluates goal conduciveness/obstruction. For AICO:
        - Supportive opportunity: User needs emotional support
        - Engaging opportunity: User wants interaction/conversation
        - Neutral: Casual interaction
        - Low priority: Minimal engagement needed
        """
        valence = sentiment_data.get("valence", 0.0)
        
        # Detect support needs (negative valence + high relevance)
        if valence < -0.3 and relevance > 0.5:
            return "supportive_opportunity"
        
        # Detect engagement opportunities (any strong emotion)
        if relevance > 0.6:
            return "engaging_opportunity"
        
        # Moderate relevance = neutral interaction
        if relevance > 0.3:
            return "neutral"
        
        # Low relevance = low priority
        return "low_priority"
    
    async def _determine_coping_capability(
        self,
        message_text: str,
        goal_impact: str,
        sentiment_data: Dict[str, Any]
    ) -> str:
        """
        Stage 3: Coping Check - "Can I handle this appropriately?"
        
        CPM Theory: Assesses control and power dynamics. For AICO:
        - High capability: Can provide appropriate support
        - Moderate capability: Can engage but with care
        - Requires escalation: Crisis situation beyond AI capability
        """
        valence = sentiment_data.get("valence", 0.0)
        
        # Crisis detection (very negative + crisis keywords)
        crisis_keywords = ['suicide', 'kill myself', 'end it', 'die', 'harm myself']
        message_lower = message_text.lower()
        has_crisis_keyword = any(keyword in message_lower for keyword in crisis_keywords)
        
        if has_crisis_keyword or valence < -0.8:
            return "requires_escalation"
        
        # High capability for supportive opportunities
        if goal_impact in ["supportive_opportunity", "engaging_opportunity"]:
            return "high_capability"
        
        return "moderate"
    
    async def _apply_social_regulation(
        self,
        goal_impact: str,
        coping_capability: str,
        sentiment_data: Dict[str, Any]
    ) -> str:
        """
        Stage 4: Normative Check - "Is my response socially appropriate?"
        
        CPM Theory: Validates moral/social appropriateness. For AICO:
        - Ensures companion-appropriate boundaries
        - Maintains personality consistency
        - Applies crisis protocols when needed
        """
        # Crisis protocol
        if coping_capability == "requires_escalation":
            return "crisis_protocol"
        
        # Empathetic response for support needs
        if goal_impact == "supportive_opportunity" and coping_capability == "high_capability":
            return "empathetic_response"
        
        # Warm engagement for interaction opportunities
        if goal_impact == "engaging_opportunity":
            return "warm_engagement"
        
        # Neutral for casual interaction
        return "neutral_response"
    
    def _detect_crisis_indicators(self, message_text: str, sentiment_data: Dict[str, Any]) -> bool:
        """Detect crisis indicators requiring immediate attention"""
        crisis_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die',
            'harm myself', 'hurt myself', 'no point', 'give up'
        ]
        message_lower = message_text.lower()
        return any(keyword in message_lower for keyword in crisis_keywords)
    
    def _generate_cpm_emotional_state(
        self, 
        appraisal: AppraisalResult,
        sentiment_data: Dict[str, Any]
    ) -> EmotionalState:
        """
        Generate CPM 5-component emotional state from appraisal results.
        
        Maps appraisal outcomes to emotional components following CPM theory:
        - Cognitive: Appraisal results
        - Physiological: Arousal level
        - Motivational: Action tendencies (approach/withdraw)
        - Motor: Expression patterns
        - Subjective: Conscious feeling label
        """
        valence_from_sentiment = sentiment_data.get("valence", 0.0)
        
        # Determine subjective feeling label based on appraisal
        if appraisal.social_appropriateness == "crisis_protocol":
            feeling = EmotionLabel.PROTECTIVE
            valence = 0.2
            arousal = 0.8
            motivational_tendency = "approach"
        elif appraisal.social_appropriateness == "empathetic_response":
            if appraisal.relevance > 0.7:
                feeling = EmotionLabel.WARM_CONCERN
                valence = 0.3
                arousal = 0.65
            else:
                feeling = EmotionLabel.REASSURING
                valence = 0.4
                arousal = 0.5
            motivational_tendency = "approach"
        elif appraisal.social_appropriateness == "warm_engagement":
            if valence_from_sentiment > 0.3:
                feeling = EmotionLabel.PLAYFUL
                valence = 0.6
                arousal = 0.7
            else:
                feeling = EmotionLabel.CURIOUS
                valence = 0.5
                arousal = 0.6
            motivational_tendency = "engage"
        else:
            # Neutral response
            feeling = EmotionLabel.CALM
            valence = 0.0
            arousal = 0.35
            motivational_tendency = "neutral"
        
        # Apply emotion regulation (dampen intensity based on regulation_strength)
        arousal = arousal * (1.0 - self.regulation_strength * 0.3)
        
        # Determine style parameters for LLM conditioning
        if feeling in [EmotionLabel.WARM_CONCERN, EmotionLabel.PROTECTIVE]:
            warmth = 0.85
            energy = 0.65
            directness = 0.5
            engagement = 0.85
        elif feeling == EmotionLabel.REASSURING:
            warmth = 0.8
            energy = 0.5
            directness = 0.6
            engagement = 0.75
        elif feeling in [EmotionLabel.PLAYFUL, EmotionLabel.CURIOUS]:
            warmth = 0.7
            energy = 0.7
            directness = 0.6
            engagement = 0.8
        else:
            warmth = 0.6
            energy = 0.45
            directness = 0.5
            engagement = 0.6
        
        # Create emotional state
        state = EmotionalState(
            timestamp=datetime.utcnow(),
            cognitive_component=appraisal,
            physiological_arousal=arousal,
            motivational_tendency="approach" if valence > 0 else "neutral",
            motor_expression="open" if engagement > 0.7 else "neutral",
            subjective_feeling=feeling,
            mood_valence=valence,
            mood_arousal=arousal,
            intensity=appraisal.relevance,
            warmth=warmth,
            energy=energy,
            directness=directness,
            formality=0.3,  # Default casual
            engagement=engagement,
            closeness=0.5,  # TODO: derive from relationship context
            care_focus=0.7  # Default caring orientation
        )
        
        return state
    
    def _create_neutral_state(self) -> EmotionalState:
        """Create neutral baseline emotional state"""
        neutral_appraisal = AppraisalResult(
            relevance=0.5,
            goal_impact="neutral",
            coping_capability="high_capability",
            social_appropriateness="neutral_response"
        )
        
        return EmotionalState(
            timestamp=datetime.utcnow(),
            cognitive_component=neutral_appraisal,
            physiological_arousal=0.3,
            motivational_tendency="neutral",
            motor_expression="neutral",
            subjective_feeling=EmotionLabel.CALM,
            mood_valence=0.0,
            mood_arousal=0.3,
            intensity=0.3,
            warmth=0.6,
            energy=0.4,
            directness=0.5,
            formality=0.3,
            engagement=0.6,
            closeness=0.5,
            care_focus=0.7
        )
    
    # ============================================================================
    # STATE PUBLISHING & HISTORY
    # ============================================================================
    
    async def _publish_emotional_state(self, state: EmotionalState) -> None:
        """Publish emotional state to message bus for consumers"""
        try:
            # Create protobuf timestamp
            ts = timestamp_pb2.Timestamp()
            ts.FromDatetime(state.timestamp)
            
            # Create protobuf EmotionState message
            emotion_proto = aico_emotion_pb2.EmotionState(
                primary=state.subjective_feeling.value,
                confidence=state.intensity,
                secondary=[],  # TODO: derive from appraisal
                valence=state.mood_valence,
                arousal=state.mood_arousal,
                dominance=0.5  # Default neutral dominance
            )
            
            # Create EmotionResponse wrapper
            emotion_response = aico_emotion_pb2.EmotionResponse(
                timestamp=ts,
                source="emotion_engine",
                emotion=emotion_proto
            )
            
            # Publish protobuf message
            await self.bus_client.publish(
                AICOTopics.EMOTION_STATE_CURRENT,
                emotion_response
            )
            
            # Note: LLM conditioning is handled via direct service access in ConversationEngine
            # No separate message bus publication needed for Phase 1
            
            self.logger.debug(f"Published emotional state: {state.subjective_feeling.value}")
            
            # Persist state to database
            await self._persist_state(state)
            
        except Exception as e:
            self.logger.error(f"Error publishing emotional state: {e}")
    
    def _add_to_history(self, compact_state: Dict[str, Any]) -> None:
        """Add compact state to history for mood arc visualization"""
        self.state_history.append(compact_state)
        
        # Trim history if too large
        if len(self.state_history) > self.max_history_size:
            trimmed_count = len(self.state_history) - self.max_history_size
            self.state_history = self.state_history[-self.max_history_size:]
            self.logger.debug(f"🎭 Trimmed {trimmed_count} old states from history (max={self.max_history_size})")
    
    async def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get current emotional state (compact projection)"""
        if self.current_state:
            return self.current_state.to_compact_dict()
        return None
    
    async def get_state_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get emotional state history (compact projections)"""
        return self.state_history[-limit:]
    
    # ============================================================================
    # STATE PERSISTENCE
    # ============================================================================
    
    async def _load_persisted_state(self) -> None:
        """Load emotional state from database on startup"""
        try:
            # Load current state
            cursor = self.db_connection.execute(
                "SELECT timestamp, subjective_feeling, mood_valence, mood_arousal, intensity, "
                "warmth, directness, formality, engagement, closeness, care_focus "
                "FROM emotion_state WHERE id = 1"
            )
            row = cursor.fetchone()
            
            if row:
                # Reconstruct emotional state from database
                self.current_state = EmotionalState(
                    timestamp=datetime.fromisoformat(row[0]),
                    subjective_feeling=EmotionLabel(row[1]),
                    mood_valence=row[2],
                    mood_arousal=row[3],
                    intensity=row[4],
                    warmth=row[5],
                    directness=row[6],
                    formality=row[7],
                    engagement=row[8],
                    closeness=row[9],
                    care_focus=row[10]
                )
                self.logger.info(f"🎭 Loaded persisted emotional state: {self.current_state.subjective_feeling.value}")
            else:
                # No persisted state, create neutral baseline
                self.current_state = self._create_neutral_state()
                self.logger.info("🎭 No persisted state found, initialized with neutral baseline")
            
            # Load history (last N entries)
            cursor = self.db_connection.execute(
                "SELECT timestamp, feeling, valence, arousal, intensity "
                "FROM emotion_history "
                "ORDER BY timestamp DESC "
                "LIMIT ?",
                (self.max_history_size,)
            )
            
            # Reverse to get chronological order
            history_rows = list(reversed(cursor.fetchall()))
            self.state_history = [
                {
                    "timestamp": row[0],
                    "feeling": row[1],
                    "valence": row[2],
                    "arousal": row[3],
                    "intensity": row[4]
                }
                for row in history_rows
            ]
            
            if self.state_history:
                self.logger.info(f"🎭 Loaded {len(self.state_history)} historical emotional states")
                
        except Exception as e:
            self.logger.error(f"Error loading persisted emotional state: {e}")
            # Fallback to neutral state
            self.current_state = self._create_neutral_state()
            self.state_history = []
    
    async def _persist_state(self, state: EmotionalState) -> None:
        """Persist emotional state to database"""
        try:
            # Update current state (single row with id=1)
            self.db_connection.execute(
                """INSERT OR REPLACE INTO emotion_state 
                   (id, user_id, timestamp, subjective_feeling, mood_valence, mood_arousal, 
                    intensity, warmth, directness, formality, engagement, closeness, care_focus, updated_at)
                   VALUES (1, 'system', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    state.timestamp.isoformat(),
                    state.subjective_feeling.value,
                    state.mood_valence,
                    state.mood_arousal,
                    state.intensity,
                    state.warmth,
                    state.directness,
                    state.formality,
                    state.engagement,
                    state.closeness,
                    state.care_focus
                )
            )
            
            # Add to history
            compact_state = state.to_compact_dict()
            self.db_connection.execute(
                """INSERT INTO emotion_history 
                   (user_id, timestamp, feeling, valence, arousal, intensity)
                   VALUES ('system', ?, ?, ?, ?, ?)""",
                (
                    compact_state["timestamp"],
                    compact_state["label"]["primary"],
                    compact_state["mood"]["valence"],
                    compact_state["mood"]["arousal"],
                    compact_state["label"]["intensity"]
                )
            )
            
            self.db_connection.commit()
            self.logger.debug(f"🎭 Persisted emotional state: {state.subjective_feeling.value}")
            
        except Exception as e:
            self.logger.error(f"Error persisting emotional state: {e}")


# ============================================================================
# SERVICE FACTORY
# ============================================================================

def create_emotion_engine(container, **kwargs):
    """Factory function for emotion engine creation"""
    return EmotionEngine("emotion_engine", container)
