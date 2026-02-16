"""
Integration tests for SelfReflectionEngine - improving coverage
"""

import pytest
from datetime import datetime, timedelta, UTC

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
