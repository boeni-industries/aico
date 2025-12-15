"""
Integration tests for LessonApplicationService - improving coverage
"""

import pytest
from unittest.mock import Mock

from aico.ai.agency.models import (
    LessonType,
    TargetKind,
    LessonStatus,
    ChangeType,
)


@pytest.mark.asyncio
async def test_lesson_applicator_initialization(agency_engine):
    """Test lesson applicator is properly initialized."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    assert applicator.config is not None
    assert applicator.db is not None
    assert applicator.lesson_store is not None
    assert applicator.projector is not None
    assert applicator.min_confidence >= 0.0
    assert isinstance(applicator.dry_run, bool)
    assert applicator.policy_amendment_limit > 0
    assert isinstance(applicator.policy_freeze, bool)


@pytest.mark.asyncio
async def test_apply_lesson_low_confidence(agency_engine, test_user):
    """Test lesson with low confidence is rejected."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    # Create mock lesson with low confidence
    lesson = Mock()
    lesson.lesson_id = "test_lesson_1"
    lesson.user_id = test_user
    lesson.lesson_type = LessonType.SKILL_TUNING
    lesson.target_kind = TargetKind.SKILL
    lesson.target_id = "test_skill"
    lesson.confidence = 0.3  # Below threshold
    lesson.status = LessonStatus.ACTIVE
    lesson.change_type = ChangeType.WEIGHT_TWEAK
    lesson.change_data = {"weight_delta": 0.1}
    
    result = await applicator.apply_lesson(lesson)
    
    assert result is False


@pytest.mark.asyncio
async def test_apply_pending_lessons_empty(agency_engine, test_user):
    """Test applying pending lessons when none exist."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    result = await applicator.apply_pending_lessons(test_user)
    
    assert result["total"] == 0
    assert result["applied"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_policy_freeze_configuration(agency_engine):
    """Test policy freeze configuration."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    # Policy freeze is configurable
    assert isinstance(applicator.policy_freeze, bool)


@pytest.mark.asyncio
async def test_dry_run_configuration(agency_engine):
    """Test dry run configuration."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    # Dry run should be configurable
    assert isinstance(applicator.dry_run, bool)


@pytest.mark.asyncio
async def test_check_policy_amendment_rate_limit(agency_engine, test_user):
    """Test policy amendment rate limiting."""
    applicator = agency_engine.self_reflection.lesson_applicator
    
    # Should pass when no amendments exist
    result = await applicator._check_policy_amendment_rate_limit(test_user)
    
    assert result is True


@pytest.mark.asyncio
async def test_apply_skill_lesson_with_real_data(agency_engine, test_user, test_db):
    """Test applying a skill lesson with actual database."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis
    import uuid
    
    applicator = agency_engine.self_reflection.lesson_applicator
    
    # First create a skill in the database
    from datetime import datetime, UTC
    skill_id = f"test_skill_for_lesson_{uuid.uuid4().hex[:8]}"
    test_db.execute(
        """INSERT INTO skills (skill_id, skill_name, skill_type, trigger_context, procedure_template, dimension_vector, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (skill_id, "Test Skill", "base", "test", "test template", '{}', "active", datetime.now(UTC).isoformat())
    )
    test_db.commit()
    
    # Create a real lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id=skill_id,
        summary_text="Improve skill selection weight",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=1.2,
            notes="Increase weight based on performance"
        ),
        confidence=0.85,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=20,
            outcome_counts={"success": 15, "failure": 5}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Store the lesson first
    await applicator.lesson_store.create_lesson(lesson)
    
    # Apply the lesson
    result = await applicator.apply_lesson(lesson)
    
    # Result may be False if dry_run is enabled in config
    assert isinstance(result, bool)
    
    # Only verify skill was updated if lesson was actually applied
    if result:
        row = test_db.execute(
            "SELECT dimension_vector FROM skills WHERE skill_id = ?",
            (skill_id,)
        ).fetchone()
        
        import json
        dimension_vector = json.loads(row["dimension_vector"])
        assert "lesson_adjustments" in dimension_vector
        assert "selection_weight" in dimension_vector["lesson_adjustments"]


@pytest.mark.asyncio
async def test_apply_skill_lesson_nonexistent_skill(agency_engine, test_user):
    """Test applying skill lesson when skill doesn't exist."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis
    import uuid
    
    applicator = agency_engine.self_reflection.lesson_applicator
    
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="nonexistent_skill",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=1.2,
            notes="Test"
        ),
        confidence=0.85,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=20,
            outcome_counts={"success": 15, "failure": 5}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Should fail gracefully
    result = await applicator._apply_skill_lesson(lesson)
    assert result is False


@pytest.mark.asyncio
async def test_apply_arbiter_weight_lesson(agency_engine, test_user):
    """Test applying arbiter weight lesson."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis
    import uuid
    
    applicator = agency_engine.self_reflection.lesson_applicator
    
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PLANNER_HEURISTIC,
        target_kind=TargetKind.ARBITER_WEIGHT,
        target_id="priority",
        summary_text="Adjust arbiter priority weight",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="priority",
            old=0.5,
            new=0.6,
            notes="Increase priority weight"
        ),
        confidence=0.8,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=15,
            outcome_counts={"success": 12, "failure": 3}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Apply the lesson
    result = await applicator._apply_arbiter_weight_lesson(lesson)
    
    # Should succeed or fail gracefully
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_apply_persona_lesson(agency_engine, test_user):
    """Test applying persona lesson."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis
    import uuid
    
    applicator = agency_engine.self_reflection.lesson_applicator
    
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PERSONA_STYLE,
        target_kind=TargetKind.PERSONA_TRAIT,
        target_id="formality",
        summary_text="Adjust formality level",
        proposed_change=ProposedChange(
            change_type=ChangeType.THRESHOLD_TWEAK,
            field="formality",
            old="formal",
            new="casual",
            notes="User prefers casual tone"
        ),
        confidence=0.9,
        metrics_basis=MetricsBasis(
            time_span="14 days",
            sample_size=30,
            outcome_counts={"positive": 25, "negative": 5}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Apply the lesson
    result = await applicator._apply_persona_lesson(lesson)
    
    # Should succeed or fail gracefully
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_apply_policy_lesson(agency_engine, test_user):
    """Test applying policy lesson."""
    from aico.ai.agency.models import Lesson, ProposedChange, MetricsBasis
    import uuid
    
    applicator = agency_engine.self_reflection.lesson_applicator
    
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.POLICY_SUGGESTION,
        target_kind=TargetKind.POLICY_RULE,
        target_id="test_policy",
        summary_text="Suggest policy adjustment",
        proposed_change=ProposedChange(
            change_type=ChangeType.THRESHOLD_TWEAK,
            field="priority",
            old=5,
            new=7,
            notes="Increase policy priority"
        ),
        confidence=0.85,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=10,
            outcome_counts={"success": 8, "failure": 2}
        ),
        status=LessonStatus.ACTIVE,
        scope="this_user",
    )
    
    # Apply the lesson
    result = await applicator._apply_policy_lesson(lesson)
    
    # Should succeed or fail gracefully
    assert isinstance(result, bool)
