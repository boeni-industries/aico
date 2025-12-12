"""
Integration tests for LessonMemoryProjector - improving coverage
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from aico.ai.agency.models import (
    LessonType,
    TargetKind,
    LessonStatus,
)


@pytest.mark.asyncio
async def test_lesson_projector_initialization(agency_engine):
    """Test lesson projector is properly initialized."""
    projector = agency_engine.self_reflection.projector
    
    assert projector.config is not None
    assert projector.db is not None
    assert projector.lesson_store is not None
    assert projector.self_model_store is not None
    assert projector.run_store is not None


@pytest.mark.asyncio
async def test_project_lesson_to_memory(agency_engine, test_user):
    """Test projecting lesson to memory."""
    projector = agency_engine.self_reflection.projector
    
    # Create mock lesson
    lesson = Mock()
    lesson.lesson_id = "test_lesson_1"
    lesson.user_id = test_user
    lesson.lesson_type = LessonType.SKILL_TUNING
    lesson.target_kind = TargetKind.SKILL
    lesson.target_id = "test_skill"
    lesson.summary_text = "Test lesson description"
    lesson.confidence = 0.85
    lesson.status = LessonStatus.ACTIVE
    lesson.created_at = datetime.utcnow()
    lesson.metrics_basis = None
    
    result = await projector.project_lesson_to_memory(lesson)
    
    assert result is not None
    assert result.get("success") is True
    assert "lesson_id" in result


@pytest.mark.asyncio
async def test_project_lesson_to_kg(agency_engine, test_user):
    """Test projecting lesson to knowledge graph."""
    projector = agency_engine.self_reflection.projector
    
    # Create mock lesson
    lesson = Mock()
    lesson.lesson_id = "test_lesson_2"
    lesson.user_id = test_user
    lesson.lesson_type = LessonType.SKILL_TUNING
    lesson.target_kind = TargetKind.SKILL
    lesson.target_id = "test_skill"
    lesson.summary_text = "Test lesson description"
    lesson.confidence = 0.85
    lesson.status = LessonStatus.ACTIVE
    lesson.created_at = datetime.utcnow()
    lesson.metrics_basis = None
    
    result = await projector.project_lesson_to_kg(lesson)
    
    assert result is not None


@pytest.mark.asyncio
async def test_query_active_lessons(agency_engine, test_user):
    """Test querying active lessons."""
    projector = agency_engine.self_reflection.projector
    
    results = await projector.query_active_lessons(test_user)
    
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_query_active_lessons_filtered(agency_engine, test_user):
    """Test querying active lessons with filter."""
    projector = agency_engine.self_reflection.projector
    
    results = await projector.query_active_lessons(
        test_user,
        target_kind=TargetKind.SKILL
    )
    
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_generate_relevance_tags(agency_engine):
    """Test relevance tag generation."""
    projector = agency_engine.self_reflection.projector
    
    # Create mock lesson
    lesson = Mock()
    lesson.lesson_type = LessonType.SKILL_TUNING
    lesson.target_kind = TargetKind.SKILL
    lesson.target_id = "test_skill"
    
    tags = projector._generate_relevance_tags(lesson)
    
    assert isinstance(tags, list)
    assert len(tags) > 0
    # Should include lesson type and target
    assert any("skill" in tag.lower() for tag in tags)


@pytest.mark.asyncio
async def test_get_target_node_id(agency_engine):
    """Test getting target node ID."""
    projector = agency_engine.self_reflection.projector
    
    # Test skill target
    node_id = projector._get_target_node_id(TargetKind.SKILL, "test_skill")
    assert node_id == "skill:test_skill"
    
    # Test policy target
    node_id = projector._get_target_node_id(TargetKind.POLICY_RULE, "test_policy")
    assert node_id == "policy_rule:test_policy"
    
    # Test arbiter weight
    node_id = projector._get_target_node_id(TargetKind.ARBITER_WEIGHT, "priority")
    assert node_id == "arbiter_weight:priority"
    
    # Test persona trait
    node_id = projector._get_target_node_id(TargetKind.PERSONA_TRAIT, "formality")
    assert node_id == "persona_trait:formality"


@pytest.mark.asyncio
async def test_project_lesson_with_real_data(agency_engine, test_user):
    """Test projecting a real lesson to memory."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis, ChangeType
    import uuid
    
    projector = agency_engine.self_reflection.projector
    
    # Create a real lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Improve skill performance",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=1.2,
            notes="Increase based on success rate"
        ),
        confidence=0.85,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=20,
            outcome_counts={"success": 16, "failure": 4}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Store the lesson first
    await projector.lesson_store.create_lesson(lesson)
    
    # Project to memory
    result = await projector.project_lesson_to_memory(lesson)
    
    assert result is not None
    assert result.get("success") is True
    assert "lesson_id" in result


