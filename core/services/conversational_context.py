"""
Conversational Context Layer for C-CPM (Context-Aware Component Process Model)

Scientific Foundation:
- Dialogue State Tracking (Feng et al. 2024)
- Hypergraph Emotion Propagation (Van et al. 2025)

This module extends Scherer's CPM with conversation-aware context tracking,
enabling emotional episode detection and dialogue state management.

All detection uses language-agnostic sentiment patterns to ensure multilingual support.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class EpisodeType(Enum):
    """Emotional episode types"""
    STRESS = "stress"
    SUPPORT = "support"
    RESOLUTION = "resolution"


@dataclass
class EmotionalEpisode:
    """
    Tracks emotional episodes across conversation turns.
    
    Based on Van et al. (2025) - Hypergraph emotional propagation in conversations
    """
    type: EpisodeType
    valence_history: List[float]
    arousal_history: List[float]
    turn_count: int = 0
    
    def is_active(self) -> bool:
        """Episode is active if it has recent turns"""
        return self.turn_count < 10  # Max 10 turns per episode
    
    def should_resolve(self, current_valence: float) -> bool:
        """
        Detect if stress episode should resolve.
        
        Resolution: SUSTAINED positive valence after sustained negative period
        
        Scientific basis:
        - Lazarus & Folkman (1984): Resolution requires sustained positive reappraisal
        - Gross (2015): Emotion regulation is a process, not an event
        
        Universal criteria:
        - Established stress: 2+ negative turns at start
        - Sustained positive: 2+ consecutive positive turns (including current)
        - Consistent threshold: 0.5 for all positive turns (strong positive)
        """
        if self.type != EpisodeType.STRESS:
            return False
        
        # Need at least 3 turns in history (2 negative + 1 positive minimum)
        if len(self.valence_history) < 3:
            return False
        
        # Criterion 1: Early stress established (first 2 turns negative)
        early_negative = all(v < -0.2 for v in self.valence_history[:2])
        
        # Criterion 2: Sustained positive (last turn + current both strongly positive)
        # Note: current_valence not yet in history, so check history[-1] + current
        last_turn_positive = self.valence_history[-1] > 0.5
        current_strongly_positive = current_valence > 0.5
        
        return early_negative and last_turn_positive and current_strongly_positive


class ConversationalContext:
    """
    Manages conversational context for emotion appraisal.
    
    Scientific Foundation:
    - Dialogue State Tracking (Feng et al. 2024)
    - Episode-aware emotion modeling (Van et al. 2025)
    
    Tracks emotional episodes across conversation turns using sentiment patterns.
    """
    
    def __init__(self, history_size: int = 5):
        self.history_size = history_size
        self.turn_history: List[Dict[str, Any]] = []
        self.current_episode: Optional[EmotionalEpisode] = None
        self.turn_count: int = 0
    
    def update(self, 
               message_text: str,
               sentiment_valence: float,
               sentiment_arousal: float,
               relevance: float) -> None:
        """
        Update conversational context with new turn.
        
        Args:
            message_text: User message
            sentiment_valence: Sentiment valence (-1 to 1)
            sentiment_arousal: Sentiment arousal (0 to 1)
            relevance: Appraisal relevance (0 to 1)
        """
        self.turn_count += 1
        
        # Add to history
        turn_data = {
            'turn': self.turn_count,
            'text': message_text,
            'valence': sentiment_valence,
            'arousal': sentiment_arousal,
            'relevance': relevance,
        }
        self.turn_history.append(turn_data)
        
        # Maintain history size
        if len(self.turn_history) > self.history_size:
            self.turn_history.pop(0)
        
        # Update episode tracking
        self._update_episode(message_text, sentiment_valence, sentiment_arousal)
    
    def _update_episode(self, 
                       message_text: str,
                       valence: float,
                       arousal: float) -> None:
        """
        Update emotional episode tracking using LANGUAGE-AGNOSTIC sentiment patterns.
        
        Based on Van et al. (2025) - Hypergraph emotional propagation
        
        Resolution detection: Positive valence after sustained negative period
        (works in all languages via sentiment analysis)
        """
        # Check if current episode should resolve (language-agnostic)
        if self.current_episode and self.current_episode.should_resolve(valence):
            self.current_episode = EmotionalEpisode(
                type=EpisodeType.RESOLUTION,
                valence_history=[valence],
                arousal_history=[arousal],
            )
            return
        
        # Start new stress episode
        if valence < -0.3 and arousal > 0.4:
            if not self.current_episode or self.current_episode.type != EpisodeType.STRESS:
                self.current_episode = EmotionalEpisode(
                    type=EpisodeType.STRESS,
                    valence_history=[valence],
                    arousal_history=[arousal],
                )
            else:
                # Continue stress episode
                self.current_episode.valence_history.append(valence)
                self.current_episode.arousal_history.append(arousal)
                self.current_episode.turn_count += 1
        
        # Track valence/arousal even when not in active stress (for resolution detection)
        elif self.current_episode:
            # Append current turn to history for resolution detection
            self.current_episode.valence_history.append(valence)
            self.current_episode.arousal_history.append(arousal)
            self.current_episode.turn_count += 1
            
            # End episode if inactive
            if not self.current_episode.is_active():
                self.current_episode = None
    
    def adjust_relevance(self, base_relevance: float, message_text: str) -> float:
        """
        Adjust relevance based on emotional episode context.
        
        Scientific basis:
        - Stress episodes boost relevance (continued concern)
        """
        adjusted = base_relevance
        
        # Boost relevance during stress episodes
        if self.current_episode and self.current_episode.type == EpisodeType.STRESS:
            adjusted = min(adjusted + 0.15, 1.0)  # Continued stress is highly relevant
        
        return adjusted
    
    def adjust_goal_impact(self, base_impact: str, sentiment_valence: float) -> str:
        """
        Adjust goal impact based on episode context.
        
        Scientific basis: Episode-aware emotion modeling (Van et al. 2025)
        """
        # Resolution detected
        if self.current_episode and self.current_episode.type == EpisodeType.RESOLUTION:
            return "resolution_opportunity"
        
        # During stress episode, maintain supportive stance
        if self.current_episode and self.current_episode.type == EpisodeType.STRESS:
            # Even positive sentiment during stress should maintain support
            if sentiment_valence > 0.0 and base_impact == "engaging_opportunity":
                return "supportive_opportunity"  # Stay supportive
        
        return base_impact
    
    def adjust_social_appropriateness(self, base_social: str) -> str:
        """
        Adjust social appropriateness based on episode context.
        
        Scientific basis: Episode-aware emotion modeling (Van et al. 2025)
        """
        # Resolution phase → calm response
        if self.current_episode and self.current_episode.type == EpisodeType.RESOLUTION:
            return "calm_resolution"
        
        return base_social
    
    def in_stress_episode(self) -> bool:
        """Check if currently in stress episode"""
        return (self.current_episode is not None and 
                self.current_episode.type == EpisodeType.STRESS and
                self.current_episode.is_active())
    
    def in_resolution_phase(self) -> bool:
        """Check if in resolution phase"""
        return (self.current_episode is not None and
                self.current_episode.type == EpisodeType.RESOLUTION)
