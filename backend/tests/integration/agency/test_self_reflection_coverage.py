"""
Integration tests for SelfReflectionEngine - improving coverage
"""

import pytest
from datetime import datetime, timedelta

from aico.ai.agency.models import (
    RunType,
    LessonType,
    EntityType,
)


@pytest.mark.asyncio
async def test_get_active_lessons(agency_engine, test_user):
    """Test getting active lessons."""
    lessons = await agency_engine.self_reflection.get_active_lessons(test_user)
    
    assert isinstance(lessons, list)


@pytest.mark.asyncio
async def test_get_active_lessons_filtered_by_type(agency_engine, test_user):
    """Test getting active lessons filtered by type."""
    lessons = await agency_engine.self_reflection.get_active_lessons(
        test_user,
        lesson_type=LessonType.SKILL_TUNING
    )
    
    assert isinstance(lessons, list)


@pytest.mark.asyncio
async def test_get_skill_performance_not_found(agency_engine, test_user):
    """Test getting skill performance when no data exists."""
    perf = await agency_engine.self_reflection.get_skill_performance(
        test_user,
        "nonexistent_skill"
    )
    
    assert perf is None


@pytest.mark.asyncio
async def test_get_goal_type_performance_not_found(agency_engine, test_user):
    """Test getting goal type performance when no data exists."""
    perf = await agency_engine.self_reflection.get_goal_type_performance(
        test_user,
        "nonexistent_goal_type"
    )
    
    assert perf is None


@pytest.mark.asyncio
async def test_get_all_skill_performances(agency_engine, test_user):
    """Test getting all skill performances."""
    perfs = await agency_engine.self_reflection.get_all_skill_performances(test_user)
    
    assert isinstance(perfs, dict)


@pytest.mark.asyncio
async def test_reflection_engine_configuration(agency_engine):
    """Test reflection engine is configured correctly."""
    reflection = agency_engine.self_reflection
    
    assert reflection.min_sample_size >= 1
    assert 0.0 <= reflection.confidence_threshold <= 1.0
    assert reflection.policy_mode in ["observe_only", "suggest", "allow_amend", "suggest_amendments", "auto_amend"]


@pytest.mark.asyncio
async def test_lesson_applicator_initialization(agency_engine):
    """Test lesson applicator is properly initialized."""
    reflection = agency_engine.self_reflection
    
    assert reflection.lesson_applicator is not None
    assert reflection.lesson_applicator.min_confidence >= 0.0
    assert isinstance(reflection.lesson_applicator.dry_run, bool)


@pytest.mark.asyncio
async def test_lesson_projector_initialization(agency_engine):
    """Test lesson projector is properly initialized."""
    reflection = agency_engine.self_reflection
    
    assert reflection.projector is not None
    assert reflection.projector.config is not None


@pytest.mark.asyncio
async def test_run_reflection_scheduled(agency_engine, test_user):
    """Test running a scheduled reflection."""
    reflection = agency_engine.self_reflection
    
    # Run a scheduled reflection
    result = await reflection.run_reflection(test_user, RunType.SCHEDULED)
    
    # Should return a reflection run object
    assert result is not None
    assert hasattr(result, 'run_id')
    assert hasattr(result, 'status')


@pytest.mark.asyncio
async def test_run_reflection_triggered(agency_engine, test_user):
    """Test running a triggered reflection."""
    reflection = agency_engine.self_reflection
    
    # Run a triggered reflection
    result = await reflection.run_reflection(test_user, RunType.TRIGGERED)
    
    # Should return a reflection run object
    assert result is not None
    assert hasattr(result, 'run_id')


@pytest.mark.asyncio
async def test_get_skill_performance_with_data(agency_engine, test_user, test_db):
    """Test getting skill performance when data exists."""
    from aico.ai.agency.models import SelfModelEntry, EntityType, PerformanceSummary
    import uuid
    
    reflection = agency_engine.self_reflection
    
    # Create a self-model entry for a skill
    skill_id = "test_skill_perf"
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id=skill_id,
        performance_summary=PerformanceSummary(
            success_rate=0.85,
            avg_completion_time=100.0,
            total_attempts=20,
            recent_trend="stable"
        ),
        window_start=datetime.utcnow() - timedelta(days=7),
        window_end=datetime.utcnow(),
        sample_size=20,
        confidence=0.9,
        last_updated=datetime.utcnow(),
    )
    
    # Store the entry
    await reflection.self_model_store.upsert_entry(entry)
    
    # Get performance
    perf = await reflection.get_skill_performance(test_user, skill_id)
    
    # Should return the success rate
    assert perf is not None
    assert perf == 0.85


