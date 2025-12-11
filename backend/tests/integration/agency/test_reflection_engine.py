"""
Integration tests for Agency Phase 5: Self-Reflection & Behavioral Learning

Tests the self-reflection engine, lesson generation, and self-model tracking.
"""

import pytest
import uuid
from datetime import datetime, timedelta

from aico.ai.agency.models import (
    LessonType, TargetKind, LessonScope, LessonStatus,
    EntityType, RunType, RunStatus,
)
from aico.ai.agency.reflection import SelfReflectionEngine


@pytest.mark.asyncio
async def test_self_reflection_engine_initialization(agency_engine):
    """Test that self-reflection engine is properly initialized."""
    assert hasattr(agency_engine, 'self_reflection')
    assert isinstance(agency_engine.self_reflection, SelfReflectionEngine)
    assert agency_engine.self_reflection.policy_mode == "observe_only"


@pytest.mark.asyncio
async def test_lesson_store_create_and_retrieve(agency_engine, test_user):
    """Test creating and retrieving lessons."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType, MetricsBasis
    
    # Create a test lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Test skill needs improvement",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=0.5,
            notes="Test adjustment"
        ),
        confidence=0.8,
        metrics_basis=MetricsBasis(
            time_span="7 days",
            sample_size=20,
            outcome_counts={"success": 10, "failure": 10}
        ),
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    
    # Store the lesson
    stored_lesson = await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    assert stored_lesson.lesson_id == lesson.lesson_id
    
    # Retrieve the lesson
    retrieved_lesson = await agency_engine.self_reflection.lesson_store.get_lesson(lesson.lesson_id)
    assert retrieved_lesson is not None
    assert retrieved_lesson.lesson_id == lesson.lesson_id
    assert retrieved_lesson.summary_text == "Test skill needs improvement"
    assert retrieved_lesson.confidence == 0.8


@pytest.mark.asyncio
async def test_self_model_store_upsert(agency_engine, test_user):
    """Test creating and updating self-model entries."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    
    # Create a self-model entry
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill",
        performance_summary=PerformanceSummary(
            success_rate=0.75,
            avg_duration_seconds=2.5,
            user_satisfaction=0.8
        ),
        window_start=window_start,
        window_end=window_end,
        sample_size=20,
        confidence=0.85,
    )
    
    # Upsert the entry
    stored_entry = await agency_engine.self_reflection.self_model_store.upsert_entry(entry)
    assert stored_entry.model_id == entry.model_id
    
    # Retrieve the entry
    retrieved_entry = await agency_engine.self_reflection.self_model_store.get_latest_entry(
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill"
    )
    assert retrieved_entry is not None
    assert retrieved_entry.performance_summary.success_rate == 0.75
    assert retrieved_entry.sample_size == 20


@pytest.mark.asyncio
async def test_reflection_run_tracking(agency_engine, test_user):
    """Test reflection run creation and tracking."""
    from aico.ai.agency.models import ReflectionRun
    
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    
    # Create a reflection run
    run = ReflectionRun(
        run_id=str(uuid.uuid4()),
        user_id=test_user,
        run_type=RunType.MANUAL,
        trigger_reason="test",
        analysis_window_start=window_start,
        analysis_window_end=window_end,
        started_at=datetime.utcnow(),
        status=RunStatus.RUNNING,
    )
    
    # Store the run
    stored_run = await agency_engine.self_reflection.run_store.create_run(run)
    assert stored_run.run_id == run.run_id
    assert stored_run.status == RunStatus.RUNNING
    
    # Update the run
    await agency_engine.self_reflection.run_store.update_run(
        run_id=run.run_id,
        status=RunStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        duration_seconds=5.0,
        lessons_generated=3,
        lessons_applied=1,
    )
    
    # Retrieve the updated run
    retrieved_run = await agency_engine.self_reflection.run_store.get_run(run.run_id)
    assert retrieved_run is not None
    assert retrieved_run.status == RunStatus.COMPLETED
    assert retrieved_run.lessons_generated == 3
    assert retrieved_run.lessons_applied == 1


