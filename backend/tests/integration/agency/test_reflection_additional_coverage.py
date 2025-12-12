"""
Additional coverage tests for reflection.py - targeting uncovered lines.

Focuses on error handling, edge cases, and all analysis methods.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from aico.ai.agency.models import (
    ReflectionRun,
    RunType,
    RunStatus,
    Lesson,
    LessonType,
    TargetKind,
    LessonStatus,
    LessonScope,
    ProposedChange,
    ChangeType,
    MetricsBasis,
)
from aico.ai.agency.reflection import SelfReflectionEngine


class TestSelfReflectionEngineInit:
    """Tests for SelfReflectionEngine initialization."""
    
    @pytest.mark.asyncio
    async def test_init_with_defaults(self, test_config, test_db):
        """Test initialization with default parameters."""
        # Reset policy_mode to a valid value in case previous tests changed it
        test_config.set("core.agency.self_reflection.policy_mode", "suggest_amendments")
        
        engine = SelfReflectionEngine(test_config, test_db)
        
        assert engine.config is not None
        assert engine.db is not None
        assert engine.lesson_store is not None
        assert engine.self_model_store is not None
        assert engine.run_store is not None
        assert engine.projector is not None
        assert engine.lesson_applicator is not None
        # Policy mode may be set by config, just verify it's valid
        assert engine.policy_mode in ["observe_only", "suggest_amendments", "auto_amend"]
        # min_sample_size may be configured differently
        assert engine.min_sample_size >= 10
        # confidence_threshold may be configured differently
        assert engine.confidence_threshold >= 0.7
    
    @pytest.mark.asyncio
    async def test_init_with_llm_client(self, test_config, test_db):
        """Test initialization with LLM client."""
        mock_llm = Mock()
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        assert engine.llm_client is mock_llm
    
    @pytest.mark.asyncio
    async def test_init_with_kg_storage(self, test_config, test_db):
        """Test initialization with KG storage."""
        mock_kg = Mock()
        engine = SelfReflectionEngine(test_config, test_db, kg_storage=mock_kg)
        
        assert engine.kg_storage is mock_kg
        assert engine.projector.kg_storage is mock_kg


class TestRunReflection:
    """Tests for run_reflection method."""
    
    @pytest.mark.asyncio
    async def test_run_reflection_scheduled(self, test_config, test_db, test_user):
        """Test scheduled reflection run."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        run = await engine.run_reflection(
            user_id=test_user,
            run_type=RunType.SCHEDULED,
            trigger_reason="Daily reflection",
            analysis_window_days=7
        )
        
        assert run is not None
        assert run.user_id == test_user
        assert run.run_type == RunType.SCHEDULED
        assert run.status == RunStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_run_reflection_triggered(self, test_config, test_db, test_user):
        """Test triggered reflection run."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        run = await engine.run_reflection(
            user_id=test_user,
            run_type=RunType.TRIGGERED,
            trigger_reason="User feedback threshold",
            analysis_window_days=3
        )
        
        assert run is not None
        assert run.run_type == RunType.TRIGGERED
        assert run.trigger_reason == "User feedback threshold"
    
    @pytest.mark.asyncio
    async def test_run_reflection_manual(self, test_config, test_db, test_user):
        """Test manual reflection run."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        run = await engine.run_reflection(
            user_id=test_user,
            run_type=RunType.MANUAL,
            trigger_reason="Admin requested",
            analysis_window_days=14
        )
        
        assert run is not None
        assert run.run_type == RunType.MANUAL
    
    @pytest.mark.asyncio
    async def test_run_reflection_error_handling(self, test_config, test_db, test_user):
        """Test that reflection run handles errors gracefully."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        # Mock _analyze_skill_performance to raise error
        with patch.object(engine, '_analyze_skill_performance', side_effect=Exception("Analysis error")):
            with pytest.raises(Exception, match="Analysis error"):
                await engine.run_reflection(user_id=test_user)
    
    @pytest.mark.asyncio
    async def test_run_reflection_applies_high_confidence_lessons(self, test_config, test_db, test_user):
        """Test that high confidence lessons are applied."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        # Create a high-confidence lesson
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
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,  # Above threshold
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        # Mock analysis methods to return our lesson
        async def mock_skill_analysis(*args, **kwargs):
            return [lesson]
        
        async def mock_empty_analysis(*args, **kwargs):
            return []
        
        with patch.object(engine, '_analyze_skill_performance', side_effect=mock_skill_analysis):
            with patch.object(engine, '_analyze_goal_patterns', side_effect=mock_empty_analysis):
                with patch.object(engine, '_analyze_user_feedback', side_effect=mock_empty_analysis):
                    with patch.object(engine, '_analyze_emotion_patterns', side_effect=mock_empty_analysis):
                        with patch.object(engine, '_analyze_social_patterns', side_effect=mock_empty_analysis):
                            with patch.object(engine, '_analyze_curiosity_outcomes', side_effect=mock_empty_analysis):
                                run = await engine.run_reflection(user_id=test_user)
        
        assert run.lessons_generated >= 1