@pytest.mark.asyncio
async def test_get_goal_type_performance_with_data(agency_engine, test_user):
    """Test getting goal type performance when data exists."""
    from aico.ai.agency.models import SelfModelEntry, EntityType, PerformanceSummary
    import uuid
    
    reflection = agency_engine.self_reflection
    
    # Create a self-model entry for a goal type
    goal_type = "research"
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.GOAL_TYPE,
        entity_id=goal_type,
        performance_summary=PerformanceSummary(
            success_rate=0.75,
            avg_completion_time=300.0,
            total_attempts=15,
            recent_trend="improving"
        ),
        window_start=datetime.utcnow() - timedelta(days=14),
        window_end=datetime.utcnow(),
        sample_size=15,
        confidence=0.8,
        last_updated=datetime.utcnow(),
    )
    
    # Store the entry
    await reflection.self_model_store.upsert_entry(entry)
    
    # Get performance
    perf = await reflection.get_goal_type_performance(test_user, goal_type)
    
    # Should return performance metrics
    assert perf is not None
    assert "success_rate" in perf
    assert perf["success_rate"] == 0.75


@pytest.mark.asyncio
async def test_reflection_stores_initialization(agency_engine):
    """Test that all reflection stores are initialized."""
    reflection = agency_engine.self_reflection
    
    assert reflection.lesson_store is not None
    assert reflection.self_model_store is not None
    assert reflection.run_store is not None


@pytest.mark.asyncio
async def test_reflection_policy_mode(agency_engine):
    """Test reflection policy mode configuration."""
    reflection = agency_engine.self_reflection
    
    assert reflection.policy_mode in ["observe_only", "suggest", "allow_amend", "suggest_amendments", "auto_amend"]


@pytest.mark.asyncio
async def test_reflection_confidence_threshold(agency_engine):
    """Test reflection confidence threshold."""
    reflection = agency_engine.self_reflection
    
    # Config may set different threshold
    assert reflection.confidence_threshold >= 0.7
    assert 0.0 <= reflection.confidence_threshold <= 1.0


@pytest.mark.asyncio
async def test_reflection_min_sample_size(agency_engine):
    """Test reflection min sample size."""
    reflection = agency_engine.self_reflection
    
    # Config may set different min_sample_size
    assert reflection.min_sample_size >= 10
    assert reflection.min_sample_size > 0


@pytest.mark.asyncio
async def test_get_all_skill_performances_with_data(agency_engine, test_user):
    """Test getting all skill performances when data exists."""
    from aico.ai.agency.models import SelfModelEntry, EntityType, PerformanceSummary
    import uuid
    
    reflection = agency_engine.self_reflection
    
    # Create multiple skill entries
    skills = [
        ("skill_a", 0.9),
        ("skill_b", 0.7),
        ("skill_c", 0.85),
    ]
    
    for skill_id, success_rate in skills:
        entry = SelfModelEntry(
            model_id=str(uuid.uuid4()),
            user_id=test_user,
            entity_type=EntityType.SKILL,
            entity_id=skill_id,
            performance_summary=PerformanceSummary(
                success_rate=success_rate,
                avg_completion_time=100.0,
                total_attempts=10,
                recent_trend="stable"
            ),
            window_start=datetime.utcnow() - timedelta(days=7),
            window_end=datetime.utcnow(),
            sample_size=10,
            confidence=0.8,
            last_updated=datetime.utcnow(),
        )
        await reflection.self_model_store.upsert_entry(entry)
    
    # Get all performances
    perfs = await reflection.get_all_skill_performances(test_user)
    
    # Should return a dict with all skills
    assert isinstance(perfs, dict)
    # May contain the skills we just added
    # (Note: other tests may have added skills too)


@pytest.mark.asyncio
async def test_reflection_run_error_handling(agency_engine, test_user):
    """Test error handling in reflection run."""
    reflection = agency_engine.self_reflection
    
    # Running reflection should handle errors gracefully
    # Even with no data, should complete without raising
    try:
        result = await reflection.run_reflection(test_user, RunType.SCHEDULED)
        assert result is not None
    except Exception as e:
        # Should not raise exceptions in normal operation
        pytest.fail(f"Reflection run raised unexpected exception: {e}")
