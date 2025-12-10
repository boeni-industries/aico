"""
Curiosity Engine Service

Detects curiosity opportunities and generates intrinsic motivation signals.
Based on agency-component-curiosity-engine.md.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .models import (
    IntrinsicSignal,
    CuriosityType,
    HobbyTemplate,
    DEFAULT_HOBBY_TEMPLATES,
)
from .intrinsic_reward import IntrinsicRewardCalculator
from .clustering import OpportunityClusterer

try:
    from aico.core.logging import get_logger
    logger = get_logger("shared", "curiosity.engine")
except Exception:
    import logging
    logger = logging.getLogger(__name__)


class CuriosityEngine:
    """Curiosity Engine for intrinsic motivation and hobby generation.
    
    Detects gaps, anomalies, and under-explored areas in the world model
    and generates curiosity signals that can become agent-self goals.
    
    Based on agency-component-curiosity-engine.md.
    """
    
    def __init__(
        self,
        world_model=None,
        personality_service=None,
        ams_service=None,
        hobby_templates: Optional[List[HobbyTemplate]] = None,
    ):
        """Initialize Curiosity Engine.
        
        Args:
            world_model: WorldModelService for querying knowledge
            personality_service: PersonalityService for personality-based scoring
            ams_service: AMS for user interest tracking
            hobby_templates: List of hobby templates (uses defaults if None)
        """
        self.world_model = world_model
        self.personality = personality_service
        self.ams = ams_service
        self.hobby_templates = hobby_templates or DEFAULT_HOBBY_TEMPLATES
        
        # Phase 6.3: Advanced components
        self.reward_calculator = IntrinsicRewardCalculator()
        self.clusterer = OpportunityClusterer(similarity_threshold=0.7)
        
        logger.info(
            f"[CURIOSITY] Engine initialized with {len(self.hobby_templates)} hobby templates "
            f"(Phase 6.3: Advanced intrinsic reward)"
        )
    
    async def scan_for_opportunities(
        self,
        user_id: str,
        max_signals: int = 10,
    ) -> List[IntrinsicSignal]:
        """Scan for curiosity opportunities.
        
        Runs all detectors and returns scored signals that pass gates.
        
        Args:
            user_id: User to scan for
            max_signals: Maximum number of signals to return
            
        Returns:
            List of IntrinsicSignal objects, sorted by total_score descending
        """
        try:
            logger.debug(f"[CURIOSITY] Scanning for opportunities for user {user_id}")
            
            # Collect signals from all detectors
            signals = []
            
            # Gap detector
            gap_signals = await self._detect_knowledge_gaps(user_id)
            signals.extend(gap_signals)
            
            # Anomaly detector
            anomaly_signals = await self._detect_anomalies(user_id)
            signals.extend(anomaly_signals)
            
            # Interest tracker
            interest_signals = await self._track_interests(user_id)
            signals.extend(interest_signals)
            
            logger.debug(f"[CURIOSITY] Collected {len(signals)} raw signals")
            
            # Phase 6.3: Calculate intrinsic rewards for all signals
            for signal in signals:
                await self._calculate_intrinsic_reward(signal, user_id)
            
            # Score and filter signals
            scored_signals = await self._score_and_filter_signals(signals, user_id)
            
            # Phase 6.3: Cluster and deduplicate
            deduplicated = self.clusterer.cluster_and_deduplicate(
                scored_signals,
                max_per_cluster=1
            )
            
            # Sort by intrinsic_reward descending and limit
            deduplicated.sort(key=lambda s: s.intrinsic_reward, reverse=True)
            result = deduplicated[:max_signals]
            
            logger.info(
                f"[CURIOSITY] Scan complete: {len(result)} signals "
                f"(from {len(signals)} raw, {len(scored_signals)} scored, {len(deduplicated)} deduplicated)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Failed to scan for opportunities: {e}")
            return []
    
    async def _detect_knowledge_gaps(self, user_id: str) -> List[IntrinsicSignal]:
        """Detect knowledge gaps in world model.
        
        Phase 6.3: Full implementation with World Model integration.
        
        From agency-component-curiosity-engine.md Section 2.2:
        - High prediction error or inconsistency
        - Sparse or missing WorldStateFacts
        - Under-represented topics in AMS
        
        Args:
            user_id: User to check
            
        Returns:
            List of knowledge_gap signals
        """
        signals = []
        
        try:
            if not self.world_model:
                logger.debug("[CURIOSITY] No World Model available for gap detection")
                return signals
            
            # Query World Model for uncertain areas
            uncertain_areas = await self.world_model.query_uncertain_areas(user_id)
            
            for area in uncertain_areas:
                topic = area.get("topic", "Unknown")
                uncertainty = area.get("uncertainty", 0.5)
                fact_count = area.get("fact_count", 0)
                
                # Create signal for knowledge gap
                signal = IntrinsicSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id=user_id,
                    signal_type=CuriosityType.KNOWLEDGE_GAP,
                    topic=topic,
                    description=f"Knowledge gap detected in {topic}: {area.get('description', 'Limited information available')}",
                    context={
                        "area": area,
                        "world_model_data": area,
                    },
                    # Basic scores (intrinsic reward calculated later)
                    novelty_score=max(0.0, 1.0 - (fact_count / 20.0)),
                    uncertainty_score=uncertainty,
                    user_relevance_score=area.get("relevance", 0.5),
                    feasibility_score=0.7,  # Knowledge gaps are generally feasible to explore
                    source_component="gap_detector",
                )
                signals.append(signal)
            
            logger.debug(f"[CURIOSITY] Gap detector found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Gap detection failed: {e}")
        
        return signals
    
    async def _detect_anomalies(self, user_id: str) -> List[IntrinsicSignal]:
        """Detect anomalies and inconsistencies.
        
        Phase 6.3: Full implementation with World Model integration.
        
        From agency-component-curiosity-engine.md Section 2.2:
        - Contradictions in information
        - Unusual patterns
        - Incomplete information
        - Temporal anomalies
        
        Args:
            user_id: User to check
            
        Returns:
            List of novelty signals
        """
        signals = []
        
        try:
            if not self.world_model:
                logger.debug("[CURIOSITY] No World Model available for anomaly detection")
                return signals
            
            # Query World Model for contradictions and anomalies
            anomalies = await self.world_model.detect_anomalies(user_id)
            
            for anomaly in anomalies:
                topic = anomaly.get("topic", "Unknown")
                anomaly_type = anomaly.get("type", "unknown")
                severity = anomaly.get("severity", 0.5)
                
                # Create signal for anomaly
                signal = IntrinsicSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id=user_id,
                    signal_type=CuriosityType.NOVELTY,
                    topic=topic,
                    description=f"Anomaly detected in {topic}: {anomaly.get('description', 'Unusual pattern or contradiction')}",
                    context={
                        "anomaly": anomaly,
                        "anomaly_type": anomaly_type,
                        "world_model_data": anomaly,
                    },
                    # Basic scores
                    novelty_score=severity,  # Anomalies are novel by definition
                    uncertainty_score=anomaly.get("uncertainty", 0.6),
                    user_relevance_score=anomaly.get("relevance", 0.5),
                    feasibility_score=0.6,
                    source_component="anomaly_detector",
                )
                signals.append(signal)
            
            logger.debug(f"[CURIOSITY] Anomaly detector found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Anomaly detection failed: {e}")
        
        return signals
    
    async def _track_interests(self, user_id: str) -> List[IntrinsicSignal]:
        """Track and predict user interests for hobby opportunities.
        
        Phase 6.3: Full implementation with AMS integration.
        
        From agency-component-curiosity-engine.md Section 2.2:
        - Topic engagement metrics
        - Repeated mentions of interests
        - Behavioral patterns suggesting latent needs
        
        Args:
            user_id: User to check
            
        Returns:
            List of hobby_play signals
        """
        signals = []
        
        try:
            # Phase 6.3: Query AMS for user interests and engagement patterns
            user_interests = []
            if self.ams:
                user_interests = await self.ams.get_user_interests(user_id, limit=20)
            
            # Generate signals from detected interests
            for interest in user_interests:
                topic = interest.get("topic", "Unknown")
                engagement = interest.get("engagement_score", 0.5)
                mentions = interest.get("mention_count", 0)
                recency = interest.get("recency_score", 0.5)
                
                # Find matching hobby template
                matching_template = self._find_matching_hobby_template(topic)
                
                signal = IntrinsicSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id=user_id,
                    signal_type=CuriosityType.HOBBY_PLAY,
                    topic=topic,
                    description=f"User interest detected: {topic} (mentioned {mentions} times, engagement: {engagement:.2f})",
                    context={
                        "interest": interest,
                        "template_id": matching_template.template_id if matching_template else None,
                        "ams_data": interest,
                    },
                    # Scores based on AMS data
                    novelty_score=max(0.0, 1.0 - recency),  # Less recent = more novel
                    uncertainty_score=0.3,  # Interests are relatively certain
                    user_relevance_score=engagement,  # Direct from engagement
                    feasibility_score=0.8,  # Hobbies are generally feasible
                    source_component="interest_tracker",
                    topic_tags=[matching_template.category.value] if matching_template else [],
                )
                signals.append(signal)
            
            # Also generate signals from hobby templates for personality fit
            if self.personality:
                personality_signals = await self._generate_personality_hobby_signals(user_id)
                signals.extend(personality_signals)
            
            logger.debug(f"[CURIOSITY] Interest tracker found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Interest tracking failed: {e}")
        
        return signals
    
    def _find_matching_hobby_template(self, topic: str) -> Optional[HobbyTemplate]:
        """Find hobby template that matches a topic.
        
        Args:
            topic: Topic to match
            
        Returns:
            Matching HobbyTemplate or None
        """
        topic_lower = topic.lower()
        
        # Simple keyword matching
        for template in self.hobby_templates:
            template_keywords = template.name.lower().split()
            if any(keyword in topic_lower for keyword in template_keywords):
                return template
        
        return None
    
    async def _generate_personality_hobby_signals(self, user_id: str) -> List[IntrinsicSignal]:
        """Generate hobby signals based on personality fit.
        
        Args:
            user_id: User ID
            
        Returns:
            List of hobby signals
        """
        signals = []
        
        try:
            personality_context = await self.personality.get_personality_context(user_id)
            
            for template in self.hobby_templates:
                # Check if personality traits match template requirements
                fits = True
                fit_score = 1.0
                
                for trait_name, required_level in template.personality_traits.items():
                    actual_level = getattr(personality_context.traits, trait_name, 0.5)
                    if actual_level < required_level:
                        fits = False
                        break
                    # Calculate how well it fits
                    fit_score *= (actual_level / required_level)
                
                if not fits:
                    continue
                
                # Create hobby opportunity signal
                signal = IntrinsicSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id=user_id,
                    signal_type=CuriosityType.HOBBY_PLAY,
                    topic=template.name,
                    description=template.description,
                    context={
                        "template_id": template.template_id,
                        "category": template.category.value,
                        "personality_fit": fit_score,
                    },
                    novelty_score=0.5,
                    uncertainty_score=0.3,
                    user_relevance_score=min(fit_score, 1.0),
                    feasibility_score=0.8,
                    source_component="interest_tracker",
                    topic_tags=[template.category.value],
                )
                signals.append(signal)
        
        except Exception as e:
            logger.error(f"[CURIOSITY] Personality hobby generation failed: {e}")
        
        return signals
    
    async def _calculate_intrinsic_reward(
        self,
        signal: IntrinsicSignal,
        user_id: str
    ) -> None:
        """Calculate intrinsic reward components for a signal.
        
        Phase 6.3: Advanced intrinsic motivation scoring.
        
        Args:
            signal: Signal to calculate reward for
            user_id: User ID for context
        """
        try:
            # Get World Model data if available
            world_model_data = signal.context.get("world_model_data", {})
            ams_data = signal.context.get("ams_data", {})
            
            # If we have World Model data, use it for precise calculations
            if world_model_data and self.world_model:
                rewards = self.reward_calculator.estimate_from_world_model_state(
                    topic=signal.topic,
                    world_model_data=world_model_data,
                    ams_data=ams_data
                )
                
                signal.prediction_error = rewards["prediction_error"]
                signal.information_gain = rewards["information_gain"]
                signal.empowerment = rewards["empowerment"]
                signal.long_term_value = rewards["long_term_value"]
            else:
                # Fallback: estimate from basic scores
                signal.prediction_error = signal.novelty_score
                signal.information_gain = signal.uncertainty_score
                signal.empowerment = signal.feasibility_score * signal.user_relevance_score
                signal.long_term_value = signal.user_relevance_score
            
            # Calculate combined intrinsic reward
            signal.intrinsic_reward = self.reward_calculator.calculate_intrinsic_reward(
                prediction_error=signal.prediction_error,
                information_gain=signal.information_gain,
                empowerment=signal.empowerment,
                long_term_value=signal.long_term_value
            )
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Failed to calculate intrinsic reward for {signal.signal_id}: {e}")
            # Fallback to basic score
            signal.intrinsic_reward = signal.total_score
    
    async def _score_and_filter_signals(
        self,
        signals: List[IntrinsicSignal],
        user_id: str,
    ) -> List[IntrinsicSignal]:
        """Score signals and apply three-gate filtering.
        
        Phase 6.3: Uses intrinsic reward for final scoring.
        
        From agency-component-curiosity-engine.md Section 2.3:
        1. Values/Ethics gate
        2. Emotion/relationship gate (uses personality)
        3. Resource gate (simple load check)
        
        Args:
            signals: Raw signals to score
            user_id: User ID for context
            
        Returns:
            Filtered and scored signals
        """
        filtered = []
        
        for signal in signals:
            try:
                # Calculate total score
                signal.total_score = await self._calculate_signal_score(signal, user_id)
                
                # Apply gates
                if not await self._passes_gates(signal, user_id):
                    continue
                
                # Map score to priority
                if signal.total_score >= 0.75:
                    signal.priority = "high"
                elif signal.total_score >= 0.50:
                    signal.priority = "normal"
                else:
                    signal.priority = "low"
                
                filtered.append(signal)
                
            except Exception as e:
                logger.error(f"[CURIOSITY] Failed to score signal {signal.signal_id}: {e}")
        
        return filtered
    
    async def _calculate_signal_score(
        self,
        signal: IntrinsicSignal,
        user_id: str,
    ) -> float:
        """Calculate weighted curiosity score.
        
        From agency-component-curiosity-engine.md Section 5:
        - Base weights: novelty 30%, relevance 25%, feasibility 20%, interest 25%
        - Personality modifiers:
          - High openness (+20% to novelty)
          - High conscientiousness (+10% to feasibility)
        
        Args:
            signal: Signal to score
            user_id: User ID for personality context
            
        Returns:
            Total score (0.0-1.0)
        """
        try:
            # Base weights
            weights = {
                'novelty': 0.30,
                'relevance': 0.25,
                'feasibility': 0.20,
                'interest': 0.25,
            }
            
            # Apply personality modifiers
            if self.personality:
                personality_context = await self.personality.get_personality_context(user_id)
                
                if personality_context.traits.openness > 0.7:
                    weights['novelty'] += 0.20
                    weights['interest'] -= 0.10
                
                if personality_context.traits.conscientiousness > 0.7:
                    weights['feasibility'] += 0.10
                    weights['novelty'] -= 0.10
            
            # Normalize weights
            total_weight = sum(weights.values())
            weights = {k: v / total_weight for k, v in weights.items()}
            
            # Calculate weighted score
            # Note: uncertainty_score is not used in base formula
            # It's used by detectors to generate signals
            score = (
                signal.novelty_score * weights['novelty'] +
                signal.user_relevance_score * weights['relevance'] +
                signal.feasibility_score * weights['feasibility'] +
                signal.user_relevance_score * weights['interest']  # Using relevance as proxy for interest
            )
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Failed to calculate score: {e}")
            return 0.5  # Default moderate score
    
    async def _passes_gates(self, signal: IntrinsicSignal, user_id: str) -> bool:
        """Check if signal passes three-gate system.
        
        Phase 6.3: Full implementation of three-gate filtering.
        
        From agency-component-curiosity-engine.md Section 2.3:
        1. Values/Ethics gate - Domain policies and sensitive topics
        2. Emotion/relationship gate - Timing appropriateness
        3. Resource gate - Intrinsic reward threshold
        
        Args:
            signal: Signal to check
            user_id: User ID for context
            
        Returns:
            True if signal passes all gates
        """
        try:
            # Gate 1: Values/Ethics
            # Check for sensitive topics that should not be explored without consent
            sensitive_keywords = ['health', 'finance', 'intimate', 'private', 'personal']
            topic_lower = signal.topic.lower()
            
            if any(keyword in topic_lower for keyword in sensitive_keywords):
                # Sensitive topics require higher relevance to proceed
                if signal.user_relevance_score < 0.7:
                    logger.debug(f"[CURIOSITY] Signal {signal.signal_id} blocked: sensitive topic with low relevance")
                    return False
            
            # Gate 2: Emotion/relationship
            if self.personality:
                personality_context = await self.personality.get_personality_context(user_id)
                
                # If relationship closeness is very low, reduce curiosity
                if personality_context.relationship.closeness < 0.3:
                    logger.debug(f"[CURIOSITY] Signal {signal.signal_id} blocked: low relationship closeness")
                    return False
                
                # If user is in distress, only allow supportive hobbies
                if personality_context.emotion.valence < -0.5:  # Negative emotion
                    if signal.signal_type != CuriosityType.HOBBY_PLAY:
                        logger.debug(f"[CURIOSITY] Signal {signal.signal_id} blocked: user in distress, only hobbies allowed")
                        return False
            
            # Gate 3: Resource (intrinsic reward threshold)
            # Use intrinsic_reward instead of total_score for Phase 6.3
            if signal.intrinsic_reward < 0.3:
                logger.debug(f"[CURIOSITY] Signal {signal.signal_id} blocked: low intrinsic reward ({signal.intrinsic_reward:.2f})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Gate check failed: {e}")
            return False
    
    def get_hobby_template(self, template_id: str) -> Optional[HobbyTemplate]:
        """Get hobby template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            HobbyTemplate if found, None otherwise
        """
        for template in self.hobby_templates:
            if template.template_id == template_id:
                return template
        return None