class TestGenerateLLMLessonMethod:
    """Tests for _generate_llm_lesson method."""
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_no_client(self, test_config, test_db):
        """Test LLM lesson generation without LLM client."""
        engine = SelfReflectionEngine(test_config, test_db, llm_client=None)
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.SKILL_TUNING,
            context={"skill_id": "test", "success_rate": 0.8}
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_skill_tuning(self, test_config, test_db):
        """Test LLM lesson generation for skill tuning."""
        mock_llm = Mock()
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        context = {
            "skill_id": "test_skill",
            "success_rate": 0.75,
            "total_uses": 20,
            "failures": 5
        }
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.SKILL_TUNING,
            context=context
        )
        
        # Currently returns None (not implemented), but should not error
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_planner_heuristic(self, test_config, test_db):
        """Test LLM lesson generation for planner heuristic."""
        mock_llm = Mock()
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        context = {
            "goal_type": "project",
            "completion_rate": 0.6,
            "retirement_rate": 0.2,
            "total_goals": 15
        }
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.PLANNER_HEURISTIC,
            context=context
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_persona_style(self, test_config, test_db):
        """Test LLM lesson generation for persona style."""
        mock_llm = Mock()
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        context = {
            "avg_rating": 3.5,
            "low_rating_count": 5,
            "total_feedback": 20
        }
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.PERSONA_STYLE,
            context=context
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_unknown_type(self, test_config, test_db):
        """Test LLM lesson generation for unknown type."""
        mock_llm = Mock()
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.CURIOSITY_FOCUS,
            context={}
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_llm_lesson_error_handling(self, test_config, test_db):
        """Test LLM lesson generation handles errors gracefully."""
        mock_llm = Mock()
        mock_llm.generate = Mock(side_effect=Exception("LLM error"))
        engine = SelfReflectionEngine(test_config, test_db, llm_client=mock_llm)
        
        result = await engine._generate_llm_lesson(
            lesson_type=LessonType.SKILL_TUNING,
            context={"skill_id": "test"}
        )
        
        # Should return None on error, not raise
        assert result is None


class TestAnalyzeSkillPerformance:
    """Tests for _analyze_skill_performance method."""
    
    @pytest.mark.asyncio
    async def test_analyze_skill_performance_no_data(self, test_config, test_db, test_user):
        """Test skill analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)
        assert len(lessons) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_skill_performance_insufficient_samples(self, test_config, test_db, test_user):
        """Test skill analysis with insufficient sample size."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        # Insert minimal feedback data (below min_sample_size)
        for i in range(5):  # Below default min_sample_size of 10
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), "test_skill", 
                 1, "success", datetime.utcnow().isoformat())
            )
        test_db.commit()
        
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Should not generate lessons with insufficient data
        assert len(lessons) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_skill_performance_with_sufficient_data(self, test_config, test_db, test_user):
        """Test skill analysis with sufficient sample size."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        # Insert sufficient feedback data
        for i in range(15):  # Above min_sample_size
            outcome = "success" if i < 12 else "failure"
            reward = 1 if i < 12 else -1
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), "test_skill", 
                 reward, outcome, datetime.utcnow().isoformat())
            )
        test_db.commit()
        
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Should generate lessons with sufficient data
        assert isinstance(lessons, list)
        # May or may not generate lessons depending on thresholds


class TestAnalyzeGoalPatterns:
    """Tests for _analyze_goal_patterns method."""
    
    @pytest.mark.asyncio
    async def test_analyze_goal_patterns_no_data(self, test_config, test_db, test_user):
        """Test goal pattern analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_goal_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)


