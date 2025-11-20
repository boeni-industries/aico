#!/usr/bin/env python3
"""
Focused Unit Tests for Emotion Engine Hypotheses

Tests isolated mechanisms without full conversation round-trips.
Each test validates ONE hypothesis from TEST_PROTOCOL.md

Run with: uv run pytest scripts/emotion/test_emotion_units.py -v
Or specific test: uv run pytest scripts/emotion/test_emotion_units.py::TestH2_ArousalBoostTrigger -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.emotion_engine import EmotionEngine, AppraisalResult, EmotionLabel


@pytest.fixture(scope="session", autouse=True)
def mock_logger():
    """Mock the logger globally to avoid initialization complexity"""
    with patch('backend.core.service_container.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def emotion_engine():
    """Create a minimal EmotionEngine for testing internal methods"""
    # Create mock container
    mock_container = Mock()
    mock_container.get.return_value = None
    
    # Initialize engine with mocks
    engine = EmotionEngine(name="test_engine", container=mock_container)
    
    # Set required config manually (bypass async start())
    engine.regulation_strength = 0.3
    engine.threat_arousal_boost = 0.25
    engine.inertia_weight = 0.4
    engine.inertia_reactivity = 0.6
    engine.inertia_decay = 0.1
    engine.turns_since_state_change = 0
    
    # Set initial state to calm (baseline)
    from datetime import datetime
    from backend.services.emotion_engine import EmotionalState
    engine.current_state = EmotionalState(
        timestamp=datetime.now(),
        cognitive_component=AppraisalResult(
            relevance=0.0,
            goal_impact="neutral",
            coping_capability="moderate",
            social_appropriateness="neutral_response"
        ),
        physiological_arousal=0.3,
        motivational_tendency="neutral",
        motor_expression="relaxed",
        subjective_feeling=EmotionLabel.CALM,
        mood_valence=0.0,
        mood_arousal=0.3,
        intensity=0.0
    )
    
    return engine


class TestH1_SentimentValenceMapping:
    """H1: Sentiment → Valence Mapping (VALIDATED - Regression Tests)"""
    
    def test_empathy_negative_to_positive_conversion(self, emotion_engine):
        """LOCKED: Negative user sentiment converts to positive AI concern"""
        engine = emotion_engine
        
        # Arrange: User expresses stress (negative sentiment)
        sentiment_data = {"valence": -0.70, "confidence": 0.49}
        appraisal = AppraisalResult(
            relevance=0.70,
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        
        # Act: Generate emotion state
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # Assert: AI should have POSITIVE concern valence
        assert state.mood_valence > 0.2, f"Expected positive concern, got valence={state.mood_valence}"
        assert state.mood_valence < 0.5, f"Concern should be moderate, got valence={state.mood_valence}"
        
        # Expected: abs(-0.70) * 0.5 = 0.35 (before inertia)
        # After inertia from calm (v=0.0): 0.0*0.4 + 0.35*0.6 ≈ 0.21-0.38 range
    
    def test_empathy_positive_gentle_response(self, emotion_engine):
        """Positive user sentiment in empathy context gets gentle scaling"""
        engine = emotion_engine
        
        sentiment_data = {"valence": 0.70, "confidence": 0.49}
        appraisal = AppraisalResult(
            relevance=0.70,
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # Expected: 0.70 * 0.6 = 0.42 target (before inertia)
        assert state.mood_valence > 0.2, f"Should maintain positive valence, got {state.mood_valence}"


class TestH2_ArousalBoostTrigger:
    """H2: Arousal Boost Trigger (BROKEN - Under Investigation)"""
    
    def test_arousal_boost_triggers_on_high_relevance_negative(self, emotion_engine):
        """Arousal boost should trigger for high-relevance negative sentiment"""
        engine = emotion_engine
        
        # Arrange: High relevance + negative sentiment + sufficient confidence
        sentiment_data = {"valence": -0.70, "confidence": 0.49}
        appraisal = AppraisalResult(
            relevance=0.70,  # > 0.65 ✓
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        
        # Act
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # Assert: Arousal should be boosted by 25%
        # Base arousal for empathy with rel>0.65: 0.65
        # After regulation (0.3 strength): 0.65 * (1 - 0.3*0.3) = 0.65 * 0.91 = 0.59
        # After boost: 0.59 * 1.25 = 0.74
        # After inertia from calm (a=0.3): 0.3*0.4 + 0.74*0.6 = 0.56
        
        expected_min = 0.65  # Should be boosted above base
        assert state.mood_arousal >= expected_min, \
            f"Arousal boost should trigger. Expected >={expected_min}, got {state.mood_arousal}"
    
    def test_arousal_boost_not_triggered_low_confidence(self, emotion_engine):
        """Arousal boost should NOT trigger if confidence too low"""
        engine = emotion_engine
        
        sentiment_data = {"valence": -0.70, "confidence": 0.35}  # Below 0.4 threshold
        appraisal = AppraisalResult(
            relevance=0.70,
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # Should NOT have boost
        # Base: 0.65, regulated: 0.59, no boost, with inertia: ~0.47
        assert state.mood_arousal < 0.65, \
            f"Arousal boost should NOT trigger with low confidence. Got {state.mood_arousal}"


class TestH3_EmotionLabelAssignment:
    """H3: Emotion Label Assignment (INCORRECT - Needs Context Awareness)"""
    
    def test_empathy_context_assigns_warm_concern(self, emotion_engine):
        """Empathetic response with moderate valence/high arousal should be warm_concern"""
        engine = emotion_engine
        
        sentiment_data = {"valence": -0.70, "confidence": 0.49}
        appraisal = AppraisalResult(
            relevance=0.70,
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # Assert: Should map to warm_concern, not curious
        # Current bug: v=0.38, a=0.72 → "curious" (wrong)
        # Expected: "warm_concern" (empathetic context)
        
        assert state.subjective_feeling.value == "warm_concern", \
            f"Empathetic response should be warm_concern, got {state.subjective_feeling.value}"
    
    def test_positive_engagement_assigns_playful(self, emotion_engine):
        """Positive engagement with high valence should be playful"""
        engine = emotion_engine
        
        sentiment_data = {"valence": 0.70, "confidence": 0.42}
        appraisal = AppraisalResult(
            relevance=0.65,
            goal_impact="engaging_opportunity",
            coping_capability="high_capability",
            social_appropriateness="warm_engagement"
        )
        
        state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
        
        # After savoring: v≈0.97, a≈0.76
        # After inertia: v≈0.58, a≈0.58
        # Should map to "playful" (v>0.5, a>0.5)
        
        assert state.subjective_feeling.value in ["playful", "curious"], \
            f"Positive engagement should be playful/curious, got {state.subjective_feeling.value}"


class TestH4_ValenceDecay:
    """H4: Valence Decay (FIXED - Minimum Valence Floor)"""
    
    def test_neutral_inputs_maintain_minimum_valence(self, emotion_engine):
        """Neutral inputs should not decay valence to near-zero in positive contexts"""
        engine = emotion_engine
        
        # First, establish a positive emotional state
        positive_sentiment = {"valence": 0.70, "confidence": 0.49}
        positive_appraisal = AppraisalResult(
            relevance=0.70,
            goal_impact="supportive_opportunity",
            coping_capability="high_capability",
            social_appropriateness="empathetic_response"
        )
        state = engine._generate_cpm_emotional_state(positive_appraisal, positive_sentiment)
        assert state.mood_valence > 0.2, "Should start with positive valence"
        
        # Set this as previous state so inertia blending occurs
        engine.previous_state = state
        
        # Now simulate neutral turns in supportive context
        for i in range(3):
            sentiment_data = {"valence": 0.0, "confidence": 0.81}
            appraisal = AppraisalResult(
                relevance=0.89,
                goal_impact="supportive_opportunity",  # Still supportive context
                coping_capability="moderate",
                social_appropriateness="neutral_response"
            )
            
            state = engine._generate_cpm_emotional_state(appraisal, sentiment_data)
            print(f"Turn {i+1}: valence={state.mood_valence:.2f}")
        
        # Should maintain minimum valence floor (0.15)
        assert state.mood_valence >= 0.15, \
            f"Valence should not decay below floor (0.15), got {state.mood_valence}"


if __name__ == "__main__":
    # Run with: uv run pytest scripts/emotion/test_emotion_units.py -v
    # Or specific: uv run pytest scripts/emotion/test_emotion_units.py::TestH2_ArousalBoostTrigger -v
    
    print("Please run with: uv run pytest scripts/emotion/test_emotion_units.py -v")
    print("This ensures proper .venv activation and dependencies")
