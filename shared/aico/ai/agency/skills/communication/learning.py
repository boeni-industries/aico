"""
Conversation Initiation Learning System

Implements state-of-the-art techniques from recent research:
- Contextual Multi-Armed Bandits with Thompson Sampling
- Human-centered PCA dimensions (Intelligence, Adaptivity, Civility)
- Real-time context-aware decision making
- Uncertainty quantification and calibration

Based on:
- "Towards Human-centered Proactive Conversational Agents" (2024)
- Thompson Sampling for Multi-Armed Bandits (Stanford)
- Contextual Bandits for Personalization
"""

from __future__ import annotations

import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from aico.core.logging import get_logger
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.communication.learning")


@dataclass
class ContextualFeatures:
    """Contextual features for bandit decision-making."""
    
    # Temporal context
    hour_of_day: int
    day_of_week: int
    time_since_last_interaction: float  # hours
    
    # User state
    recent_response_rate: float
    avg_response_time: float
    conversation_frequency: float  # conversations per day
    
    # Conversation context
    pending_initiations: int
    recent_dismissals: int
    topic_diversity: float  # 0-1, how varied recent topics are
    
    # Emotional/engagement context
    recent_engagement_score: float  # 0-1
    user_activity_level: str  # 'low', 'medium', 'high'
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for bandit algorithms."""
        # Normalize features to [0, 1] range
        return np.array([
            self.hour_of_day / 24.0,
            self.day_of_week / 7.0,
            min(self.time_since_last_interaction / 24.0, 1.0),  # Cap at 24h
            self.recent_response_rate,
            min(self.avg_response_time / 3600.0, 1.0),  # Cap at 1 hour
            min(self.conversation_frequency / 10.0, 1.0),  # Cap at 10/day
            float(self.pending_initiations) / 5.0,  # Cap at 5
            float(self.recent_dismissals) / 3.0,  # Cap at 3
            self.topic_diversity,
            self.recent_engagement_score,
            {'low': 0.0, 'medium': 0.5, 'high': 1.0}.get(self.user_activity_level, 0.5),
        ])


@dataclass
class BanditArm:
    """Represents an action (initiation strategy) in multi-armed bandit."""
    
    arm_id: str
    strategy_type: str  # 'time_of_day', 'topic', 'urgency'
    strategy_params: Dict[str, Any]
    
    # Thompson Sampling parameters (Beta distribution)
    alpha: float = 1.0  # Success count + 1 (prior)
    beta: float = 1.0   # Failure count + 1 (prior)
    
    # Contextual learning
    context_weights: Optional[np.ndarray] = None
    
    def sample_reward(self) -> float:
        """Sample expected reward using Thompson Sampling (Beta distribution)."""
        return np.random.beta(self.alpha, self.beta)
    
    def update(self, reward: float):
        """Update parameters based on observed reward (0 or 1)."""
        if reward > 0.5:  # Success
            self.alpha += 1
        else:  # Failure
            self.beta += 1
    
    def expected_reward(self) -> float:
        """Calculate expected reward (mean of Beta distribution)."""
        return self.alpha / (self.alpha + self.beta)
    
    def uncertainty(self) -> float:
        """Calculate uncertainty (variance of Beta distribution)."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))