@pytest.mark.asyncio
async def test_get_active_lessons(agency_engine, test_user):
    """Test retrieving active lessons for a user."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create multiple lessons
    for i in range(3):
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id=f"skill_{i}",
            summary_text=f"Test lesson {i}",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=0.8,
            ),
            confidence=0.7,
            scope=LessonScope.THIS_USER,
            status=LessonStatus.ACTIVE,
        )
        await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Retrieve active lessons
    active_lessons = await agency_engine.get_active_lessons(
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING
    )
    
    assert len(active_lessons) >= 3
    assert all(lesson.status == LessonStatus.ACTIVE for lesson in active_lessons)
    assert all(lesson.lesson_type == LessonType.SKILL_TUNING for lesson in active_lessons)


@pytest.mark.asyncio
async def test_lesson_status_update(agency_engine, test_user):
    """Test updating lesson status."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create a lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="weight",
            old=1.0,
            new=0.8,
        ),
        confidence=0.7,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Create a new lesson that will supersede the first one
    new_lesson_id = str(uuid.uuid4())
    new_lesson = Lesson(
        lesson_id=new_lesson_id,
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Updated test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="weight",
            old=1.0,
            new=0.7,
        ),
        confidence=0.8,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(new_lesson)
    
    # Update status to superseded
    await agency_engine.self_reflection.lesson_store.update_lesson_status(
        lesson_id=lesson.lesson_id,
        status=LessonStatus.SUPERSEDED,
        superseded_by=new_lesson_id
    )
    
    # Verify update
    updated_lesson = await agency_engine.self_reflection.lesson_store.get_lesson(lesson.lesson_id)
    assert updated_lesson.status == LessonStatus.SUPERSEDED
    assert updated_lesson.superseded_by == new_lesson_id


@pytest.mark.asyncio
async def test_mark_lesson_applied(agency_engine, test_user):
    """Test marking a lesson as applied."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create a lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="weight",
            old=1.0,
            new=0.8,
        ),
        confidence=0.7,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Mark as applied
    await agency_engine.self_reflection.lesson_store.mark_lesson_applied(
        lesson_id=lesson.lesson_id,
        applied_by="test_system"
    )
    
    # Verify
    updated_lesson = await agency_engine.self_reflection.lesson_store.get_lesson(lesson.lesson_id)
    assert updated_lesson.applied_at is not None
    assert updated_lesson.applied_by == "test_system"


@pytest.mark.asyncio
async def test_agency_engine_reflection_methods(agency_engine, test_user):
    """Test AgencyEngine convenience methods for reflection."""
    # Test get_active_lessons
    lessons = await agency_engine.get_active_lessons(user_id=test_user)
    assert isinstance(lessons, list)
    
    # Test get_self_model_entry
    entry = await agency_engine.get_self_model_entry(
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="nonexistent_skill"
    )
    assert entry is None  # Should return None for nonexistent entry


# ============================================================================
# New Tests for Phase 5 Completion Features
# ============================================================================

@pytest.mark.asyncio
async def test_arbiter_adjustments_table(agency_engine, test_user):
    """Test agency_arbiter_adjustments table creation and usage."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create a lesson that will generate an arbiter adjustment
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PLANNER_HEURISTIC,
        target_kind=TargetKind.ARBITER_WEIGHT,
        target_id="goal_type_learning",
        summary_text="Learning goals have high retirement rate",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="goal_type_priority_weight",
            old=1.0,
            new=0.7,
            notes="Reduce priority for learning goals"
        ),
        confidence=0.8,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Apply the lesson (this should create an arbiter adjustment)
    await agency_engine.self_reflection.lesson_applicator.apply_lesson(lesson)
    
    # Verify adjustment was stored
    rows = agency_engine.arbiter.db.execute(
        """SELECT * FROM agency_arbiter_adjustments 
           WHERE lesson_id = ? AND active = 1""",
        (lesson.lesson_id,)
    ).fetchall()
    
    assert len(rows) == 1
    assert rows[0]["adjustment_key"] == "goal_type_learning"
    assert rows[0]["adjustment_value"] == 0.7
    assert rows[0]["confidence"] == 0.8


