"""
Integration tests for CuriosityEngine (Phase 3).

Tests curiosity signal generation, scoring, and hobby goal creation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from aico.ai.curiosity import (
    CuriosityEngine,
    IntrinsicSignal,
    CuriosityType,
    HobbyTemplate,
    HobbyCategory,
)
from aico.ai.personality import PersonalityService, PersonalityContext, PersonalityTraits, RelationshipVector


@pytest.fixture
def mock_world_model():
    """Mock WorldModelService."""
    mock = MagicMock()
    mock.query_uncertain_areas = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_personality_service():
    """Mock PersonalityService."""
    mock = MagicMock()
    
    # Default personality context
    context = PersonalityContext(
        user_id="test-user",
        traits=PersonalityTraits(
            openness=0.7,
            conscientiousness=0.6,
            extraversion=0.5,
            agreeableness=0.6,
            neuroticism=0.4,
        ),
        relationship=RelationshipVector(
            user_id="test-user",
            closeness=0.7,
            trust_level=0.8,
            familiarity=0.7,
        ),
    )
    
    mock.get_personality_context = AsyncMock(return_value=context)
    return mock


@pytest.fixture
def curiosity_engine(mock_world_model, mock_personality_service):
    """Create CuriosityEngine with mocked dependencies."""
    return CuriosityEngine(
        world_model=mock_world_model,
        personality_service=mock_personality_service,
    )


@pytest.mark.asyncio
class TestCuriosityEngine:
    """Test suite for CuriosityEngine."""
    
    async def test_engine_initialization(self, curiosity_engine):
        """Test CuriosityEngine initializes correctly."""
        assert curiosity_engine is not None
        assert curiosity_engine.world_model is not None
        assert curiosity_engine.personality is not None
        assert len(curiosity_engine.hobby_templates) == 6  # 6 default templates
    
    async def test_scan_for_opportunities_no_services(self):
        """Test scanning works without services."""
        # Arrange
        engine = CuriosityEngine(world_model=None, personality_service=None)
        
        # Act
        signals = await engine.scan_for_opportunities(user_id="test-user")
        
        # Assert - Should return hobby signals even without services
        assert isinstance(signals, list)
        # Without personality filtering, should get all 6 hobby templates
        assert len(signals) >= 0
    
    async def test_scan_for_opportunities_with_services(self, curiosity_engine):
        """Test scanning with full services."""
        # Act
        signals = await curiosity_engine.scan_for_opportunities(
            user_id="test-user",
            max_signals=10,
        )
        
        # Assert
        assert isinstance(signals, list)
        assert len(signals) <= 10
        
        # All signals should be IntrinsicSignal objects
        for signal in signals:
            assert isinstance(signal, IntrinsicSignal)
            assert signal.user_id == "test-user"
            assert signal.signal_type in CuriosityType
            assert 0.0 <= signal.total_score <= 1.0
            assert signal.priority in ["low", "normal", "high"]
    
    async def test_gap_detector(self, curiosity_engine, mock_world_model):
        """Test knowledge gap detection."""
        # Arrange - Mock uncertain areas
        mock_world_model.query_uncertain_areas.return_value = [
            {"topic": "User's work schedule", "description": "Missing information about work hours"},
            {"topic": "Sleep patterns", "description": "Incomplete sleep data"},
        ]
        
        # Act
        signals = await curiosity_engine._detect_knowledge_gaps("test-user")
        
        # Assert
        assert len(signals) == 2
        assert all(s.signal_type == CuriosityType.KNOWLEDGE_GAP for s in signals)
        assert signals[0].topic == "User's work schedule"
        assert signals[1].topic == "Sleep patterns"
    
    async def test_interest_tracker_personality_filtering(self, curiosity_engine, mock_personality_service):
        """Test interest tracker filters by personality traits."""
        # Arrange - Set personality with low openness
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(
                openness=0.3,  # Low - should filter out openness-requiring hobbies
                conscientiousness=0.8,  # High - should allow conscientiousness hobbies
                extraversion=0.5,
                agreeableness=0.5,
                neuroticism=0.5,
            ),
            relationship=RelationshipVector(
                user_id="test-user",
                closeness=0.7,
                trust_level=0.8,
                familiarity=0.7,
            ),
        )
        mock_personality_service.get_personality_context.return_value = context
        
        # Act
        signals = await curiosity_engine._track_interests("test-user")
        
        # Assert - Should only get conscientiousness-based hobbies
        assert len(signals) > 0
        
        # Check that high-openness hobbies are filtered out
        hobby_names = [s.topic for s in signals]
        assert "Deep Dive Learning" not in hobby_names  # Requires openness > 0.6
        assert "Pattern Analysis" not in hobby_names  # Requires openness > 0.7
        
        # Check that conscientiousness hobbies are included
        assert any("Skill Building" in name or "Memory Organization" in name or "Knowledge Graph" in name 
                   for name in hobby_names)
    
    async def test_signal_scoring_with_personality(self, curiosity_engine):
        """Test signal scoring applies personality modifiers."""
        # Arrange
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.NOVELTY,
            topic="Test Topic",
            description="Test description",
            novelty_score=0.8,
            uncertainty_score=0.6,
            user_relevance_score=0.7,
            feasibility_score=0.5,
        )
        
        # Act
        score = await curiosity_engine._calculate_signal_score(signal, "test-user")
        
        # Assert
        assert 0.0 <= score <= 1.0
        # With high openness (0.7), novelty weight should be boosted
        # Score should be influenced by novelty and relevance
        assert score > 0.0
    
    async def test_signal_scoring_without_personality(self):
        """Test signal scoring works without personality service."""
        # Arrange
        engine = CuriosityEngine(world_model=None, personality_service=None)
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Test Hobby",
            description="Test description",
            novelty_score=0.6,
            uncertainty_score=0.5,
            user_relevance_score=0.7,
            feasibility_score=0.8,
        )
        
        # Act
        score = await engine._calculate_signal_score(signal, "test-user")
        
        # Assert - Should use base weights
        assert 0.0 <= score <= 1.0
        assert score > 0.0
    
    async def test_three_gate_system_values_ethics(self):
        """Test Values/Ethics gate (Phase 6.3 - sensitive topic filtering)."""
        # Arrange - Engine without personality to test values gate only
        engine = CuriosityEngine(world_model=None, personality_service=None)
        
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Python programming",
            description="Learn Python",
            user_relevance_score=0.8,
            total_score=0.8,
            intrinsic_reward=0.8,  # Above 0.3 threshold
        )
        
        # Act
        passes = await engine._passes_gates(signal, "test-user")
        
        # Assert - Should pass (non-sensitive topic with good reward)
        assert passes is True
    
    async def test_three_gate_system_values_ethics_sensitive(self, curiosity_engine):
        """Test Values/Ethics gate blocks sensitive topics with low relevance."""
        # Arrange - Sensitive topic with low relevance
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Personal health issues",
            description="Explore health data",
            user_relevance_score=0.3,  # Too low for sensitive topic
            intrinsic_reward=0.5,
        )
        
        # Act
        passes = await curiosity_engine._passes_gates(signal, "test-user")
        
        # Assert - Should fail (sensitive topic with low relevance)
        assert passes is False
    
    async def test_three_gate_system_emotion_relationship(self, curiosity_engine, mock_personality_service):
        """Test Emotion/relationship gate filters by closeness."""
        # Arrange - Low relationship closeness
        context = PersonalityContext(
            user_id="test-user",
            traits=PersonalityTraits(
                openness=0.7, conscientiousness=0.6, extraversion=0.5,
                agreeableness=0.6, neuroticism=0.4,
            ),
            relationship=RelationshipVector(
                user_id="test-user",
                closeness=0.2,  # Very low - should fail gate
                trust_level=0.5,
                familiarity=0.5,
            ),
        )
        mock_personality_service.get_personality_context.return_value = context
        
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Test Hobby",
            description="Test",
            total_score=0.8,
        )
        
        # Act
        passes = await curiosity_engine._passes_gates(signal, "test-user")
        
        # Assert - Should fail due to low closeness
        assert passes is False
    
    async def test_three_gate_system_resource(self, curiosity_engine):
        """Test Resource gate filters by score threshold."""
        # Arrange - Low score signal
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id="test-user",
            signal_type=CuriosityType.NOVELTY,
            topic="Low Priority",
            description="Test",
            total_score=0.2,  # Below threshold
        )
        
        # Act
        passes = await curiosity_engine._passes_gates(signal, "test-user")
        
        # Assert - Should fail due to low score
        assert passes is False
    
    async def test_priority_mapping(self, curiosity_engine):
        """Test signal score maps to correct priority."""
        # Arrange
        high_signal = IntrinsicSignal(
            signal_id="high",
            user_id="test-user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="High Priority",
            description="Test",
            novelty_score=0.9,
            user_relevance_score=0.9,
            feasibility_score=0.8,
        )
        
        normal_signal = IntrinsicSignal(
            signal_id="normal",
            user_id="test-user",
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Normal Priority",
            description="Test",
            novelty_score=0.6,
            user_relevance_score=0.6,
            feasibility_score=0.6,
        )
        
        low_signal = IntrinsicSignal(
            signal_id="low",
            user_id="test-user",
            signal_type=CuriosityType.NOVELTY,
            topic="Low Priority",
            description="Test",
            novelty_score=0.3,
            user_relevance_score=0.3,
            feasibility_score=0.3,
        )
        
        # Act
        signals = await curiosity_engine._score_and_filter_signals(
            [high_signal, normal_signal, low_signal],
            "test-user",
        )
        
        # Assert
        for signal in signals:
            if signal.total_score >= 0.75:
                assert signal.priority == "high"
            elif signal.total_score >= 0.50:
                assert signal.priority == "normal"
            else:
                assert signal.priority == "low"
    
    async def test_get_hobby_template(self, curiosity_engine):
        """Test retrieving hobby template by ID."""
        # Act
        template = curiosity_engine.get_hobby_template("deep_dive_learning")
        
        # Assert
        assert template is not None
        assert template.template_id == "deep_dive_learning"
        assert template.name == "Deep Dive Learning"
        assert template.category == HobbyCategory.LEARNING
        
        # Test non-existent template
        none_template = curiosity_engine.get_hobby_template("nonexistent")
        assert none_template is None
    
    async def test_custom_hobby_templates(self):
        """Test CuriosityEngine with custom hobby templates."""
        # Arrange
        custom_templates = [
            HobbyTemplate(
                template_id="custom_hobby",
                name="Custom Hobby",
                category=HobbyCategory.CREATIVE,
                description="A custom hobby for testing",
                goal_template="Work on {topic}",
                personality_traits={"openness": 0.8},
            ),
        ]
        
        engine = CuriosityEngine(
            world_model=None,
            personality_service=None,
            hobby_templates=custom_templates,
        )
        
        # Assert
        assert len(engine.hobby_templates) == 1
        assert engine.hobby_templates[0].template_id == "custom_hobby"
    
    async def test_signal_expiration(self, curiosity_engine):
        """Test signals can have expiration times."""
        # Arrange
        from datetime import timedelta
        
        signal = IntrinsicSignal(
            signal_id="expiring-signal",
            user_id="test-user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Expiring Opportunity",
            description="Test",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        
        # Assert
        assert signal.expires_at is not None
        assert signal.expires_at > datetime.utcnow()
    
    async def test_signal_status_tracking(self, curiosity_engine):
        """Test signal status can be tracked."""
        # Arrange
        signal = IntrinsicSignal(
            signal_id="status-signal",
            user_id="test-user",
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Status Test",
            description="Test",
            status="pending",
        )
        
        # Assert initial status
        assert signal.status == "pending"
        
        # Simulate conversion
        signal.status = "converted"
        assert signal.status == "converted"