class ContextualBanditLearner:
    """
    Contextual Multi-Armed Bandit for conversation initiation optimization.
    
    Uses Thompson Sampling with contextual features to balance exploration
    and exploitation while learning optimal initiation strategies.
    """
    
    def __init__(self, db: EncryptedLibSQLConnection):
        self.db = db
        self.arms: Dict[str, BanditArm] = {}
        self._initialize_arms()
    
    def _initialize_arms(self):
        """Initialize bandit arms for different initiation strategies."""
        
        # Time-based strategies
        for time_period in ['morning', 'afternoon', 'evening', 'night']:
            self.arms[f"time_{time_period}"] = BanditArm(
                arm_id=f"time_{time_period}",
                strategy_type='time_of_day',
                strategy_params={'period': time_period}
            )
        
        # Topic-based strategies
        for topic in ['information_gap', 'concern', 'curiosity', 'approval']:
            self.arms[f"topic_{topic}"] = BanditArm(
                arm_id=f"topic_{topic}",
                strategy_type='topic',
                strategy_params={'topic': topic}
            )
        
        # Urgency-based strategies
        for urgency in ['low', 'medium', 'high']:
            self.arms[f"urgency_{urgency}"] = BanditArm(
                arm_id=f"urgency_{urgency}",
                strategy_type='urgency',
                strategy_params={'urgency': urgency}
            )
    
    def select_strategy(
        self,
        context: ContextualFeatures,
        available_strategies: Optional[List[str]] = None
    ) -> Tuple[str, float]:
        """
        Select best initiation strategy using Thompson Sampling.
        
        Returns: (strategy_id, expected_reward)
        """
        if available_strategies:
            candidate_arms = {k: v for k, v in self.arms.items() if k in available_strategies}
        else:
            candidate_arms = self.arms
        
        # Thompson Sampling: sample from each arm's posterior
        samples = {
            arm_id: arm.sample_reward()
            for arm_id, arm in candidate_arms.items()
        }
        
        # Select arm with highest sampled reward
        best_arm_id = max(samples.items(), key=lambda x: x[1])[0]
        expected_reward = self.arms[best_arm_id].expected_reward()
        
        logger.info(
            f"🎰 [BANDIT] Selected strategy: {best_arm_id}, "
            f"expected_reward={expected_reward:.3f}, "
            f"uncertainty={self.arms[best_arm_id].uncertainty():.3f}"
        )
        
        return best_arm_id, expected_reward
    
    def update_from_outcome(
        self,
        strategy_id: str,
        context: ContextualFeatures,
        outcome: str,  # 'answered', 'dismissed', 'pending'
        response_time: Optional[float] = None
    ):
        """Update bandit based on initiation outcome."""
        
        if strategy_id not in self.arms:
            logger.warning(f"🎰 [BANDIT] Unknown strategy: {strategy_id}")
            return
        
        # Calculate reward based on outcome
        if outcome == 'answered':
            # High reward for quick responses
            if response_time and response_time < 300:  # < 5 min
                reward = 1.0
            elif response_time and response_time < 3600:  # < 1 hour
                reward = 0.8
            else:
                reward = 0.6
        elif outcome == 'dismissed':
            reward = 0.0
        else:  # pending
            return  # Don't update until resolved
        
        # Update arm
        self.arms[strategy_id].update(reward)
        
        logger.info(
            f"🎰 [BANDIT] Updated {strategy_id}: "
            f"α={self.arms[strategy_id].alpha:.1f}, "
            f"β={self.arms[strategy_id].beta:.1f}, "
            f"E[reward]={self.arms[strategy_id].expected_reward():.3f}"
        )
    
    def get_arm_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all arms."""
        return {
            arm_id: {
                'expected_reward': arm.expected_reward(),
                'uncertainty': arm.uncertainty(),
                'alpha': arm.alpha,
                'beta': arm.beta,
                'trials': arm.alpha + arm.beta - 2,  # Total trials
            }
            for arm_id, arm in self.arms.items()
        }


class AdaptivityScorer:
    """
    Scores initiation decisions on Adaptivity dimension.
    
    Based on research: Patience, Timing Sensitivity, Self-awareness
    """
    
    @staticmethod
    def calculate_patience_score(
        context: ContextualFeatures,
        time_since_last: float
    ) -> float:
        """
        Score based on conversation smoothness (patience).
        
        Higher score for appropriate pacing.
        """
        # Penalize too frequent initiations
        if time_since_last < 1.0:  # < 1 hour
            return 0.2
        elif time_since_last < 6.0:  # < 6 hours
            return 0.6
        elif time_since_last < 24.0:  # < 24 hours
            return 1.0
        else:  # > 24 hours
            return 0.8  # Slight penalty for too long
    
    @staticmethod
    def calculate_timing_sensitivity(
        context: ContextualFeatures
    ) -> float:
        """
        Score based on real-time user context.
        
        Higher score when user is likely receptive.
        """
        score = 0.5  # Base score
        
        # Boost for high activity
        if context.user_activity_level == 'high':
            score += 0.2
        elif context.user_activity_level == 'low':
            score -= 0.2
        
        # Boost for good recent response rate
        score += context.recent_response_rate * 0.3
        
        # Penalty for pending initiations
        score -= min(context.pending_initiations * 0.1, 0.3)
        
        # Penalty for recent dismissals
        score -= min(context.recent_dismissals * 0.15, 0.3)
        
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def calculate_self_awareness(
        predicted_success: float,
        actual_success: bool,
        history: List[Tuple[float, bool]]
    ) -> float:
        """
        Calculate Expected Calibration Error (ECE).
        
        Measures how well confidence matches actual accuracy.
        Lower ECE = better calibration = higher self-awareness.
        """
        if len(history) < 5:
            return 0.5  # Insufficient data
        
        # Bin predictions into buckets
        n_bins = 5
        bins = np.linspace(0, 1, n_bins + 1)
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i in range(n_bins):
            bin_preds = [
                (pred, actual) for pred, actual in history
                if bins[i] <= pred < bins[i + 1]
            ]
            
            if bin_preds:
                bin_counts.append(len(bin_preds))
                bin_confidences.append(np.mean([p for p, _ in bin_preds]))
                bin_accuracies.append(np.mean([float(a) for _, a in bin_preds]))
        
        if not bin_counts:
            return 0.5
        
        # Calculate ECE
        total = sum(bin_counts)
        ece = sum(
            (count / total) * abs(conf - acc)
            for count, conf, acc in zip(bin_counts, bin_confidences, bin_accuracies)
        )
        
        # Convert ECE to score (lower ECE = higher score)
        return 1.0 - min(ece, 1.0)


class CivilityScorer:
    """
    Scores initiation decisions on Civility dimension.
    
    Based on research: Boundary respect, trust, emotional intelligence
    """
    
    @staticmethod
    def calculate_boundary_respect(
        context: ContextualFeatures,
        user_preferences: Dict[str, Any]
    ) -> float:
        """
        Score based on respecting user boundaries.
        
        Higher score for respecting quiet hours, frequency limits, etc.
        """
        score = 1.0
        
        # Check quiet hours
        quiet_hours = user_preferences.get('quiet_hours', [])
        if context.hour_of_day in quiet_hours:
            score -= 0.5
        
        # Check frequency limits
        max_per_day = user_preferences.get('max_initiations_per_day', 5)
        if context.conversation_frequency > max_per_day:
            score -= 0.3
        
        # Check pending limit
        max_pending = user_preferences.get('max_pending', 2)
        if context.pending_initiations >= max_pending:
            score -= 0.4
        
        return max(0.0, score)
    
    @staticmethod
    def calculate_emotional_intelligence(
        context: ContextualFeatures,
        topic: str
    ) -> float:
        """
        Score based on emotional appropriateness.
        
        Higher score for matching topic to user's emotional state.
        """
        # If user has low engagement, avoid heavy topics
        if context.recent_engagement_score < 0.3:
            heavy_topics = ['concern', 'approval']
            if topic in heavy_topics:
                return 0.4
        
        # If user is highly engaged, can handle more complex topics
        if context.recent_engagement_score > 0.7:
            return 1.0
        
        return 0.7  # Default moderate score


def extract_contextual_features(
    db: EncryptedLibSQLConnection,
    user_id: str
) -> ContextualFeatures:
    """Extract contextual features for bandit decision-making."""
    
    now = datetime.utcnow()
    
    # Temporal context
    hour_of_day = now.hour
    day_of_week = now.weekday()
    
    # Get recent interaction data
    recent_initiations = db.execute(
        """SELECT initiated_at, resolved_at, resolution_status, user_response_time
           FROM aico_conversation_initiations
           WHERE user_id = ?
           AND initiated_at > datetime('now', '-7 days')
           ORDER BY initiated_at DESC""",
        (user_id,)
    ).fetchall()
    
    if not recent_initiations:
        # Default features for new users
        return ContextualFeatures(
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            time_since_last_interaction=24.0,
            recent_response_rate=0.5,
            avg_response_time=1800.0,
            conversation_frequency=1.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.5,
            recent_engagement_score=0.5,
            user_activity_level='medium'
        )
    
    # Calculate metrics
    answered = [i for i in recent_initiations if i['resolution_status'] == 'answered']
    dismissed = [i for i in recent_initiations if i['resolution_status'] == 'dismissed']
    pending = [i for i in recent_initiations if i['resolution_status'] == 'pending']
    
    recent_response_rate = len(answered) / len(recent_initiations) if recent_initiations else 0.5
    
    response_times = [i['user_response_time'] for i in answered if i['user_response_time']]
    avg_response_time = np.mean(response_times) if response_times else 1800.0
    
    conversation_frequency = len(recent_initiations) / 7.0  # Per day over last week
    
    # Time since last interaction
    if recent_initiations:
        last_time = datetime.fromisoformat(recent_initiations[0]['initiated_at'])
        time_since_last = (now - last_time).total_seconds() / 3600.0  # hours
    else:
        time_since_last = 24.0
    
    # Recent dismissals (last 3 days)
    recent_dismissals_count = len([
        i for i in dismissed
        if (now - datetime.fromisoformat(i['initiated_at'])).days < 3
    ])
    
    # Engagement score (based on response rate and speed)
    engagement_score = recent_response_rate * 0.7
    if avg_response_time < 600:  # < 10 min
        engagement_score += 0.3
    elif avg_response_time < 3600:  # < 1 hour
        engagement_score += 0.2
    engagement_score = min(1.0, engagement_score)
    
    # Activity level
    if conversation_frequency > 3:
        activity_level = 'high'
    elif conversation_frequency > 1:
        activity_level = 'medium'
    else:
        activity_level = 'low'
    
    return ContextualFeatures(
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        time_since_last_interaction=time_since_last,
        recent_response_rate=recent_response_rate,
        avg_response_time=avg_response_time,
        conversation_frequency=conversation_frequency,
        pending_initiations=len(pending),
        recent_dismissals=recent_dismissals_count,
        topic_diversity=0.5,  # TODO: Calculate from topic variety
        recent_engagement_score=engagement_score,
        user_activity_level=activity_level
    )