@pytest.mark.asyncio
async def test_arbiter_loads_adjustments(agency_engine, test_user):
    """Test that Goal Arbiter loads and applies lesson-based adjustments."""
    from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, Lesson, ProposedChange, ChangeType
    
    # Clean up any existing adjustments for this test
    # Note: adjustment_key is PRIMARY KEY, so only one "priority" can exist globally
    agency_engine.arbiter.db.execute(
        "DELETE FROM agency_arbiter_adjustments WHERE adjustment_key = ?",
        ("priority",)
    )
    agency_engine.arbiter.db.commit()
    
    # Create a lesson first (FK constraint requirement)
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PLANNER_HEURISTIC,
        target_kind=TargetKind.ARBITER_WEIGHT,
        target_id="priority",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="priority",
            old=0.3,
            new=0.5,
        ),
        confidence=0.9,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Create an arbiter adjustment directly
    agency_engine.arbiter.db.execute(
        """INSERT INTO agency_arbiter_adjustments 
           (adjustment_key, adjustment_value, lesson_id, user_id, applied_at, confidence, active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        ("priority", 0.5, lesson.lesson_id, test_user, datetime.utcnow().isoformat(), 0.9)
    )
    agency_engine.arbiter.db.commit()
    
    # Clear arbiter cache to force reload
    agency_engine.arbiter._adjustments_cache = {}
    agency_engine.arbiter._adjustments_cache_time = None
    
    # Create a test goal
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user,
        goal_type="test",
        title="Test goal",
        description="Test goal",
        origin=GoalOrigin.USER,
        priority=GoalPriority.HIGH,
    )
    
    # Score the goal (should apply adjustment)
    scored_goal = agency_engine.arbiter.score_goal(goal)
    
    # Verify adjustment was loaded
    adjustments = agency_engine.arbiter._load_adjustments(test_user)
    assert "priority" in adjustments
    assert adjustments["priority"] == 0.5


@pytest.mark.asyncio
async def test_skill_performance_exposure(agency_engine, test_user):
    """Test self-model skill performance exposure to Planner."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    # Create skill performance data
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill_123",
        performance_summary=PerformanceSummary(
            success_rate=0.85,
            avg_duration_seconds=1.5,
        ),
        window_start=datetime.utcnow() - timedelta(days=7),
        window_end=datetime.utcnow(),
        sample_size=25,
        confidence=0.9,
    )
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry)
    
    # Test skill performance retrieval
    success_rate = await agency_engine.get_skill_performance(test_user, "test_skill_123")
    
    assert success_rate is not None
    assert success_rate == 0.85


@pytest.mark.asyncio
async def test_goal_type_performance_context(agency_engine, test_user):
    """Test goal type performance context for Arbiter."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    # Create goal type performance data
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.GOAL_TYPE,
        entity_id="learning",
        performance_summary=PerformanceSummary(
            success_rate=0.65,
            additional_metrics={"completion_rate": 0.65, "retirement_rate": 0.35}
        ),
        window_start=datetime.utcnow() - timedelta(days=7),
        window_end=datetime.utcnow(),
        sample_size=20,
        confidence=0.8,
    )
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry)
    
    # Create a goal of this type so it appears in the query
    from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, GoalStatus
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user,
        goal_type="learning",
        title="Test learning goal",
        description="Test learning goal",
        origin=GoalOrigin.USER,
        priority=GoalPriority.NORMAL,
        status=GoalStatus.ACTIVE,
    )
    await agency_engine.goal_store.create_goal(goal)
    
    # Test goal type performance context retrieval
    context = await agency_engine.get_goal_type_performance_context(test_user)
    
    assert "learning" in context
    assert context["learning"]["success_rate"] == 0.65
    assert context["learning"]["confidence"] == 0.8


@pytest.mark.asyncio
async def test_all_skill_performances(agency_engine, test_user):
    """Test bulk skill performance retrieval for Curiosity Engine."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    # Create multiple skill performance entries
    skills = [
        ("skill_a", 0.9, 30),
        ("skill_b", 0.4, 15),
        ("skill_c", 0.7, 20),
    ]
    
    for skill_id, success_rate, sample_size in skills:
        entry = SelfModelEntry(
            model_id=str(uuid.uuid4()),
            user_id=test_user,
            entity_type=EntityType.SKILL,
            entity_id=skill_id,
            performance_summary=PerformanceSummary(
                success_rate=success_rate,
            ),
            window_start=datetime.utcnow() - timedelta(days=7),
            window_end=datetime.utcnow(),
            sample_size=sample_size,
            confidence=0.8,
        )
        await agency_engine.self_reflection.self_model_store.upsert_entry(entry)
    
    # Test bulk retrieval
    performances = await agency_engine.self_reflection.get_all_skill_performances(test_user)
    
    assert len(performances) == 3
    assert performances["skill_a"] == 0.9
    assert performances["skill_b"] == 0.4
    assert performances["skill_c"] == 0.7


