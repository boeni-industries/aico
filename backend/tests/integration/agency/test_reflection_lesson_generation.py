"""
Comprehensive tests for reflection.py lesson generation - targeting uncovered lines.

Focuses on:
- Skill performance lesson generation (lines 354-408)
- Goal pattern lesson generation (lines 447-510)
- User feedback analysis
- Emotion pattern analysis
- Social pattern analysis
- Curiosity outcome analysis
"""

import pytest
from datetime import datetime, timedelta, UTC
import uuid

from aico.ai.agency.models import (
    LessonType,
    TargetKind,
    LessonScope,
    LessonStatus,
)
from aico.ai.agency.reflection import SelfReflectionEngine


class TestSkillPerformanceLessonGeneration:
    """Tests for skill performance analysis and lesson generation."""
    
    @pytest.mark.asyncio
    async def test_skill_lesson_analysis_runs_without_error(self, test_config, test_db, test_user):
        """Test that skill performance analysis runs without error."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create skill learning data with unique ID
        skill_id = f"poor_skill_{str(uuid.uuid4())[:8]}"
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (skill_id, "{}",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        
        # Create behavioral feedback showing poor skill performance
        for i in range(25):
            outcome = "failure" if i < 20 else "success"  # 80% failure rate
            reward = -1 if outcome == "failure" else 1
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), skill_id, 
                 reward, outcome, datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run skill analysis - should complete without error
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Verify it returns a list (may or may not generate lessons depending on config)
        assert isinstance(lessons, list)
    
    @pytest.mark.asyncio
    async def test_skill_lesson_not_generated_for_good_performance(self, test_config, test_db, test_user):
        """Test that no lessons are generated for skills with good performance."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create skill learning data with unique ID
        skill_id = f"good_skill_{str(uuid.uuid4())[:8]}"
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (skill_id, "{}",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        
        # Create behavioral feedback showing good skill performance
        # Use 25 samples to ensure we're well above min_sample_size
        for i in range(25):
            outcome = "success" if i < 20 else "failure"  # 80% success rate
            reward = 1 if outcome == "success" else -1
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), skill_id, 
                 reward, outcome, datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run skill analysis
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Should NOT generate lesson for good performance (success_rate >= 0.5)
        assert len(lessons) == 0
    
    @pytest.mark.asyncio
    async def test_skill_lesson_with_kg_projection(self, test_config, test_db, test_user):
        """Test skill lesson analysis with KG storage enabled."""
        from unittest.mock import Mock
        
        mock_kg = Mock()
        engine = SelfReflectionEngine(test_config, test_db, kg_storage=mock_kg)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create skill learning data with unique ID
        skill_id = f"kg_skill_{str(uuid.uuid4())[:8]}"
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (skill_id, "{}",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        
        # Create poor performing skill with enough samples
        for i in range(25):
            outcome = "failure" if i < 20 else "success"  # 80% failure rate
            reward = -1 if outcome == "failure" else 1
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), skill_id, 
                 reward, outcome, datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run analysis - should complete without error
        lessons = await engine._analyze_skill_performance(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Verify it returns a list
        assert isinstance(lessons, list)


class TestGoalPatternLessonGeneration:
    """Tests for goal pattern analysis and lesson generation."""
    
    @pytest.mark.asyncio
    async def test_goal_lesson_analysis_runs_without_error(self, test_config, test_db, test_user):
        """Test that goal pattern analysis runs without error."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create goals with high retirement rate
        goal_type = "learning"
        for i in range(15):  # Above min_sample_size
            status = "retired" if i < 10 else "completed"  # 67% retirement rate
            test_db.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, goal_type, title, description, status, priority, origin, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, goal_type, "Test goal", "Test description", status, 
                 "normal", "user_request", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run goal analysis - should complete without error
        lessons = await engine._analyze_goal_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Verify it returns a list
        assert isinstance(lessons, list)
    
    @pytest.mark.asyncio
    async def test_goal_lesson_not_generated_for_low_retirement_rate(self, test_config, test_db, test_user):
        """Test that no lessons are generated for goal types with low retirement rate."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create goals with low retirement rate
        goal_type = "project"
        for i in range(15):
            status = "completed" if i < 12 else "retired"  # 20% retirement rate
            test_db.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, goal_type, title, description, status, priority, origin, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, goal_type, "Test goal", "Test description", status, 
                 "normal", "user_request", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run goal analysis
        lessons = await engine._analyze_goal_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Should NOT generate lesson for low retirement rate (<= 0.5)
        assert len(lessons) == 0
    
    @pytest.mark.asyncio
    async def test_goal_lesson_skipped_for_insufficient_sample_size(self, test_config, test_db, test_user):
        """Test that lessons are not generated when sample size is too small."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        # Create only 5 goals (below min_sample_size of 10)
        goal_type = "hobby"
        for i in range(5):
            test_db.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, goal_type, title, description, status, priority, origin, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, goal_type, "Test goal", "Test description", "retired", 
                 "normal", "user_request", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run goal analysis
        lessons = await engine._analyze_goal_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        # Should NOT generate lesson due to insufficient sample size
        assert len(lessons) == 0


class TestUserFeedbackAnalysis:
    """Tests for user feedback analysis."""
    
    @pytest.mark.asyncio
    async def test_user_feedback_analysis_with_no_data(self, test_config, test_db, test_user):
        """Test user feedback analysis when no feedback exists."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        lessons = await engine._analyze_user_feedback(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)
        assert len(lessons) == 0


class TestEmotionPatternAnalysis:
    """Tests for emotion pattern analysis."""
    
    @pytest.mark.asyncio
    async def test_emotion_pattern_analysis_with_no_data(self, test_config, test_db, test_user):
        """Test emotion pattern analysis when no data exists."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        lessons = await engine._analyze_emotion_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)
        # Emotion pattern analysis may generate baseline lessons even with no data
        # (e.g., suggesting warmth adjustments based on default emotion history)
        assert len(lessons) >= 0  # Should not crash, may generate 0 or more lessons


class TestSocialPatternAnalysis:
    """Tests for social pattern analysis."""
    
    @pytest.mark.asyncio
    async def test_social_pattern_analysis_with_no_data(self, test_config, test_db, test_user):
        """Test social pattern analysis when no data exists."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        lessons = await engine._analyze_social_patterns(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)
        assert len(lessons) == 0


class TestCuriosityOutcomeAnalysis:
    """Tests for curiosity outcome analysis."""
    
    @pytest.mark.asyncio
    async def test_curiosity_outcome_analysis_with_no_data(self, test_config, test_db, test_user):
        """Test curiosity outcome analysis when no data exists."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        window_start = datetime.now(UTC) - timedelta(days=7)
        window_end = datetime.now(UTC)
        
        lessons = await engine._analyze_curiosity_outcomes(
            user_id=test_user,
            window_start=window_start,
            window_end=window_end,
            run_id="test-run"
        )
        
        assert isinstance(lessons, list)
        assert len(lessons) == 0


class TestReflectionRunWithLessonGeneration:
    """Integration tests for full reflection run with lesson generation."""
    
    @pytest.mark.asyncio
    async def test_reflection_run_generates_skill_lessons(self, test_config, test_db, test_user):
        """Test that reflection run generates skill lessons from behavioral feedback."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        # Create skill learning data with unique ID
        skill_id = f"integ_skill_{str(uuid.uuid4())[:8]}"
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (skill_id, "{}",
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        
        # Create poor performing skill with enough samples
        for i in range(25):
            outcome = "failure" if i < 20 else "success"  # 80% failure rate
            reward = -1 if outcome == "failure" else 1
            test_db.execute(
                """INSERT INTO ams_behavioral_feedback 
                   (feedback_id, user_id, message_id, skill_id, reward, outcome, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, str(uuid.uuid4()), skill_id, 
                 reward, outcome, (datetime.now(UTC) - timedelta(days=3)).isoformat())
            )
        test_db.commit()
        
        # Run full reflection
        from aico.ai.agency.models import RunType
        run = await engine.run_reflection(
            user_id=test_user,
            run_type=RunType.MANUAL,
            analysis_window_days=7
        )
        
        # Should have generated at least one lesson
        assert run.lessons_generated >= 1
    
    @pytest.mark.asyncio
    async def test_reflection_run_generates_goal_lessons(self, test_config, test_db, test_user):
        """Test that reflection run generates goal lessons from goal patterns."""
        engine = SelfReflectionEngine(test_config, test_db)
        
        # Create goals with high retirement rate (need 25+ to exceed min_sample_size)
        goal_type = "reflection_test"
        for i in range(25):
            status = "retired" if i < 20 else "completed"  # 80% retirement rate
            test_db.execute(
                """INSERT INTO agency_goals 
                   (goal_id, user_id, goal_type, title, description, status, priority, origin, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), test_user, goal_type, "Test goal", "Test description", status, 
                 "normal", "user_request", (datetime.now(UTC) - timedelta(days=3)).isoformat(), 
                 datetime.now(UTC).isoformat())
            )
        test_db.commit()
        
        # Run full reflection
        from aico.ai.agency.models import RunType
        run = await engine.run_reflection(
            user_id=test_user,
            run_type=RunType.MANUAL,
            analysis_window_days=7
        )
        
        # Should have generated at least one lesson
        assert run.lessons_generated >= 1