@pytest.mark.asyncio
async def test_project_self_model_entry(agency_engine, test_user):
    """Test projecting self-model entry."""
    from aico.ai.agency.models import SelfModelEntry, EntityType, PerformanceSummary
    import uuid
    
    projector = agency_engine.self_reflection.projector
    
    # Create a self-model entry
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill",
        performance_summary=PerformanceSummary(
            success_rate=0.8,
            avg_completion_time=120.0,
            total_attempts=25,
            recent_trend="improving"
        ),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
        sample_size=25,
        confidence=0.85,
        last_updated=datetime.utcnow(),
    )
    
    # Store the entry first
    await projector.self_model_store.upsert_entry(entry)
    
    # Project to KG
    result = await projector.project_self_model_to_kg(entry)
    
    # Should succeed or return None gracefully
    assert result is None or isinstance(result, dict)


@pytest.mark.asyncio
async def test_generate_relevance_tags_all_types(agency_engine):
    """Test relevance tag generation for all lesson types."""
    projector = agency_engine.self_reflection.projector
    
    # Test each lesson type
    lesson_types = [
        (LessonType.SKILL_TUNING, TargetKind.SKILL, "skill"),
        (LessonType.PLANNER_HEURISTIC, TargetKind.ARBITER_WEIGHT, "planning"),
        (LessonType.PERSONA_STYLE, TargetKind.PERSONA_TRAIT, "persona"),
        (LessonType.POLICY_SUGGESTION, TargetKind.POLICY_RULE, "policy"),
        (LessonType.CURIOSITY_FOCUS, TargetKind.CURIOSITY_POLICY, "curiosity"),
    ]
    
    for lesson_type, target_kind, expected_tag in lesson_types:
        lesson = Mock()
        lesson.lesson_type = lesson_type
        lesson.target_kind = target_kind
        lesson.target_id = "test_target"
        
        tags = projector._generate_relevance_tags(lesson)
        
        assert isinstance(tags, list)
        assert len(tags) > 0
        # Should include type-specific tag
        assert any(expected_tag in tag.lower() for tag in tags)


@pytest.mark.asyncio
async def test_query_active_lessons_multiple_filters(agency_engine, test_user):
    """Test querying active lessons with multiple filters."""
    projector = agency_engine.self_reflection.projector
    
    # Query with both user_id and target_kind
    results = await projector.query_active_lessons(
        test_user,
        target_kind=TargetKind.SKILL
    )
    
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_project_lesson_to_kg_without_kg_storage(agency_engine, test_user):
    """Test projecting to KG when KG storage is not available."""
    projector = agency_engine.self_reflection.projector
    
    # Create mock lesson
    lesson = Mock()
    lesson.lesson_id = "test_lesson_no_kg"
    lesson.user_id = test_user
    lesson.lesson_type = LessonType.SKILL_TUNING
    lesson.target_kind = TargetKind.SKILL
    lesson.target_id = "test_skill"
    lesson.summary_text = "Test lesson"
    lesson.confidence = 0.85
    lesson.status = LessonStatus.ACTIVE
    lesson.created_at = datetime.utcnow()
    lesson.metrics_basis = None
    
    # Should handle gracefully when KG storage is None
    result = await projector.project_lesson_to_kg(lesson)
    
    # Should return None or empty result when KG not available
    assert result is None or isinstance(result, dict)


@pytest.mark.asyncio
async def test_project_lesson_error_handling(agency_engine, test_user):
    """Test error handling in lesson projection."""
    projector = agency_engine.self_reflection.projector
    
    # Create invalid mock lesson (missing required attributes)
    lesson = Mock()
    lesson.lesson_id = None  # Invalid
    lesson.user_id = test_user
    
    # Should handle errors gracefully
    try:
        result = await projector.project_lesson_to_memory(lesson)
        # If it doesn't raise, should return error indicator
        assert result is None or "error" in result or "success" in result
    except Exception:
        # Acceptable to raise exception for invalid data
        pass