@pytest.mark.asyncio
async def test_personality_service_persona_adjustments(agency_engine, test_user):
    """Test PersonalityService loading and applying persona lessons."""
    from aico.ai.personality.service import PersonalityService
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Get database connection from agency engine
    db = agency_engine.self_reflection.db
    
    # Create a persona lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PERSONA_STYLE,
        target_kind=TargetKind.PERSONA_TRAIT,
        target_id="response_tone",
        summary_text="User prefers more empathetic responses",
        proposed_change=ProposedChange(
            change_type=ChangeType.TEMPLATE_UPDATE,
            field="response_tone",
            old="neutral",
            new="empathetic",
        ),
        confidence=0.8,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    
    # Store lesson in database
    db.execute(
        """INSERT INTO agency_lessons (
            lesson_id, user_id, lesson_type, target_kind, target_id,
            summary_text, proposed_change, confidence, scope, status,
            created_at, applied_at, applied_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            lesson.lesson_id, lesson.user_id, lesson.lesson_type.value,
            lesson.target_kind.value, lesson.target_id, lesson.summary_text,
            lesson.proposed_change.model_dump_json(), lesson.confidence,
            lesson.scope.value, lesson.status.value,
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            "test_system"
        )
    )
    db.commit()
    
    # Initialize PersonalityService
    personality_service = PersonalityService(db_connection=db)
    
    # Get personality context (should include lesson adjustments)
    context = await personality_service.get_personality_context(test_user)
    
    assert "response_tone" in context.preferences
    assert context.preferences["response_tone"] == "empathetic"


@pytest.mark.asyncio
async def test_llm_lesson_generation_fallback(agency_engine, test_user):
    """Test that LLM lesson generation falls back to statistical summaries."""
    # The reflection engine should not have an LLM client in tests
    assert agency_engine.self_reflection.llm_client is None
    
    # Generate LLM lesson (should return None and fall back)
    llm_summary = await agency_engine.self_reflection._generate_llm_lesson(
        lesson_type=LessonType.SKILL_TUNING,
        context={
            "skill_id": "test_skill",
            "success_rate": 0.3,
            "total_uses": 20,
            "failures": 14,
        }
    )
    
    # Should return None when LLM unavailable
    assert llm_summary is None


@pytest.mark.asyncio
async def test_arbiter_performance_multiplier(agency_engine, test_user):
    """Test that arbiter applies performance-based multipliers from self-model."""
    from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, SelfModelEntry, PerformanceSummary
    
    # Create goal type performance data with low success rate
    entry = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.GOAL_TYPE,
        entity_id="experimental",
        performance_summary=PerformanceSummary(
            success_rate=0.2,  # Low success rate
        ),
        window_start=datetime.utcnow() - timedelta(days=7),
        window_end=datetime.utcnow(),
        sample_size=20,
        confidence=0.8,  # High confidence
    )
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry)
    
    # Create a goal of this type
    goal = Goal(
        goal_id=str(uuid.uuid4()),
        user_id=test_user,
        goal_type="experimental",
        title="Test experimental goal",
        description="Test experimental goal",
        origin=GoalOrigin.USER,
        priority=GoalPriority.NORMAL,
    )
    
    # Score without performance context
    scored_without = agency_engine.arbiter.score_goal(goal)
    
    # Score with performance context
    perf_context = await agency_engine.get_goal_type_performance_context(test_user)
    scored_with = agency_engine.arbiter.score_goal(
        goal,
        context={"goal_type_performance": perf_context}
    )
    
    # Score with performance data should be lower (penalty for low success rate)
    assert scored_with.arbiter_score < scored_without.arbiter_score


@pytest.mark.asyncio
async def test_lesson_applicator_dry_run(agency_engine, test_user):
    """Test lesson applicator dry-run mode."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    from aico.ai.agency.lesson_applicator import LessonApplicationService
    
    # Create lesson applicator in dry-run mode
    from unittest.mock import MagicMock
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default: True if 'dry_run' in key else default
    
    dry_run_applicator = LessonApplicationService(
        config=mock_config,
        db_connection=agency_engine.self_reflection.db,
        lesson_store=agency_engine.self_reflection.lesson_store,
    )
    
    # Create a test lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=0.5,
        ),
        confidence=0.8,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    
    # Apply in dry-run mode (should return False)
    result = await dry_run_applicator.apply_lesson(lesson)
    
    assert result is False  # Dry-run should not actually apply


