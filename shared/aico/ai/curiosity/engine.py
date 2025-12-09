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
        hobby_templates: Optional[List[HobbyTemplate]] = None,
    ):
        """Initialize Curiosity Engine.
        
        Args:
            world_model: WorldModelService for querying knowledge
            personality_service: PersonalityService for personality-based scoring
            hobby_templates: List of hobby templates (uses defaults if None)
        """
        self.world_model = world_model
        self.personality = personality_service
        self.hobby_templates = hobby_templates or DEFAULT_HOBBY_TEMPLATES
        
        logger.info("[CURIOSITY] Engine initialized with %d hobby templates", len(self.hobby_templates))
    
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
            
            # Score and filter signals
            scored_signals = await self._score_and_filter_signals(signals, user_id)
            
            # Sort by total_score descending and limit
            scored_signals.sort(key=lambda s: s.total_score, reverse=True)
            result = scored_signals[:max_signals]
            
            logger.info(
                f"[CURIOSITY] Scan complete: {len(result)} signals (from {len(signals)} raw)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Failed to scan for opportunities: {e}")
            return []
    
    async def _detect_knowledge_gaps(self, user_id: str) -> List[IntrinsicSignal]:
        """Detect knowledge gaps in world model.
        
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
            # Phase 3 v1: Simple placeholder detection
            # TODO: Integrate with World Model uncertain areas query
            # TODO: Query AMS for topic coverage gaps
            
            if self.world_model:
                # Query for uncertain areas (placeholder in Phase 2)
                uncertain_areas = await self.world_model.query_uncertain_areas(user_id)
                
                for area in uncertain_areas:
                    signal = IntrinsicSignal(
                        signal_id=str(uuid.uuid4()),
                        user_id=user_id,
                        signal_type=CuriosityType.KNOWLEDGE_GAP,
                        topic=area.get("topic", "Unknown"),
                        description=f"Knowledge gap detected: {area.get('description', 'Missing information')}",
                        context={"area": area},
                        novelty_score=0.6,
                        uncertainty_score=0.8,
                        user_relevance_score=0.7,
                        feasibility_score=0.6,
                        source_component="gap_detector",
                    )
                    signals.append(signal)
            
            logger.debug(f"[CURIOSITY] Gap detector found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Gap detection failed: {e}")
        
        return signals
    
    async def _detect_anomalies(self, user_id: str) -> List[IntrinsicSignal]:
        """Detect anomalies and inconsistencies.
        
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
            # Phase 3 v1: Placeholder
            # TODO: Implement anomaly detection from World Model
            # TODO: Check for contradicting facts
            # TODO: Detect unusual interaction patterns
            
            logger.debug(f"[CURIOSITY] Anomaly detector found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Anomaly detection failed: {e}")
        
        return signals
    
    async def _track_interests(self, user_id: str) -> List[IntrinsicSignal]:
        """Track and predict user interests for hobby opportunities.
        
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
            # Phase 3 v1: Generate hobby opportunities from templates
            # TODO: Integrate with AMS to detect actual user interests
            # TODO: Track topic frequency and engagement
            
            # For now, generate one signal per hobby template
            # In production, this would be based on actual user behavior
            for template in self.hobby_templates:
                # Check personality fit
                if self.personality:
                    personality_context = await self.personality.get_personality_context(user_id)
                    
                    # Check if personality traits match template requirements
                    fits = True
                    for trait_name, required_level in template.personality_traits.items():
                        actual_level = getattr(personality_context.traits, trait_name, 0.5)
                        if actual_level < required_level:
                            fits = False
                            break
                    
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
                    },
                    novelty_score=0.5,
                    uncertainty_score=0.3,
                    user_relevance_score=0.6,
                    feasibility_score=0.8,
                    source_component="interest_tracker",
                    topic_tags=[template.category.value],
                )
                signals.append(signal)
            
            logger.debug(f"[CURIOSITY] Interest tracker found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"[CURIOSITY] Interest tracking failed: {e}")
        
        return signals
    
    async def _score_and_filter_signals(
        self,
        signals: List[IntrinsicSignal],
        user_id: str,
    ) -> List[IntrinsicSignal]:
        """Score signals and apply three-gate filtering.
        
        From agency-component-curiosity-engine.md Section 2.3:
        1. Values/Ethics gate (Phase 4 - placeholder)
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
        
        From agency-component-curiosity-engine.md Section 2.3:
        1. Values/Ethics gate - Domain policies (Phase 4 placeholder)
        2. Emotion/relationship gate - Timing appropriateness
        3. Resource gate - System load check
        
        Args:
            signal: Signal to check
            user_id: User ID for context
            
        Returns:
            True if signal passes all gates
        """
        try:
            # Gate 1: Values/Ethics (Phase 4 - always pass for now)
            # TODO: Implement domain policies
            # TODO: Check sensitive topics
            # TODO: Respect user preferences
            
            # Gate 2: Emotion/relationship (basic check)
            if self.personality:
                personality_context = await self.personality.get_personality_context(user_id)
                
                # If relationship closeness is very low, reduce curiosity
                if personality_context.relationship.closeness < 0.3:
                    return False
            
            # Gate 3: Resource (simple threshold for Phase 3)
            # TODO: Integrate with actual resource monitor
            # For now, just check if score is above minimum threshold
            if signal.total_score < 0.3:
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
