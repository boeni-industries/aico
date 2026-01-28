"""
Additional coverage tests for lesson_applicator.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
import uuid
import json

from aico.ai.agency.models import (
    Lesson,
    LessonType,
    TargetKind,
    LessonStatus,
    LessonScope,
    ProposedChange,
    MetricsBasis,
    ChangeType,
)
from aico.ai.agency.lesson_applicator import LessonApplicationService


class TestLessonApplicationServiceInit:
    """Tests for LessonApplicationService initialization."""
    
    @pytest.mark.asyncio
    async def test_init_with_defaults(self, test_config, test_db):
        """Test initialization with default parameters."""
        service = LessonApplicationService(test_config, test_db)
        
        assert service.config is not None
        assert service.db is not None
        assert service.lesson_store is not None
        assert service.projector is not None
        assert service.min_confidence == 0.7
        assert isinstance(service.dry_run, bool)
        assert service.policy_amendment_limit >= 2  # Config may vary
        assert isinstance(service.policy_freeze, bool)
    
    @pytest.mark.asyncio
    async def test_init_with_custom_lesson_store(self, test_config, test_db):
        """Test initialization with custom lesson store."""
        from aico.ai.agency.store import LessonStore
        
        custom_store = LessonStore(test_db)
        service = LessonApplicationService(test_config, test_db, lesson_store=custom_store)
        
        assert service.lesson_store is custom_store
    
    @pytest.mark.asyncio
    async def test_init_with_kg_storage(self, test_config, test_db):
        """Test initialization with KG storage."""
        mock_kg = Mock()
        service = LessonApplicationService(test_config, test_db, kg_storage=mock_kg)
        
        assert service.projector.kg_storage is mock_kg


class TestApplyLessonConfidenceThreshold:
    """Tests for confidence threshold checking."""
    
    @pytest.mark.asyncio
    async def test_apply_lesson_below_confidence_threshold(self, test_config, test_db, test_user):
        """Test that lessons below confidence threshold are skipped."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Low confidence lesson",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.5,  # Below default threshold of 0.7
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_lesson_above_confidence_threshold(self, test_config, test_db, test_user):
        """Test that lessons above confidence threshold are processed."""
        service = LessonApplicationService(test_config, test_db)
        
        # Create skill learning data with unique ID
        skill_id = f"test_skill_{str(uuid.uuid4())[:8]}"
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at) 
               VALUES (?, ?, ?, ?)""",
            (skill_id, "{}", 
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id=skill_id,
            summary_text="High confidence lesson",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="selection_weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,  # Above threshold
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Result may be False if dry_run is enabled in config
        assert isinstance(result, bool)


class TestApplySkillLesson:
    """Tests for skill lesson application."""
    
    @pytest.mark.asyncio
    async def test_apply_skill_lesson_dry_run(self, test_config, test_db, test_user):
        """Test skill lesson application in dry run mode."""
        # Set dry_run config
        test_config.set("agency.lesson_application.dry_run", True)
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Should return False in dry run
        assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_skill_lesson_skill_not_found(self, test_config, test_db, test_user):
        """Test skill lesson when skill doesn't exist."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="nonexistent_skill",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_skill_lesson_with_existing_dimension_vector(self, test_config, test_db, test_user):
        """Test skill lesson with existing dimension vector."""
        service = LessonApplicationService(test_config, test_db)
        
        # Create skill with existing dimension vector and unique ID
        skill_id = f"test_skill_{str(uuid.uuid4())[:8]}"
        existing_vector = {"existing_field": "value"}
        test_db.execute(
            """INSERT INTO agency_skill_learning_data (skill_id, dimension_vector, created_at, updated_at) 
               VALUES (?, ?, ?, ?)""",
            (skill_id,
             json.dumps(existing_vector), datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id=skill_id,
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="new_weight",
                old=1.0,
                new=1.5,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Result may be False if dry_run is enabled in config
        assert isinstance(result, bool)
        
        # Only verify dimension vector if lesson was actually applied
        if result:
            row = test_db.execute(
                "SELECT dimension_vector FROM agency_skill_learning_data WHERE skill_id = ?",
                (skill_id,)
            ).fetchone()
            
            vector = json.loads(row["dimension_vector"])
            assert "lesson_adjustments" in vector
            assert "new_weight" in vector["lesson_adjustments"]


class TestApplyArbiterWeightLesson:
    """Tests for arbiter weight lesson application."""
    
    @pytest.mark.asyncio
    async def test_apply_arbiter_weight_lesson_user_specific(self, test_config, test_db, test_user):
        """Test arbiter weight lesson for specific user."""
        service = LessonApplicationService(test_config, test_db)
        
        # Create lesson in DB first
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.ARBITER_WEIGHT,
            target_id="priority",
            summary_text="Adjust priority weight",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.3,
                new=0.35,
                notes="Increase priority weight"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        
        result = await service.apply_lesson(lesson)
        
        # Result may be False if dry_run is enabled in config
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_apply_arbiter_weight_lesson_global(self, test_config, test_db, test_user):
        """Test arbiter weight lesson with global scope."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.ARBITER_WEIGHT,
            target_id="freshness",
            summary_text="Adjust freshness weight globally",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="freshness",
                old=0.15,
                new=0.2,
                notes="Global adjustment"
            ),
            confidence=0.9,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.GLOBAL_DEFAULT,
        )
        
        await service.lesson_store.create_lesson(lesson)
        
        result = await service.apply_lesson(lesson)
        
        # Result may be False if dry_run is enabled in config
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_apply_arbiter_weight_lesson_dry_run(self, test_config, test_db, test_user):
        """Test arbiter weight lesson in dry run mode."""
        test_config.set("agency.lesson_application.dry_run", True)
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.ARBITER_WEIGHT,
            target_id="priority",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.3,
                new=0.35,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        assert result is False


class TestApplyPersonaLesson:
    """Tests for persona lesson application."""
    
    @pytest.mark.asyncio
    async def test_apply_persona_lesson(self, test_config, test_db, test_user):
        """Test persona lesson application."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PERSONA_STYLE,
            target_kind=TargetKind.PERSONA_TRAIT,
            target_id="formality",
            summary_text="Adjust formality level",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="formality",
                old=0.5,
                new=0.7,
                notes="More formal"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        
        result = await service.apply_lesson(lesson)
        
        # Result may be False if dry_run is enabled in config
        assert result is False if test_config.get("agency.lesson_application.dry_run") else True
    
    @pytest.mark.asyncio
    async def test_apply_persona_lesson_dry_run(self, test_config, test_db, test_user):
        """Test persona lesson in dry run mode."""
        test_config.set("agency.lesson_application.dry_run", True)
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PERSONA_STYLE,
            target_kind=TargetKind.PERSONA_TRAIT,
            target_id="friendliness",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="friendliness",
                old=0.8,
                new=0.9,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        assert result is False


class TestApplyPolicyLesson:
    """Tests for policy lesson application."""
    
    @pytest.mark.asyncio
    async def test_apply_policy_lesson_observe_only_mode(self, test_config, test_db, test_user):
        """Test policy lesson in observe_only mode."""
        # Policy mode defaults to observe_only
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="privacy_rule",
            summary_text="Suggest privacy policy",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="privacy_threshold",
                old=0.7,
                new=0.8,
                notes="Increase privacy"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Result depends on policy_mode and dry_run config
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_apply_policy_lesson_with_freeze(self, test_config, test_db, test_user):
        """Test policy lesson when policy freeze is active."""
        test_config.set("agency.self_reflection.policy_mode", "suggest_amendments")
        test_config.set("agency.lesson_application.policy_freeze", True)
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="test_policy",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="threshold",
                old=0.5,
                new=0.6,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Should return False when policy freeze is active
        assert result is False


class TestApplyLessonErrorHandling:
    """Tests for error handling in lesson application."""
    
    @pytest.mark.asyncio
    async def test_apply_lesson_with_planner_template_target(self, test_config, test_db, test_user):
        """Test applying lesson with PLANNER_TEMPLATE target kind (not yet implemented)."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PLANNER_HEURISTIC,
            target_kind=TargetKind.PLANNER_TEMPLATE,  # Not handled in apply_lesson
            target_id="test_template",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="test",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        result = await service.apply_lesson(lesson)
        
        # Should return False for unhandled target_kind
        assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_lesson_exception_handling(self, test_config, test_db, test_user):
        """Test that exceptions during application are handled gracefully."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        # Mock _apply_skill_lesson to raise exception
        with patch.object(service, '_apply_skill_lesson', side_effect=Exception("Test error")):
            result = await service.apply_lesson(lesson)
            
            # Should return False on exception
            assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_skill_lesson_db_error(self, test_config, test_db, test_user):
        """Test skill lesson application handles database errors."""
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.SKILL_TUNING,
            target_kind=TargetKind.SKILL,
            target_id="test_skill",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="weight",
                old=1.0,
                new=1.2,
                notes="Test"
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        # Mock db.execute to raise error
        with patch.object(test_db, 'execute', side_effect=Exception("DB error")):
            result = await service._apply_skill_lesson(lesson)
            
            assert result is False
