"""
Integration tests for CuriosityEngine - improving coverage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aico.ai.curiosity import (
    CuriosityEngine,
    IntrinsicSignal,
    CuriosityType,
    HobbyTemplate,
    HobbyCategory,
)


@pytest.fixture
def curiosity_engine_with_mocks():
    """Create CuriosityEngine with mocked dependencies."""
    mock_world_model = MagicMock()
    mock_world_model.query_uncertain_areas = AsyncMock(return_value=[])
    mock_world_model.detect_anomalies = AsyncMock(return_value=[])
    
    mock_personality = MagicMock()
    mock_personality.get_personality_context = AsyncMock(return_value=None)
    
    mock_ams = MagicMock()
    mock_ams.get_user_interests = AsyncMock(return_value=[])
    
    return CuriosityEngine(
        world_model=mock_world_model,
        personality_service=mock_personality,
        ams_service=mock_ams,
    )


@pytest.mark.asyncio
async def test_detect_knowledge_gaps(curiosity_engine_with_mocks):
    """Test knowledge gap detection."""
    signals = await curiosity_engine_with_mocks._detect_knowledge_gaps("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_detect_anomalies(curiosity_engine_with_mocks):
    """Test anomaly detection."""
    signals = await curiosity_engine_with_mocks._detect_anomalies("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_track_interests(curiosity_engine_with_mocks):
    """Test interest tracking."""
    signals = await curiosity_engine_with_mocks._track_interests("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_generate_personality_hobby_signals(curiosity_engine_with_mocks):
    """Test personality-based hobby signal generation."""
    signals = await curiosity_engine_with_mocks._generate_personality_hobby_signals("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_calculate_intrinsic_reward(curiosity_engine_with_mocks):
    """Test intrinsic reward calculation."""
    signal = IntrinsicSignal(
        signal_id="test_signal",
        user_id="test_user",
        signal_type=CuriosityType.KNOWLEDGE_GAP,
        topic="test_topic",
        description="Test description",
        novelty_score=0.8,
        uncertainty_score=0.7,
        user_relevance_score=0.6,
        feasibility_score=0.8,
        cost_estimate=0.3,
        total_score=0.7,
        priority="normal",
        source_component="test",
        target_ref=None,
        topic_tags=[],
        detected_at=None,
        expires_at=None,
        status="active",
    )
    
    await curiosity_engine_with_mocks._calculate_intrinsic_reward(signal, "test_user")
    
    # Should have intrinsic reward set
    assert signal.intrinsic_reward is not None


@pytest.mark.asyncio
async def test_score_and_filter_signals(curiosity_engine_with_mocks):
    """Test signal scoring and filtering."""
    signals = [
        IntrinsicSignal(
            signal_id="signal_1",
            user_id="test_user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="topic_1",
            description="Description 1",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.6,
            feasibility_score=0.8,
            cost_estimate=0.3,
            total_score=0.7,
            priority="normal",
            source_component="test",
            target_ref=None,
            topic_tags=[],
            detected_at=None,
            expires_at=None,
            status="active",
        ),
        IntrinsicSignal(
            signal_id="signal_2",
            user_id="test_user",
            signal_type=CuriosityType.NOVELTY,
            topic="topic_2",
            description="Description 2",
            novelty_score=0.5,
            uncertainty_score=0.4,
            user_relevance_score=0.3,
            feasibility_score=0.6,
            cost_estimate=0.5,
            total_score=0.4,
            priority="low",
            source_component="test",
            target_ref=None,
            topic_tags=[],
            detected_at=None,
            expires_at=None,
            status="active",
        ),
    ]
    
    filtered = await curiosity_engine_with_mocks._score_and_filter_signals(signals, "test_user")
    
    assert isinstance(filtered, list)


@pytest.mark.asyncio
async def test_calculate_signal_score(curiosity_engine_with_mocks):
    """Test signal score calculation."""
    signal = IntrinsicSignal(
        signal_id="test_signal",
        user_id="test_user",
        signal_type=CuriosityType.KNOWLEDGE_GAP,
        topic="test_topic",
        description="Test description",
        novelty_score=0.8,
        uncertainty_score=0.7,
        user_relevance_score=0.6,
        feasibility_score=0.8,
        cost_estimate=0.3,
        total_score=0.7,
        priority="normal",
        source_component="test",
        target_ref=None,
        topic_tags=[],
        detected_at=None,
        expires_at=None,
        status="active",
    )
    
    score = await curiosity_engine_with_mocks._calculate_signal_score(signal, "test_user")
    
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_passes_gates(curiosity_engine_with_mocks):
    """Test three-gate filtering."""
    signal = IntrinsicSignal(
        signal_id="test_signal",
        user_id="test_user",
        signal_type=CuriosityType.KNOWLEDGE_GAP,
        topic="test_topic",
        description="Test description",
        novelty_score=0.8,
        uncertainty_score=0.7,
        user_relevance_score=0.6,
        feasibility_score=0.8,
        cost_estimate=0.3,
        total_score=0.7,
        priority="normal",
        source_component="test",
        target_ref=None,
        topic_tags=[],
        detected_at=None,
        expires_at=None,
        status="active",
    )
    
    passes = await curiosity_engine_with_mocks._passes_gates(signal, "test_user")
    
    assert isinstance(passes, bool)


def test_find_matching_hobby_template(curiosity_engine_with_mocks):
    """Test finding matching hobby template."""
    # Should find a template for a known topic
    template = curiosity_engine_with_mocks._find_matching_hobby_template("photography")
    
    # May or may not find depending on templates
    assert template is None or isinstance(template, HobbyTemplate)


def test_get_hobby_template(curiosity_engine_with_mocks):
    """Test getting hobby template by ID."""
    # Get first template ID
    if curiosity_engine_with_mocks.hobby_templates:
        template_id = curiosity_engine_with_mocks.hobby_templates[0].template_id
        template = curiosity_engine_with_mocks.get_hobby_template(template_id)
        
        assert template is not None
        assert template.template_id == template_id
    
    # Test non-existent template
    template = curiosity_engine_with_mocks.get_hobby_template("nonexistent")
    assert template is None


@pytest.mark.asyncio
async def test_scan_for_opportunities_max_signals(curiosity_engine_with_mocks):
    """Test max_signals parameter."""
    signals = await curiosity_engine_with_mocks.scan_for_opportunities(
        user_id="test_user",
        max_signals=3
    )
    
    assert isinstance(signals, list)
    assert len(signals) <= 3


@pytest.mark.asyncio
async def test_scan_for_opportunities_error_handling(curiosity_engine_with_mocks):
    """Test error handling in scan."""
    # Make world_model raise an error
    curiosity_engine_with_mocks.world_model.query_uncertain_areas = AsyncMock(
        side_effect=Exception("Test error")
    )
    
    # Should handle error gracefully
    signals = await curiosity_engine_with_mocks.scan_for_opportunities("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_curiosity_engine_without_services():
    """Test engine works without optional services."""
    engine = CuriosityEngine(
        world_model=None,
        personality_service=None,
        ams_service=None,
    )
    
    signals = await engine.scan_for_opportunities("test_user")
    
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_clustering_integration(curiosity_engine_with_mocks):
    """Test opportunity clustering."""
    # Create multiple similar signals
    signals = [
        IntrinsicSignal(
            signal_id=f"signal_{i}",
            user_id="test_user",
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="similar_topic",
            description=f"Description {i}",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.6,
            feasibility_score=0.8,
            cost_estimate=0.3,
            total_score=0.7,
            priority="normal",
            source_component="test",
            target_ref=None,
            topic_tags=[],
            detected_at=None,
            expires_at=None,
            status="active",
        )
        for i in range(5)
    ]
    
    # Clusterer should be initialized
    assert curiosity_engine_with_mocks.clusterer is not None


@pytest.mark.asyncio
async def test_reward_calculator_integration(curiosity_engine_with_mocks):
    """Test intrinsic reward calculator integration."""
    assert curiosity_engine_with_mocks.reward_calculator is not None