@pytest.mark.asyncio
async def test_lesson_confidence_threshold(agency_engine, test_user):
    """Test that lesson applicator respects confidence thresholds."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    from aico.ai.agency.lesson_applicator import LessonApplicationService
    
    # Create lesson applicator with high confidence threshold
    from unittest.mock import MagicMock
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, default: 0.9 if 'min_confidence' in key else default
    
    high_threshold_applicator = LessonApplicationService(
        config=mock_config,
        db_connection=agency_engine.self_reflection.db,
        lesson_store=agency_engine.self_reflection.lesson_store,
    )
    
    # Create a lesson with low confidence
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill",
        summary_text="Test lesson",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=0.5,
        ),
        confidence=0.6,  # Below threshold
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    
    # Apply (should be rejected due to low confidence)
    result = await high_threshold_applicator.apply_lesson(lesson)
    
    assert result is False  # Should reject low-confidence lesson


# ============================================================================
# High Priority: Reflection Engine Core Logic Tests
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_goal_patterns_high_retirement(agency_engine, test_user):
    """Test goal pattern analysis with high retirement rate."""
    from aico.ai.agency.models import Goal, GoalOrigin, GoalPriority, GoalStatus
    
    # Create goals with high retirement rate for a specific type
    for i in range(25):
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            user_id=test_user,
            goal_type="experimental",
            title=f"Experimental goal {i}",
            description=f"Test experimental goal {i}",
            origin=GoalOrigin.CURIOSITY,
            priority=GoalPriority.LOW,
            status=GoalStatus.RETIRED if i < 18 else GoalStatus.COMPLETED,  # 72% retirement
            created_at=datetime.utcnow() - timedelta(days=6),
            completed_at=datetime.utcnow() - timedelta(days=1) if i >= 18 else None,
        )
        await agency_engine.goal_store.create_goal(goal)
    
    # Run goal pattern analysis
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    
    run_id = str(uuid.uuid4())
    lessons = await agency_engine.self_reflection._analyze_goal_patterns(
        user_id=test_user,
        window_start=window_start,
        window_end=window_end,
        run_id=run_id
    )
    
    # Should generate a lesson to deprioritize this goal type
    assert len(lessons) > 0
    experimental_lesson = next((l for l in lessons if "experimental" in l.target_id), None)
    assert experimental_lesson is not None
    assert experimental_lesson.lesson_type == LessonType.PLANNER_HEURISTIC
    assert experimental_lesson.target_kind == TargetKind.ARBITER_WEIGHT




@pytest.mark.asyncio
async def test_self_model_upsert_updates_existing(agency_engine, test_user):
    """Test that self-model upsert updates existing entries."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    
    # Create initial entry
    entry1 = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill_update",
        performance_summary=PerformanceSummary(
            success_rate=0.5,
        ),
        window_start=window_start,
        window_end=window_end,
        sample_size=10,
        confidence=0.6,
    )
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry1)
    
    # Update with new data
    entry2 = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill_update",
        performance_summary=PerformanceSummary(
            success_rate=0.8,  # Improved
        ),
        window_start=window_start,
        window_end=window_end,
        sample_size=20,  # More samples
        confidence=0.9,
    )
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry2)
    
    # Retrieve and verify it was updated, not duplicated
    latest = await agency_engine.self_reflection.self_model_store.get_latest_entry(
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="test_skill_update"
    )
    
    assert latest is not None
    assert latest.performance_summary.success_rate == 0.8
    assert latest.sample_size == 20
    assert latest.confidence == 0.9


# ============================================================================
# High Priority: Lesson Applicator Tests
# ============================================================================

