"""
Tests for Phase 6.3: Intrinsic Reward Calculator

Tests the advanced curiosity scoring algorithms including prediction error,
information gain, empowerment, and long-term value estimation.
"""

import pytest
from datetime import datetime, timedelta

from aico.ai.curiosity.intrinsic_reward import IntrinsicRewardCalculator


class TestIntrinsicRewardCalculator:
    """Test intrinsic reward calculations"""
    
    def test_initialization(self):
        """Test calculator initialization"""
        calc = IntrinsicRewardCalculator()
        
        assert calc.weights["prediction_error"] == 0.30
        assert calc.weights["information_gain"] == 0.25
        assert calc.weights["empowerment"] == 0.25
        assert calc.weights["long_term_value"] == 0.20
        assert sum(calc.weights.values()) == 1.0
    
    def test_prediction_error_identical_states(self):
        """Test prediction error with identical states"""
        calc = IntrinsicRewardCalculator()
        
        state = {"key1": "value1", "key2": 42, "key3": True}
        error = calc.calculate_prediction_error(state, state)
        
        # Identical states should have very low error
        assert 0.0 <= error <= 0.2
    
    def test_prediction_error_different_states(self):
        """Test prediction error with completely different states"""
        calc = IntrinsicRewardCalculator()
        
        expected = {"key1": "value1", "key2": 10}
        observed = {"key1": "value2", "key2": 100}
        
        error = calc.calculate_prediction_error(expected, observed)
        
        # Different states should have high error
        assert 0.5 <= error <= 1.0
    
    def test_prediction_error_missing_keys(self):
        """Test prediction error with missing keys"""
        calc = IntrinsicRewardCalculator()
        
        expected = {"key1": "value1", "key2": 42}
        observed = {"key1": "value1"}  # Missing key2
        
        error = calc.calculate_prediction_error(expected, observed)
        
        # Missing keys should contribute to error
        assert error > 0.3
    
    def test_prediction_error_numerical_difference(self):
        """Test prediction error with numerical values"""
        calc = IntrinsicRewardCalculator()
        
        expected = {"value": 100}
        observed = {"value": 150}
        
        error = calc.calculate_prediction_error(expected, observed)
        
        # 50% difference should give moderate error
        assert 0.3 <= error <= 0.7
    
    def test_information_gain_full_reduction(self):
        """Test information gain with full uncertainty reduction"""
        calc = IntrinsicRewardCalculator()
        
        gain = calc.calculate_information_gain(
            prior_uncertainty=1.0,
            posterior_uncertainty=0.0,
            topic_importance=1.0
        )
        
        # Full reduction with high importance = high gain
        assert gain == 1.0
    
    def test_information_gain_no_reduction(self):
        """Test information gain with no uncertainty reduction"""
        calc = IntrinsicRewardCalculator()
        
        gain = calc.calculate_information_gain(
            prior_uncertainty=0.5,
            posterior_uncertainty=0.5,
            topic_importance=1.0
        )
        
        # No reduction = no gain
        assert gain == 0.0
    
    def test_information_gain_partial_reduction(self):
        """Test information gain with partial reduction"""
        calc = IntrinsicRewardCalculator()
        
        gain = calc.calculate_information_gain(
            prior_uncertainty=0.8,
            posterior_uncertainty=0.3,
            topic_importance=0.5
        )
        
        # 0.5 reduction * 0.5 importance = 0.25
        assert 0.2 <= gain <= 0.3
    
    def test_information_gain_low_importance(self):
        """Test that low importance reduces gain"""
        calc = IntrinsicRewardCalculator()
        
        high_imp = calc.calculate_information_gain(1.0, 0.0, 1.0)
        low_imp = calc.calculate_information_gain(1.0, 0.0, 0.1)
        
        assert low_imp < high_imp
        assert low_imp < 0.2
    
    def test_empowerment_maximum(self):
        """Test empowerment with maximum values"""
        calc = IntrinsicRewardCalculator()
        
        empowerment = calc.calculate_empowerment(
            state_influence=1.0,
            action_diversity=1.0,
            reachability=1.0
        )
        
        # Max values should give high empowerment
        assert empowerment == 1.0
    
    def test_empowerment_minimum(self):
        """Test empowerment with minimum values"""
        calc = IntrinsicRewardCalculator()
        
        empowerment = calc.calculate_empowerment(
            state_influence=0.0,
            action_diversity=0.0,
            reachability=0.0
        )
        
        # Min values should give zero empowerment
        assert empowerment == 0.0
    
    def test_empowerment_moderate(self):
        """Test empowerment with moderate values"""
        calc = IntrinsicRewardCalculator()
        
        empowerment = calc.calculate_empowerment(
            state_influence=0.5,
            action_diversity=0.5,
            reachability=0.5
        )
        
        # sqrt(0.5 * 0.5 * 0.5) = sqrt(0.125) ≈ 0.35
        assert 0.3 <= empowerment <= 0.4
    
    def test_empowerment_low_reachability(self):
        """Test that low reachability reduces empowerment"""
        calc = IntrinsicRewardCalculator()
        
        high_reach = calc.calculate_empowerment(1.0, 1.0, 1.0)
        low_reach = calc.calculate_empowerment(1.0, 1.0, 0.1)
        
        assert low_reach < high_reach
        assert low_reach < 0.4
    
    def test_long_term_value_immediate_only(self):
        """Test long-term value with no future opportunities"""
        calc = IntrinsicRewardCalculator()
        
        value = calc.calculate_long_term_value(
            immediate_value=0.8,
            future_opportunities=0,
            decay_factor=0.9,
            horizon=5
        )
        
        # No future opportunities = just immediate value
        assert 0.7 <= value <= 0.9
    
    def test_long_term_value_with_future(self):
        """Test long-term value with future opportunities"""
        calc = IntrinsicRewardCalculator()
        
        no_future = calc.calculate_long_term_value(0.5, 0, 0.9, 5)
        with_future = calc.calculate_long_term_value(0.5, 10, 0.9, 5)
        
        # Future opportunities should increase value
        assert with_future > no_future
    
    def test_long_term_value_decay(self):
        """Test that decay factor affects long-term value"""
        calc = IntrinsicRewardCalculator()
        
        high_decay = calc.calculate_long_term_value(0.5, 10, 0.9, 5)
        low_decay = calc.calculate_long_term_value(0.5, 10, 0.5, 5)
        
        # Higher decay = more future value
        assert high_decay > low_decay
    
    def test_long_term_value_horizon(self):
        """Test that horizon affects long-term value"""
        calc = IntrinsicRewardCalculator()
        
        short_horizon = calc.calculate_long_term_value(0.5, 10, 0.9, 2)
        long_horizon = calc.calculate_long_term_value(0.5, 10, 0.9, 10)
        
        # Longer horizon = more future value
        assert long_horizon > short_horizon
    
    def test_calculate_intrinsic_reward_all_max(self):
        """Test combined reward with maximum values"""
        calc = IntrinsicRewardCalculator()
        
        reward = calc.calculate_intrinsic_reward(
            prediction_error=1.0,
            information_gain=1.0,
            empowerment=1.0,
            long_term_value=1.0
        )
        
        # All max should give 1.0
        assert reward == 1.0
    
    def test_calculate_intrinsic_reward_all_min(self):
        """Test combined reward with minimum values"""
        calc = IntrinsicRewardCalculator()
        
        reward = calc.calculate_intrinsic_reward(
            prediction_error=0.0,
            information_gain=0.0,
            empowerment=0.0,
            long_term_value=0.0
        )
        
        # All min should give 0.0
        assert reward == 0.0
    
    def test_calculate_intrinsic_reward_weighted(self):
        """Test that weights are applied correctly"""
        calc = IntrinsicRewardCalculator()
        
        # Only prediction error (30% weight)
        reward = calc.calculate_intrinsic_reward(1.0, 0.0, 0.0, 0.0)
        assert 0.25 <= reward <= 0.35
        
        # Only information gain (25% weight)
        reward = calc.calculate_intrinsic_reward(0.0, 1.0, 0.0, 0.0)
        assert 0.20 <= reward <= 0.30
        
        # Only empowerment (25% weight)
        reward = calc.calculate_intrinsic_reward(0.0, 0.0, 1.0, 0.0)
        assert 0.20 <= reward <= 0.30
        
        # Only long-term value (20% weight)
        reward = calc.calculate_intrinsic_reward(0.0, 0.0, 0.0, 1.0)
        assert 0.15 <= reward <= 0.25
    
    def test_calculate_intrinsic_reward_custom_weights(self):
        """Test custom weights"""
        calc = IntrinsicRewardCalculator()
        
        custom_weights = {
            "prediction_error": 0.5,
            "information_gain": 0.3,
            "empowerment": 0.1,
            "long_term_value": 0.1,
        }
        
        reward = calc.calculate_intrinsic_reward(
            prediction_error=1.0,
            information_gain=0.0,
            empowerment=0.0,
            long_term_value=0.0,
            custom_weights=custom_weights
        )
        
        # Should use custom 50% weight for prediction error
        assert 0.45 <= reward <= 0.55
    
    def test_estimate_from_world_model_state_high_uncertainty(self):
        """Test estimation from World Model with high uncertainty"""
        calc = IntrinsicRewardCalculator()
        
        world_model_data = {
            "uncertainty": 0.9,
            "fact_count": 2,
            "last_updated": datetime.utcnow() - timedelta(days=30),
            "contradictions": 3,
            "related_topics": ["topic1", "topic2", "topic3"],
        }
        
        rewards = calc.estimate_from_world_model_state(
            topic="test_topic",
            world_model_data=world_model_data
        )
        
        # High uncertainty should give high information gain
        assert rewards["information_gain"] > 0.5
        # Old data should give high prediction error
        assert rewards["prediction_error"] > 0.3
        # Related topics should give some empowerment
        assert rewards["empowerment"] > 0.0
    
    def test_estimate_from_world_model_state_well_known(self):
        """Test estimation from World Model with well-known topic"""
        calc = IntrinsicRewardCalculator()
        
        world_model_data = {
            "uncertainty": 0.1,
            "fact_count": 50,
            "last_updated": datetime.utcnow(),
            "contradictions": 0,
            "related_topics": ["topic1"],
        }
        
        rewards = calc.estimate_from_world_model_state(
            topic="test_topic",
            world_model_data=world_model_data
        )
        
        # Low uncertainty should give low information gain
        assert rewards["information_gain"] < 0.3
        # Recent data should give low prediction error
        assert rewards["prediction_error"] < 0.5
    
    def test_sigmoid_function(self):
        """Test sigmoid activation"""
        calc = IntrinsicRewardCalculator()
        
        # Sigmoid properties
        assert calc._sigmoid(0) == 0.5
        assert calc._sigmoid(-10) < 0.1
        assert calc._sigmoid(10) > 0.9
        assert 0 < calc._sigmoid(-5) < 0.5
        assert 0.5 < calc._sigmoid(5) < 1.0
    
    def test_calculate_staleness_fresh(self):
        """Test staleness calculation for fresh data"""
        calc = IntrinsicRewardCalculator()
        
        fresh = datetime.utcnow()
        staleness = calc._calculate_staleness(fresh)
        
        # Fresh data should have low staleness
        assert staleness < 0.3
    
    def test_calculate_staleness_old(self):
        """Test staleness calculation for old data"""
        calc = IntrinsicRewardCalculator()
        
        old = datetime.utcnow() - timedelta(days=60)
        staleness = calc._calculate_staleness(old)
        
        # Old data should have high staleness
        assert staleness > 0.7
    
    def test_calculate_staleness_none(self):
        """Test staleness with no last_updated"""
        calc = IntrinsicRewardCalculator()
        
        staleness = calc._calculate_staleness(None)
        
        # No data should be maximally stale
        assert staleness == 1.0
    
    def test_estimate_topic_importance_no_ams(self):
        """Test topic importance without AMS data"""
        calc = IntrinsicRewardCalculator()
        
        importance = calc._estimate_topic_importance("test", None)
        
        # Default moderate importance
        assert importance == 0.5
    
    def test_estimate_topic_importance_with_ams(self):
        """Test topic importance with AMS data"""
        calc = IntrinsicRewardCalculator()
        
        ams_data = {
            "mention_count": 20,
            "engagement_score": 0.8,
            "recency_score": 0.6,
        }
        
        importance = calc._estimate_topic_importance("test", ams_data)
        
        # High engagement and mentions should give high importance
        assert importance > 0.6
    
    def test_estimate_topic_importance_low_engagement(self):
        """Test topic importance with low engagement"""
        calc = IntrinsicRewardCalculator()
        
        ams_data = {
            "mention_count": 1,
            "engagement_score": 0.1,
            "recency_score": 0.1,
        }
        
        importance = calc._estimate_topic_importance("test", ams_data)
        
        # Low engagement should give low importance
        assert importance < 0.4
