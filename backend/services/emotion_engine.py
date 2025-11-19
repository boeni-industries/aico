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
        print(f"🔍 [EMOTION_ENGINE] emotion_config loaded: {emotion_config}")
        self.appraisal_sensitivity = emotion_config.get("appraisal_sensitivity", 0.7)
        self.regulation_strength = emotion_config.get("regulation_strength", 0.8)
        self.threat_arousal_boost = emotion_config.get("threat_arousal_boost", 0.25)
        self.max_history_size = emotion_config.get("max_history_size", 100)
        print(f"🔍 [EMOTION_ENGINE] regulation_strength set to: {self.regulation_strength}")
        print(f"🔍 [EMOTION_ENGINE] threat_arousal_boost set to: {self.threat_arousal_boost}")
        
        # Emotional inertia configuration (Kuppens et al., 2010; Scherer CPM)
        inertia_config = emotion_config.get("inertia", {})
        self.inertia_enabled = inertia_config.get("enabled", True)
        self.inertia_weight = inertia_config.get("weight", 0.4)  # Previous state influence
        self.reactivity_weight = inertia_config.get("reactivity", 0.6)  # Current appraisal influence
        self.inertia_decay = inertia_config.get("decay_per_turn", 0.1)
        self.supportive_context_bias = inertia_config.get("supportive_context_bias", True)
        
        # Emotional state tracking
        self.current_state: Optional[EmotionalState] = None
        self.previous_state: Optional[EmotionalState] = None  # For inertia calculation
        self.state_history: List[Dict[str, Any]] = []  # Compact states for mood arc
        self.turns_since_state_change: int = 0  # For inertia decay
        
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
            # MessageBusClient stores correlation_id in metadata.attributes
            correlation_id = envelope.metadata.attributes.get("correlation_id", "")
            
            if not correlation_id or correlation_id not in self.pending_sentiment_requests:
                return
            
            # Get the pending request context
            request_context = self.pending_sentiment_requests[correlation_id]
            
            # Parse sentiment response
            from aico.proto.aico_modelservice_pb2 import SentimentResponse
            sentiment_response = SentimentResponse()
            envelope.any_payload.Unpack(sentiment_response)
            
            sentiment_data = {
                "label": sentiment_response.sentiment,
                "confidence": sentiment_response.confidence,  # Changed from "score" to "confidence"
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
            import traceback
            print(f"🚨 [EMOTION_ENGINE] ERROR in sentiment response handler: {e}")
            print(f"🚨 [EMOTION_ENGINE] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error handling sentiment response: {e}\n{traceback.format_exc()}")
    
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
        try:
            request_id = str(uuid.uuid4())
            
            # Create sentiment request
            from aico.proto.aico_modelservice_pb2 import SentimentRequest
            request = SentimentRequest()
            request.text = message_text
            
            # Store context for completing processing when response arrives
            self.pending_sentiment_requests[request_id] = {
                "message_text": message_text,
                "user_id": user_id,
                "conversation_id": conversation_id
            }
            
            # Build response topic for reply_to
            response_topic = AICOTopics.build_response_topic(
                AICOTopics.MODELSERVICE_SENTIMENT_RESPONSE,
                "emotion_engine",
                request_id
            )
            
            # Publish the request
            await self.bus_client.publish(
                AICOTopics.MODELSERVICE_SENTIMENT_REQUEST, 
                request, 
                correlation_id=request_id,
                reply_to=response_topic
            )
            
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
            print(f"🔍 [EMOTION_ENGINE] _complete_emotional_processing CALLED for conversation {conversation_id}")
            
            # Update previous state BEFORE generating new state (for inertia calculation)
            previous_feeling = self.current_state.subjective_feeling if self.current_state else None
            self.previous_state = self.current_state
            print(f"🔍 [EMOTION_ENGINE] Previous state saved: {previous_feeling}")
            
            # Run appraisal with sentiment data (uses self.previous_state for inertia)
            print(f"🔍 [EMOTION_ENGINE] About to call _process_emotional_response_with_sentiment...")
            emotional_state = await self._process_emotional_response_with_sentiment(
                user_id=user_id,
                message_text=message_text,
                conversation_id=conversation_id,
                sentiment_data=sentiment_data
            )
            print(f"🔍 [EMOTION_ENGINE] _process_emotional_response_with_sentiment returned: {emotional_state.subjective_feeling.value}")
            
            # Update current state after generation
            self.current_state = emotional_state
            
            # Track state changes for decay
            if previous_feeling and previous_feeling != emotional_state.subjective_feeling:
                self.turns_since_state_change = 0
            else:
                self.turns_since_state_change += 1
            
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
            import traceback
            print(f"🚨 [EMOTION_ENGINE] EXCEPTION in _complete_emotional_processing: {e}")
            print(f"🚨 [EMOTION_ENGINE] Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error completing emotional processing: {e}\n{traceback.format_exc()}")
    
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
        
        CPM Theory (Scherer, 2001): Relevance is determined by novelty, intrinsic 
        pleasantness, and motivational consistency. This is the first selective filter
        in sequential appraisal - only relevant stimuli merit expensive processing.
        
        Implementation (MULTILINGUAL - no keywords):
        - Intrinsic pleasantness: Sentiment confidence (0-1)
        - Base engagement: Companion attentiveness (0.4)
        
        Returns: Raw relevance score (0-1 range, undampened)
        Note: Sensitivity is applied to thresholds in Stage 2, not to relevance values
        """
        # Base relevance from sentiment confidence
        # Per Scherer CPM (2001): Relevance = novelty + intrinsic pleasantness + goal relevance
        # Confidence reflects certainty of appraisal (intrinsic pleasantness)
        # Note: Valence is pleasantness, NOT intensity (Russell 1980)
        sentiment_confidence = sentiment_data.get("confidence", 0.5)
        
        # Combine factors (multilingual approach)
        base_relevance = (
            sentiment_confidence * 0.6 +  # Sentiment confidence (certainty of appraisal)
            0.4                            # Base engagement (companion attentiveness)
        )
        
        # Boost for detected user emotion (Phase 2+ feature)
        if user_emotion:
            base_relevance = min(base_relevance + 0.2, 1.0)
        
        # Return raw relevance (sensitivity applied to thresholds, not values)
        return base_relevance
    
    async def _analyze_goal_impact(
        self,
        message_text: str,
        relevance: float,
        sentiment_data: Dict[str, Any]
    ) -> str:
        """
        Stage 2: Implication Check - "What does this mean for my companion goals?"
        
        CPM Theory (Scherer, 2001): Evaluates goal conduciveness/obstruction.
        Sequential processing - only processes stimuli that passed relevance filter.
        
        Implementation:
        - Applies appraisal_sensitivity to decision thresholds (not to relevance values)
        - Higher sensitivity (0.7) = lower thresholds = more responsive to user needs
        - Combines relevance with valence to determine goal impact
        
        Returns:
        - supportive_opportunity: Negative valence + high relevance (user needs support)
        - engaging_opportunity: High relevance regardless of valence
        - neutral: Moderate relevance
        - low_priority: Low relevance
        """
        valence = sentiment_data.get("valence", 0.0)
        
        # Per Scherer CPM (2001): Goal conduciveness determines emotional valence
        # Negative valence = goal obstruction → support needed
        # Positive valence = goal conducive → engagement opportunity
        
        # Detect support needs (negative valence + sufficient relevance)
        if valence < -0.3 and relevance > 0.5:
            return "supportive_opportunity"
        
        # Detect engagement opportunities (positive valence + sufficient relevance)
        if valence > 0.3 and relevance > 0.5:
            return "engaging_opportunity"
        
        # Moderate relevance = neutral interaction
        if relevance > 0.4:
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
        # CPM Theory: Each emotion has fixed dimensional profile (Scherer, 2001)
        if appraisal.social_appropriateness == "crisis_protocol":
            feeling = EmotionLabel.PROTECTIVE
            valence = 0.2
            arousal = 0.8
            motivational_tendency = "approach"
        elif appraisal.social_appropriateness == "empathetic_response":
            # High relevance = deeper concern, lower relevance = general reassurance
            if appraisal.relevance > 0.65:
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
        
        # Apply emotion regulation FIRST (part of CPM Stage 3: Coping Potential)
        # Regulation is part of the appraisal process itself, not post-processing
        # (Scherer CPM: coping potential modulates arousal before state persistence)
        arousal = arousal * (1.0 - self.regulation_strength * 0.3)
        
        # Context-aware arousal amplification for high-stakes threats
        # (Sander et al., 2003 relevance theory; 2023 modern threat research)
        # Existential threats (job loss, survival) trigger heightened arousal
        threat_detected = False  # Track if threat boost was applied
        if appraisal.goal_impact == "supportive_opportunity":
            # High relevance + negative sentiment + clear signal = existential threat
            relevance = appraisal.relevance
            sentiment_valence = sentiment_data.get("valence", 0.0)  # Don't overwrite emotion valence!
            confidence = sentiment_data.get("confidence", 0)
            
            if (relevance > 0.65 and sentiment_valence < -0.3 and confidence > 0.4):
                # Amplify arousal for contextually relevant threats (language-agnostic)
                print(f"🔥 [AROUSAL_BOOST] Triggered! relevance={relevance:.2f}, sentiment_valence={sentiment_valence:.2f}, confidence={confidence:.2f}, arousal before={arousal:.2f}")
                arousal *= (1.0 + self.threat_arousal_boost)  # Configurable boost (default 25%)
                threat_detected = True  # Mark for reduced inertia
                print(f"🔥 [AROUSAL_BOOST] Arousal after boost: {arousal:.2f} (+{self.threat_arousal_boost*100:.0f}%)")
            else:
                print(f"⚠️ [AROUSAL_BOOST] NOT triggered: relevance={relevance:.2f} (need >0.65), sentiment_valence={sentiment_valence:.2f} (need <-0.3), confidence={confidence:.2f} (need >0.4)")
        
        # Apply emotional inertia AFTER regulation (Kuppens et al., 2010; Scherer CPM recursive appraisal)
        # Inertia blends the REGULATED appraisal with previous state to prevent double-dampening
        if self.inertia_enabled and self.previous_state is not None:
            # Calculate decay based on turns since state change
            effective_inertia = self.inertia_weight * (1.0 - self.inertia_decay * self.turns_since_state_change)
            effective_inertia = max(0.0, effective_inertia)  # Don't go negative
            
            # Reduce inertia for acute threat responses (LeDoux 1996: amygdala overrides)
            # Existential threats should dominate emotional state, not be dampened by inertia
            if threat_detected:
                effective_inertia *= 0.3  # Reduce inertia to 30% for threat responses
                print(f"🔥 [THREAT_OVERRIDE] Reducing inertia for acute threat response: {effective_inertia:.2f}")
            
            effective_reactivity = 1.0 - effective_inertia
            
            print(f"🧠 [INERTIA] Previous: {self.previous_state.subjective_feeling.value} (v={self.previous_state.mood_valence:.2f}, a={self.previous_state.mood_arousal:.2f})")
            print(f"🧠 [INERTIA] Current (regulated): {feeling.value} (v={valence:.2f}, a={arousal:.2f})")
            print(f"🧠 [INERTIA] Weights: inertia={effective_inertia:.2f}, reactivity={effective_reactivity:.2f}, turns={self.turns_since_state_change}")
            
            # Store regulated values for comparison
            regulated_valence, regulated_arousal = valence, arousal
            
            # Blend previous and current states (leaky integrator model)
            valence = (valence * effective_reactivity) + (self.previous_state.mood_valence * effective_inertia)
            arousal = (arousal * effective_reactivity) + (self.previous_state.mood_arousal * effective_inertia)
            
            print(f"🧠 [INERTIA] Blended: (v={valence:.2f}, a={arousal:.2f})")
            
            # Supportive context bias: DISABLED per Kuppens et al. (2010)
            # Excessive inertia prevents appropriate emotional responses
            # Natural inertia (weight=0.4) is sufficient for emotional continuity
        
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