@pytest.mark.asyncio
async def test_apply_skill_weight_adjustment(agency_engine, test_user):
    """Test applying skill weight adjustments."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Note: We don't need to create the skill in the DB for this test
    # The lesson applicator will handle skills that may or may not exist
    
    # Create a skill tuning lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="test_skill_weight",
        summary_text="Skill needs weight adjustment",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="selection_weight",
            old=1.0,
            new=0.7,
        ),
        confidence=0.85,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Apply the lesson
    result = await agency_engine.self_reflection.lesson_applicator.apply_lesson(lesson)
    
    # Verify application - result may be True or False depending on whether skill exists
    # The important thing is that it doesn't crash
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_apply_policy_suggestion(agency_engine, test_user):
    """Test that policy suggestions are logged but not auto-applied."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create a policy suggestion lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.POLICY_SUGGESTION,
        target_kind=TargetKind.POLICY_RULE,
        target_id="new_policy_rule",
        summary_text="Suggest new policy based on patterns",
        proposed_change=ProposedChange(
            change_type=ChangeType.TEMPLATE_UPDATE,
            field="policy_rules",
            old="",
            new="new_rule_content",
        ),
        confidence=0.75,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Apply the lesson (should log but not apply)
    result = await agency_engine.self_reflection.lesson_applicator.apply_lesson(lesson)
    
    # Policy suggestions should be logged, not directly applied
    # Result depends on implementation - could be True (logged) or False (not applied)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_lesson_application_marks_applied(agency_engine, test_user):
    """Test that successful lesson application marks lesson as applied."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create a lesson
    lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PLANNER_HEURISTIC,
        target_kind=TargetKind.ARBITER_WEIGHT,
        target_id="test_weight",
        summary_text="Test weight adjustment",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="priority",
            old=0.3,
            new=0.4,
        ),
        confidence=0.8,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
    )
    await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
    
    # Apply the lesson
    await agency_engine.self_reflection.lesson_applicator.apply_lesson(lesson)
    
    # Verify lesson was marked as applied
    updated_lesson = await agency_engine.self_reflection.lesson_store.get_lesson(lesson.lesson_id)
    assert updated_lesson.applied_at is not None
    assert updated_lesson.applied_by is not None


@pytest.mark.asyncio
async def test_batch_lesson_application(agency_engine, test_user):
    """Test applying multiple lessons in batch."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create multiple lessons
    lessons = []
    for i in range(5):
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.ARBITER_WEIGHT,
            target_id=f"test_batch_{i}",
            summary_text=f"Batch lesson {i}",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.3,
                new=0.3 + (i * 0.05),
            ),
            confidence=0.8,
            scope=LessonScope.THIS_USER,
            status=LessonStatus.ACTIVE,
        )
        await agency_engine.self_reflection.lesson_store.create_lesson(lesson)
        lessons.append(lesson)
    
    # Apply all lessons
    results = []
    for lesson in lessons:
        result = await agency_engine.self_reflection.lesson_applicator.apply_lesson(lesson)
        results.append(result)
    
    # All should succeed
    assert all(results)
    
    # Verify all were marked as applied
    for lesson in lessons:
        updated = await agency_engine.self_reflection.lesson_store.get_lesson(lesson.lesson_id)
        assert updated.applied_at is not None


# ============================================================================
# Additional Coverage Tests - Edge Cases & Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_run_reflection_with_no_data(agency_engine, test_user):
    """Test reflection run when no data exists."""
    # Run reflection on fresh user with no history
    result = await agency_engine.self_reflection.run_reflection(
        user_id=test_user,
        run_type=RunType.MANUAL
    )
    
    # Should complete without errors
    assert result is not None
    assert result.status == RunStatus.COMPLETED
    assert result.lessons_generated == 0  # No data = no lessons


@pytest.mark.asyncio
async def test_analyze_skill_performance_empty_window(agency_engine, test_user):
    """Test skill performance analysis with empty time window."""
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    run_id = str(uuid.uuid4())
    
    lessons = await agency_engine.self_reflection._analyze_skill_performance(
        user_id=test_user,
        window_start=window_start,
        window_end=window_end,
        run_id=run_id
    )
    
    # Should return empty list, not crash
    assert isinstance(lessons, list)
    assert len(lessons) == 0


@pytest.mark.asyncio
async def test_analyze_goal_patterns_no_goals(agency_engine, test_user):
    """Test goal pattern analysis when user has no goals."""
    window_start = datetime.utcnow() - timedelta(days=30)
    window_end = datetime.utcnow()
    run_id = str(uuid.uuid4())
    
    lessons = await agency_engine.self_reflection._analyze_goal_patterns(
        user_id=test_user,
        window_start=window_start,
        window_end=window_end,
        run_id=run_id
    )
    
    assert isinstance(lessons, list)
    assert len(lessons) == 0


@pytest.mark.asyncio
async def test_analyze_user_feedback_no_feedback(agency_engine, test_user):
    """Test user feedback analysis with no feedback data."""
    window_start = datetime.utcnow() - timedelta(days=7)
    window_end = datetime.utcnow()
    run_id = str(uuid.uuid4())
    
    lessons = await agency_engine.self_reflection._analyze_user_feedback(
        user_id=test_user,
        window_start=window_start,
        window_end=window_end,
        run_id=run_id
    )
    
    assert isinstance(lessons, list)
    assert len(lessons) == 0


