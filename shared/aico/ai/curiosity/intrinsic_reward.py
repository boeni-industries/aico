"""
Intrinsic Reward Calculations for Curiosity Engine

Implements principled intrinsic motivation algorithms:
- Prediction error-based curiosity (surprise)
- Information gain (epistemic uncertainty reduction)
- Empowerment (ability to influence future states)
- Long-term value estimation

Phase 6.3: Advanced Curiosity Scoring
Based on research from:
- Pathak et al. (2017) - Curiosity-driven Exploration
- Burda et al. (2018) - Large-Scale Study of Curiosity-Driven Learning
- Mohamed & Rezende (2015) - Variational Information Maximisation
"""

import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, UTC


class IntrinsicRewardCalculator:
    """Calculates intrinsic motivation scores for curiosity signals"""
    
    def __init__(self):
        """Initialize intrinsic reward calculator"""
        # Weights for combining different reward components
        self.weights = {
            "prediction_error": 0.30,  # Surprise/novelty
            "information_gain": 0.25,  # Epistemic uncertainty reduction
            "empowerment": 0.25,       # State influence ability
            "long_term_value": 0.20,   # Expected future returns
        }
    
    def calculate_prediction_error(
        self,
        expected_state: Dict[str, Any],
        observed_state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate prediction error (surprise) between expected and observed states.
        
        Measures how much the observed state deviates from predictions.
        High prediction error indicates novelty and learning opportunity.
        
        Args:
            expected_state: What the World Model predicted
            observed_state: What was actually observed
            context: Additional context for weighting
            
        Returns:
            Prediction error score (0.0-1.0)
        """
        if not expected_state or not observed_state:
            return 0.0
        
        # Calculate normalized difference between states
        differences = []
        
        for key in set(expected_state.keys()) | set(observed_state.keys()):
            expected = expected_state.get(key)
            observed = observed_state.get(key)
            
            if expected is None or observed is None:
                # Missing key is maximum surprise
                differences.append(1.0)
            elif isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
                # Numerical difference (normalized)
                max_val = max(abs(expected), abs(observed), 1.0)
                diff = abs(expected - observed) / max_val
                differences.append(min(diff, 1.0))
            elif isinstance(expected, str) and isinstance(observed, str):
                # String difference (binary: match or not)
                differences.append(0.0 if expected == observed else 1.0)
            elif isinstance(expected, bool) and isinstance(observed, bool):
                # Boolean difference
                differences.append(0.0 if expected == observed else 1.0)
            else:
                # Type mismatch is high surprise
                differences.append(0.8)
        
        if not differences:
            return 0.0
        
        # Average prediction error across all fields
        avg_error = sum(differences) / len(differences)
        
        # Apply sigmoid to smooth the score
        return self._sigmoid(avg_error * 2 - 1)
    
    def calculate_information_gain(
        self,
        prior_uncertainty: float,
        posterior_uncertainty: float,
        topic_importance: float = 0.5
    ) -> float:
        """Calculate expected information gain (epistemic uncertainty reduction).
        
        Measures how much exploring this topic would reduce uncertainty.
        Based on KL divergence and entropy reduction.
        
        Args:
            prior_uncertainty: Current uncertainty about topic (0.0-1.0)
            posterior_uncertainty: Expected uncertainty after exploration (0.0-1.0)
            topic_importance: How important this topic is (0.0-1.0)
            
        Returns:
            Information gain score (0.0-1.0)
        """
        # Information gain is the reduction in uncertainty
        uncertainty_reduction = max(0.0, prior_uncertainty - posterior_uncertainty)
        
        # Weight by topic importance
        weighted_gain = uncertainty_reduction * topic_importance
        
        # Normalize to 0-1 range
        return min(weighted_gain, 1.0)
    
    def calculate_empowerment(
        self,
        state_influence: float,
        action_diversity: float,
        reachability: float = 0.5
    ) -> float:
        """Calculate empowerment (ability to influence future states).
        
        Measures how much control/influence AICO would gain by exploring this area.
        High empowerment means more options and control in future interactions.
        
        Args:
            state_influence: How much this affects future states (0.0-1.0)
            action_diversity: Number of new actions/options enabled (0.0-1.0)
            reachability: How accessible these states are (0.0-1.0)
            
        Returns:
            Empowerment score (0.0-1.0)
        """
        # Empowerment is the mutual information between actions and states
        # Approximated as: influence * diversity * reachability
        empowerment = state_influence * action_diversity * reachability
        
        # Apply square root to reduce extreme values
        return math.sqrt(empowerment)
    
    def calculate_long_term_value(
        self,
        immediate_value: float,
        future_opportunities: int,
        decay_factor: float = 0.9,
        horizon: int = 5
    ) -> float:
        """Calculate expected long-term value of exploring this topic.
        
        Estimates cumulative value over time, accounting for:
        - Immediate learning value
        - Future opportunities unlocked
        - Temporal discounting
        
        Args:
            immediate_value: Value of immediate exploration (0.0-1.0)
            future_opportunities: Number of future opportunities unlocked
            decay_factor: Temporal discount factor (0.0-1.0)
            horizon: Time horizon for value estimation
            
        Returns:
            Long-term value score (0.0-1.0)
        """
        # Immediate value
        total_value = immediate_value
        
        # Add discounted future value
        for t in range(1, horizon + 1):
            # Each future opportunity has diminishing value
            future_value = (future_opportunities / 10.0) * (decay_factor ** t)
            total_value += future_value
        
        # Normalize to 0-1 range
        max_possible = immediate_value + sum(
            (future_opportunities / 10.0) * (decay_factor ** t)
            for t in range(1, horizon + 1)
        )
        
        if max_possible > 0:
            return min(total_value / max_possible, 1.0)
        return immediate_value
    
    def calculate_intrinsic_reward(
        self,
        prediction_error: float,
        information_gain: float,
        empowerment: float,
        long_term_value: float,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Combine all intrinsic reward components into final score.
        
        Args:
            prediction_error: Prediction error score (0.0-1.0)
            information_gain: Information gain score (0.0-1.0)
            empowerment: Empowerment score (0.0-1.0)
            long_term_value: Long-term value score (0.0-1.0)
            custom_weights: Optional custom weights for components
            
        Returns:
            Combined intrinsic reward score (0.0-1.0)
        """
        weights = custom_weights or self.weights
        
        # Weighted sum of components
        reward = (
            prediction_error * weights["prediction_error"] +
            information_gain * weights["information_gain"] +
            empowerment * weights["empowerment"] +
            long_term_value * weights["long_term_value"]
        )
        
        # Ensure in valid range
        return max(0.0, min(reward, 1.0))
    
    def estimate_from_world_model_state(
        self,
        topic: str,
        world_model_data: Dict[str, Any],
        ams_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """Estimate all intrinsic reward components from World Model state.
        
        Args:
            topic: Topic being evaluated
            world_model_data: Data from World Model about this topic
            ams_data: Optional data from AMS about user interests
            
        Returns:
            Dictionary with all reward component scores
        """
        # Extract relevant metrics from World Model
        uncertainty = world_model_data.get("uncertainty", 0.5)
        fact_count = world_model_data.get("fact_count", 0)
        last_updated = world_model_data.get("last_updated")
        contradictions = world_model_data.get("contradictions", 0)
        related_topics = world_model_data.get("related_topics", [])
        
        # Calculate prediction error (based on contradictions and staleness)
        staleness = self._calculate_staleness(last_updated) if last_updated else 0.5
        pred_error = min((contradictions / 5.0) + staleness, 1.0)
        
        # Calculate information gain (based on current uncertainty)
        # High uncertainty means high potential gain
        expected_reduction = uncertainty * 0.7  # Assume 70% reduction possible
        info_gain = self.calculate_information_gain(
            prior_uncertainty=uncertainty,
            posterior_uncertainty=uncertainty - expected_reduction,
            topic_importance=self._estimate_topic_importance(topic, ams_data)
        )
        
        # Calculate empowerment (based on related topics and actions)
        state_influence = min(len(related_topics) / 10.0, 1.0)
        action_diversity = min(fact_count / 20.0, 1.0) if fact_count > 0 else 0.3
        empower = self.calculate_empowerment(
            state_influence=state_influence,
            action_diversity=action_diversity,
            reachability=0.7  # Assume moderate reachability
        )
        
        # Calculate long-term value
        immediate = 1.0 - (fact_count / 50.0) if fact_count < 50 else 0.3
        future_opps = len(related_topics)
        lt_value = self.calculate_long_term_value(
            immediate_value=immediate,
            future_opportunities=future_opps
        )
        
        return {
            "prediction_error": pred_error,
            "information_gain": info_gain,
            "empowerment": empower,
            "long_term_value": lt_value,
        }
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation function"""
        return 1.0 / (1.0 + math.exp(-x))
    
    def _calculate_staleness(self, last_updated: datetime) -> float:
        """Calculate staleness score based on last update time"""
        if not last_updated:
            return 1.0
        
        days_old = (datetime.now(UTC) - last_updated).days
        
        # Sigmoid curve: fresh (0 days) = 0.0, very old (30+ days) = 1.0
        return self._sigmoid((days_old - 15) / 5)
    
    def _estimate_topic_importance(
        self,
        topic: str,
        ams_data: Optional[Dict[str, Any]]
    ) -> float:
        """Estimate topic importance from AMS data"""
        if not ams_data:
            return 0.5  # Default moderate importance
        
        # Check mention frequency
        mentions = ams_data.get("mention_count", 0)
        engagement = ams_data.get("engagement_score", 0.5)
        recency = ams_data.get("recency_score", 0.5)
        
        # Combine signals
        importance = (
            min(mentions / 10.0, 0.4) +  # Frequency (max 40%)
            engagement * 0.4 +            # Engagement (40%)
            recency * 0.2                 # Recency (20%)
        )
        
        return min(importance, 1.0)