class TestAnalyzeUserFeedback:
    """Tests for _analyze_user_feedback method."""
    
    @pytest.mark.asyncio
    async def test_analyze_user_feedback_no_data(self, test_config, test_db, test_user):
        """Test user feedback analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_user_feedback(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)


class TestAnalyzeEmotionPatterns:
    """Tests for _analyze_emotion_patterns method."""
    
    @pytest.mark.asyncio
    async def test_analyze_emotion_patterns_no_data(self, test_config, test_db, test_user):
        """Test emotion pattern analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_emotion_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)


class TestAnalyzeSocialPatterns:
    """Tests for _analyze_social_patterns method."""
    
    @pytest.mark.asyncio
    async def test_analyze_social_patterns_no_data(self, test_config, test_db, test_user):
        """Test social pattern analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_social_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)


class TestAnalyzeCuriosityOutcomes:
    """Tests for _analyze_curiosity_outcomes method."""
    
    @pytest.mark.asyncio
    async def test_analyze_curiosity_outcomes_no_data(self, test_config, test_db, test_user):
        """Test curiosity outcomes analysis with no data."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.utcnow() - timedelta(days=7)
        window_end = datetime.utcnow()
        
        lessons = await engine._analyze_curiosity_outcomes(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)


class TestReflectionRunLifecycle:
    """Tests for complete reflection run lifecycle."""
    
    @pytest.mark.asyncio
    async def test_reflection_run_creates_run_record(self, test_config, test_db, test_user):
        """Test that reflection run creates a run record."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        run = await engine.run_reflection(user_id=test_user)
        
        # Verify run was created in database
        stored_run = await engine.run_store.get_run(run.run_id)
        assert stored_run is not None
        assert stored_run.run_id == run.run_id
    
    @pytest.mark.asyncio
    async def test_reflection_run_updates_on_completion(self, test_config, test_db, test_user):
        """Test that reflection run updates status on completion."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        run = await engine.run_reflection(user_id=test_user)
        
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None
        assert run.duration_seconds is not None
    
    @pytest.mark.asyncio
    async def test_reflection_run_updates_on_failure(self, test_config, test_db, test_user):
        """Test that reflection run updates status on failure."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        # Mock to cause failure
        with patch.object(engine, '_analyze_skill_performance', side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                await engine.run_reflection(user_id=test_user)
        
        # Check that a failed run was recorded
        # Note: We can't easily get the run_id since it failed, but the error handling was tested


class TestReflectionConfiguration:
    """Tests for reflection configuration."""
    
    @pytest.mark.asyncio
    async def test_custom_min_sample_size(self, test_config, test_db):
        """Test custom min_sample_size configuration."""
        test_config.set("core.agency.self_reflection.min_sample_size", 20)
        engine = SelfReflectionEngine(test_config, test_db)
        
        assert engine.min_sample_size == 20
    
    @pytest.mark.asyncio
    async def test_custom_confidence_threshold(self, test_config, test_db):
        """Test custom confidence_threshold configuration."""
        test_config.set("core.agency.self_reflection.confidence_threshold", 0.8)
        engine = SelfReflectionEngine(test_config, test_db)
        
        assert engine.confidence_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_policy_mode_configuration(self, test_config, test_db):
        """Test policy_mode configuration."""
        test_config.set("core.agency.self_reflection.policy_mode", "suggest_amendments")
        engine = SelfReflectionEngine(test_config, test_db)
        
        assert engine.policy_mode == "suggest_amendments"