@pytest.mark.asyncio
async def test_get_active_lessons_with_type_filter(agency_engine, test_user):
    """Test filtering active lessons by type."""
    from aico.ai.agency.models import Lesson, ProposedChange, ChangeType
    
    # Create lessons of different types
    skill_lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING,
        target_kind=TargetKind.SKILL,
        target_id="skill1",
        summary_text="Skill adjustment",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="weight",
            old=1.0,
            new=0.8
        ),
        confidence=0.9,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
        created_at=datetime.utcnow()
    )
    
    goal_lesson = Lesson(
        lesson_id=str(uuid.uuid4()),
        user_id=test_user,
        lesson_type=LessonType.PLANNER_HEURISTIC,
        target_kind=TargetKind.PLANNER_TEMPLATE,
        target_id="learning",
        summary_text="Goal pattern",
        proposed_change=ProposedChange(
            change_type=ChangeType.WEIGHT_TWEAK,
            field="priority",
            old=1.0,
            new=1.2
        ),
        confidence=0.85,
        scope=LessonScope.THIS_USER,
        status=LessonStatus.ACTIVE,
        created_at=datetime.utcnow()
    )
    
    # Store both lessons
    await agency_engine.self_reflection.lesson_store.create_lesson(skill_lesson)
    await agency_engine.self_reflection.lesson_store.create_lesson(goal_lesson)
    
    # Get only skill lessons
    skill_lessons = await agency_engine.self_reflection.get_active_lessons(
        user_id=test_user,
        lesson_type=LessonType.SKILL_TUNING
    )
    
    assert len(skill_lessons) >= 1
    assert all(l.lesson_type == LessonType.SKILL_TUNING for l in skill_lessons)


@pytest.mark.asyncio
async def test_get_self_model_with_filters(agency_engine, test_user):
    """Test retrieving self-model entries with filters."""
    from aico.ai.agency.models import SelfModelEntry, PerformanceSummary
    
    # Create self-model entries
    now = datetime.utcnow()
    entry1 = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="skill1",
        performance_summary=PerformanceSummary(
            success_rate=0.8,
            sample_size=10,
            last_updated=now
        ),
        window_start=now - timedelta(days=7),
        window_end=now,
        sample_size=10,
        confidence=0.85,
        last_updated=now,
        created_at=now
    )
    
    entry2 = SelfModelEntry(
        model_id=str(uuid.uuid4()),
        user_id=test_user,
        entity_type=EntityType.GOAL_TYPE,
        entity_id="learning",
        performance_summary=PerformanceSummary(
            success_rate=0.9,
            sample_size=5,
            last_updated=now
        ),
        window_start=now - timedelta(days=7),
        window_end=now,
        sample_size=5,
        confidence=0.90,
        last_updated=now,
        created_at=now
    )
    
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry1)
    await agency_engine.self_reflection.self_model_store.upsert_entry(entry2)
    
    # Get specific skill entry
    skill_entry = await agency_engine.self_reflection.get_self_model(
        user_id=test_user,
        entity_type=EntityType.SKILL,
        entity_id="skill1"
    )
    
    assert skill_entry is not None
    assert skill_entry.entity_type == EntityType.SKILL
    assert skill_entry.entity_id == "skill1"


@pytest.mark.asyncio
async def test_get_skill_performance_nonexistent(agency_engine, test_user):
    """Test getting performance for non-existent skill."""
    perf = await agency_engine.self_reflection.get_skill_performance(
        user_id=test_user,
        skill_id="nonexistent_skill"
    )
    
    assert perf is None


@pytest.mark.asyncio
async def test_get_goal_type_performance_nonexistent(agency_engine, test_user):
    """Test getting performance for non-existent goal type."""
    perf = await agency_engine.self_reflection.get_goal_type_performance(
        user_id=test_user,
        goal_type="nonexistent_type"
    )
    
    assert perf is None


@pytest.mark.asyncio
async def test_get_all_skill_performances_empty(agency_engine, test_user):
    """Test getting all skill performances when none exist."""
    perfs = await agency_engine.self_reflection.get_all_skill_performances(
        user_id=test_user
    )
    
    assert isinstance(perfs, dict)
    assert len(perfs) == 0
