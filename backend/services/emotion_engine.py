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
        
        # Configuration
        emotion_config = self.container.config.get("core.emotion", {})
        self.appraisal_sensitivity = emotion_config.get("appraisal_sensitivity", 0.7)
        self.regulation_strength = emotion_config.get("regulation_strength", 0.8)
        self.max_history_size = emotion_config.get("max_history_size", 100)
        
        # Emotional state tracking
        self.current_state: Optional[EmotionalState] = None
        self.state_history: List[Dict[str, Any]] = []  # Compact states for mood arc
        
        # Feature flags
        self.enable_user_emotion_detection = emotion_config.get("enable_user_emotion_detection", False)
        self.enable_llm_conditioning = emotion_config.get("enable_llm_conditioning", True)
        
        self.logger.info(f"EmotionEngine initialized with sensitivity={self.appraisal_sensitivity}")
    
    async def initialize(self) -> None:
        """Initialize service resources"""
        # Initialize with neutral baseline state
        self.current_state = self._create_neutral_state()
        self.logger.info("Emotion processor initialized with neutral baseline state")
    
    async def start(self) -> None:
        """Start the emotion processor service"""
        try:
            self.logger.info("🎭 [EMOTION_PROCESSOR] Starting emotion processor...")
            
            # Initialize message bus client
            self.bus_client = MessageBusClient("emotion_processor")
            await self.bus_client.connect()
            self.logger.info("🎭 [EMOTION_PROCESSOR] Message bus client connected")
            
            # Subscribe to conversation events
            await self._setup_subscriptions()
            self.logger.info("🎭 [EMOTION_PROCESSOR] Subscriptions established")
            
            # Publish initial neutral state
            await self._publish_emotional_state(self.current_state)
            
            self.logger.info("🎭 [EMOTION_PROCESSOR] Emotion processor started successfully")
            
        except Exception as e:
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
    
    async def _handle_conversation_turn(self, message) -> None:
        """Handle incoming conversation turn and generate emotional response"""
        try:
            self.logger.info("🎭 [EMOTION_PROCESSOR] Received conversation turn event")
            
            # Unpack ConversationMessage from envelope
            from aico.proto.aico_conversation_pb2 import ConversationMessage
            conv_message = ConversationMessage()
            message.any_payload.Unpack(conv_message)
            
            user_id = conv_message.user_id if conv_message.user_id else conv_message.source
            message_text = conv_message.message.text
            conversation_id = conv_message.message.conversation_id
            
            self.logger.info(f"🎭 [EMOTION_PROCESSOR] Processing turn for user {user_id[:8]}...")
            
            # Perform appraisal and generate emotional state
            emotional_state = await self._process_emotional_response(
                user_id=user_id,
                message_text=message_text,
                conversation_id=conversation_id,
                user_emotion=None  # TODO: integrate user emotion detection
            )
            
            # Update current state
            previous_feeling = self.current_state.subjective_feeling if self.current_state else None
            self.current_state = emotional_state
            
            # Log state transition if significant change
            if previous_feeling and previous_feeling != emotional_state.subjective_feeling:
                self.logger.info(f"🎭 Emotional state transition: {previous_feeling.value} → {emotional_state.subjective_feeling.value}")
            
            # Publish emotional state
            await self._publish_emotional_state(emotional_state)
            
            # Add to history (compact format)
            self._add_to_history(emotional_state.to_compact_dict())
            
            self.logger.info(f"🎭 [EMOTION_PROCESSOR] Generated emotional state: {emotional_state.subjective_feeling.value}")
            
        except Exception as e:
            self.logger.error(f"Error handling conversation turn: {e}")
    
    # ============================================================================
    # APPRAISAL & EMOTION GENERATION
    # ============================================================================
    
    async def _process_emotional_response(
        self,
        user_id: str,
        message_text: str,
        conversation_id: str,
        user_emotion: Optional[Dict[str, Any]] = None
    ) -> EmotionalState:
        """
        Process emotional response using 4-stage appraisal.
        
        Phase 1 implementation: simple rule-based appraisal.
        Future: integrate LLM-based appraisal assistance and memory context.
        """
        
        # Stage 1: Relevance Assessment
        relevance = self._assess_relevance(message_text, user_emotion)
        self.logger.debug(f"🎭 Appraisal Stage 1 - Relevance: {relevance:.2f}")
        
        # Stage 2: Goal Impact Analysis
        goal_impact = self._analyze_goal_impact(message_text, relevance)
        self.logger.debug(f"🎭 Appraisal Stage 2 - Goal Impact: {goal_impact}")
        
        # Stage 3: Coping Assessment
        coping_capability = self._determine_coping_capability(message_text, goal_impact)
        self.logger.debug(f"🎭 Appraisal Stage 3 - Coping: {coping_capability}")
        
        # Stage 4: Social Appropriateness Check
        social_appropriateness = self._apply_social_regulation(goal_impact, coping_capability)
        self.logger.debug(f"🎭 Appraisal Stage 4 - Social Regulation: {social_appropriateness}")
        
        # Create appraisal result
        appraisal = AppraisalResult(
            relevance=relevance,
            goal_impact=goal_impact,
            coping_capability=coping_capability,
            social_appropriateness=social_appropriateness,
            user_emotion_detected=user_emotion.get("primary") if user_emotion else None,
            crisis_indicators=False  # TODO: integrate crisis detection
        )
        
        # Generate CPM emotional state from appraisal
        emotional_state = self._generate_cpm_emotional_state(appraisal)
        
        self.logger.debug(f"🎭 Generated CPM state: {emotional_state.subjective_feeling.value} (valence={emotional_state.mood_valence:.2f}, arousal={emotional_state.mood_arousal:.2f})")
        
        return emotional_state
    
    def _assess_relevance(self, message_text: str, user_emotion: Optional[Dict]) -> float:
        """Stage 1: Assess relevance - does this matter?"""
        # Simple heuristic: longer messages and detected emotions increase relevance
        base_relevance = min(len(message_text) / 200.0, 1.0) * 0.5
        
        if user_emotion:
            emotion_boost = 0.3
        else:
            emotion_boost = 0.0
        
        relevance = min(base_relevance + emotion_boost + 0.2, 1.0)
        return relevance * self.appraisal_sensitivity
    
    def _analyze_goal_impact(self, message_text: str, relevance: float) -> str:
        """Stage 2: Analyze goal impact - what does this mean for companion goals?"""
        # Simple heuristic: assume supportive opportunity for now
        # Future: integrate intent classification and memory context
        
        if relevance > 0.7:
            return "supportive_opportunity"
        elif relevance > 0.3:
            return "neutral"
        else:
            return "low_priority"
    
    def _determine_coping_capability(self, message_text: str, goal_impact: str) -> str:
        """Stage 3: Determine coping capability - can I handle this?"""
        # Phase 1: assume high capability for all non-crisis situations
        # Future: integrate crisis detection and complexity assessment
        
        if goal_impact == "supportive_opportunity":
            return "high_capability"
        else:
            return "moderate"
    
    def _apply_social_regulation(self, goal_impact: str, coping_capability: str) -> str:
        """Stage 4: Apply social regulation - is this appropriate?"""
        # Simple mapping for Phase 1
        if goal_impact == "supportive_opportunity" and coping_capability == "high_capability":
            return "empathetic_response"
        else:
            return "neutral_response"
    
    def _generate_cpm_emotional_state(self, appraisal: AppraisalResult) -> EmotionalState:
        """Generate CPM 5-component emotional state from appraisal results"""
        
        # Map appraisal to CPM components (simplified for Phase 1)
        
        # Determine subjective feeling label
        if appraisal.social_appropriateness == "empathetic_response":
            if appraisal.relevance > 0.7:
                feeling = EmotionLabel.WARM_CONCERN
            else:
                feeling = EmotionLabel.CURIOUS
        else:
            feeling = EmotionLabel.CALM
        
        # Determine mood valence and arousal
        if feeling == EmotionLabel.WARM_CONCERN:
            valence = 0.3  # Slightly positive (caring)
            arousal = 0.6  # Moderately activated
        elif feeling == EmotionLabel.CURIOUS:
            valence = 0.5
            arousal = 0.5
        else:
            valence = 0.0
            arousal = 0.3
        
        # Determine style parameters
        if feeling == EmotionLabel.WARM_CONCERN:
            warmth = 0.8
            energy = 0.6
            directness = 0.5
            engagement = 0.8
        elif feeling == EmotionLabel.CURIOUS:
            warmth = 0.7
            energy = 0.6
            directness = 0.6
            engagement = 0.7
        else:
            warmth = 0.6
            energy = 0.4
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
# SERVICE FACTORY
# ============================================================================

def create_emotion_engine(container, **kwargs):
    """Factory function for emotion engine creation"""
    return EmotionEngine("emotion_engine", container)
