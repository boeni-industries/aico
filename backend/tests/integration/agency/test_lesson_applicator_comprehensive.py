"""
Comprehensive coverage tests for lesson_applicator.py - targeting uncovered code paths.

Focuses on:
- Policy amendment logic (_apply_policy_amendment)
- Rate limiting (_check_policy_amendment_rate_limit)
- Batch lesson application (apply_pending_lessons)
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, UTC
import uuid
import json

from aico.ai.agency.models import (
    Lesson,
    LessonType,
    TargetKind,
    LessonStatus,
    LessonScope,
    ProposedChange,
    ChangeType,
)
from aico.ai.agency.lesson_applicator import LessonApplicationService


class TestPolicyAmendmentLogic:
    """Tests for _apply_policy_amendment method."""
    
    @pytest.mark.asyncio
    async def test_policy_amendment_with_freeze_active(self, test_config, test_db, test_user):
        """Test policy amendment blocked when policy_freeze is active."""
        test_config.set("agency.lesson_application.policy_freeze", True)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="test_policy",
            summary_text="Test policy change",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should be blocked by freeze
        assert result is False
    
    @pytest.mark.asyncio
    async def test_policy_amendment_rate_limit_exceeded(self, test_config, test_db, test_user):
        """Test policy amendment blocked when rate limit exceeded."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 2)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create 2 already-applied policy lessons in last 24h
        for i in range(2):
            past_lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                user_id=test_user,
                lesson_type=LessonType.POLICY_SUGGESTION,
                target_kind=TargetKind.POLICY_RULE,
                target_id=f"past_policy_{i}",
                summary_text="Past policy",
                proposed_change=ProposedChange(
                    change_type=ChangeType.WEIGHT_TWEAK,
                    field="priority",
                    old=0.5,
                    new=0.6,
                ),
                confidence=0.8,
                status=LessonStatus.ACTIVE,
                scope=LessonScope.THIS_USER,
            )
            await service.lesson_store.create_lesson(past_lesson)
            # Mark as applied by values_ethics_service
            test_db.execute(
                "UPDATE agency_lessons SET applied_at = ?, applied_by = ? WHERE lesson_id = ?",
                (datetime.now(UTC).isoformat(), "values_ethics_service", past_lesson.lesson_id)
            )
            test_db.commit()
        
        # Try to apply new lesson - should be blocked by rate limit
        new_lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="new_policy",
            summary_text="New policy",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(new_lesson)
        result = await service.apply_lesson(new_lesson)
        
        # Should be blocked by rate limit
        assert result is False
    
    @pytest.mark.asyncio
    async def test_policy_amendment_weight_tweak(self, test_config, test_db, test_user):
        """Test policy amendment with WEIGHT_TWEAK change type."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 10)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create a policy rule first
        policy_id = str(uuid.uuid4())
        test_db.execute(
            """INSERT INTO agency_policy_rules 
               (rule_id, rule_name, target_type, conditions, effect, scope, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (policy_id, "Test Policy", "goal", "{}", "allow", "global", 50,
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id=policy_id,
            summary_text="Increase policy priority",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.8,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should succeed
        assert result is True
        
        # Verify policy was updated
        row = test_db.execute(
            "SELECT priority FROM agency_policy_rules WHERE rule_id = ?",
            (policy_id,)
        ).fetchone()
        assert row["priority"] == 0.8
    
    @pytest.mark.asyncio
    async def test_policy_amendment_threshold_tweak(self, test_config, test_db, test_user):
        """Test policy amendment with THRESHOLD_TWEAK change type."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 10)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create a policy rule with conditions
        policy_id = str(uuid.uuid4())
        initial_conditions = {"min_confidence": 0.7}
        test_db.execute(
            """INSERT INTO agency_policy_rules 
               (rule_id, rule_name, target_type, conditions, effect, scope, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (policy_id, "Test Policy", "goal", json.dumps(initial_conditions), "allow", "global", 50,
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id=policy_id,
            summary_text="Adjust confidence threshold",
            proposed_change=ProposedChange(
                change_type=ChangeType.THRESHOLD_TWEAK,
                field="min_confidence",
                old=0.7,
                new=0.8,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should succeed
        assert result is True
        
        # Verify conditions were updated
        row = test_db.execute(
            "SELECT conditions FROM agency_policy_rules WHERE rule_id = ?",
            (policy_id,)
        ).fetchone()
        conditions = json.loads(row["conditions"])
        assert conditions["min_confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_policy_amendment_nonexistent_policy(self, test_config, test_db, test_user):
        """Test policy amendment when policy rule doesn't exist."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        
        service = LessonApplicationService(test_config, test_db)
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="nonexistent_policy",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should fail - policy not found
        assert result is False
    
    @pytest.mark.asyncio
    async def test_policy_amendment_invalid_field(self, test_config, test_db, test_user):
        """Test policy amendment with invalid field name."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 10)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create a policy rule
        policy_id = str(uuid.uuid4())
        test_db.execute(
            """INSERT INTO agency_policy_rules 
               (rule_id, rule_name, target_type, conditions, effect, scope, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (policy_id, "Test Policy", "goal", "{}", "allow", "global", 50,
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id=policy_id,
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="nonexistent_field",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should fail - invalid field
        assert result is False
    
    @pytest.mark.asyncio
    async def test_policy_amendment_unsupported_change_type(self, test_config, test_db, test_user):
        """Test policy amendment with unsupported change type."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", False)
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 10)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create a policy rule
        policy_id = str(uuid.uuid4())
        test_db.execute(
            """INSERT INTO agency_policy_rules 
               (rule_id, rule_name, target_type, conditions, effect, scope, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (policy_id, "Test Policy", "goal", "{}", "allow", "global", 50,
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id=policy_id,
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.TEMPLATE_UPDATE,  # Unsupported for policies
                field="priority",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should fail - unsupported change type
        assert result is False
    
    @pytest.mark.asyncio
    async def test_policy_amendment_dry_run(self, test_config, test_db, test_user):
        """Test policy amendment in dry_run mode."""
        test_config.set("agency.lesson_application.policy_freeze", False)
        test_config.set("agency.self_reflection.policy_mode", "allow_amend")
        test_config.set("agency.lesson_application.dry_run", True)
        
        service = LessonApplicationService(test_config, test_db)
        
        # Create a policy rule
        policy_id = str(uuid.uuid4())
        test_db.execute(
            """INSERT INTO agency_policy_rules 
               (rule_id, rule_name, target_type, conditions, effect, scope, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (policy_id, "Test Policy", "goal", "{}", "allow", "global", 50,
             datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat())
        )
        test_db.commit()
        
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id=policy_id,
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.8,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should return False in dry_run
        assert result is False
        
        # Verify policy was NOT updated
        row = test_db.execute(
            "SELECT priority FROM agency_policy_rules WHERE rule_id = ?",
            (policy_id,)
        ).fetchone()
        assert row["priority"] == 50  # Unchanged from initial value


class TestBatchLessonApplication:
    """Tests for apply_pending_lessons method."""
    
    @pytest.mark.asyncio
    async def test_apply_pending_lessons_no_lessons(self, test_config, test_db, test_user):
        """Test batch application when no lessons exist."""
        service = LessonApplicationService(test_config, test_db)
        
        result = await service.apply_pending_lessons(test_user)
        
        assert result["total"] == 0
        assert result["applied"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_apply_pending_lessons_skips_already_applied(self, test_config, test_db, test_user):
        """Test batch application skips already-applied lessons."""
        test_config.set("agency.lesson_application.dry_run", False)
        service = LessonApplicationService(test_config, test_db)
        
        # Create lesson that's already applied
        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PERSONA_STYLE,
            target_kind=TargetKind.PERSONA_TRAIT,
            target_id="test_trait",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="formality",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        await service.lesson_store.create_lesson(lesson)
        
        # Mark as already applied
        test_db.execute(
            "UPDATE agency_lessons SET applied_at = ?, applied_by = ? WHERE lesson_id = ?",
            (datetime.now(UTC).isoformat(), "test", lesson.lesson_id)
        )
        test_db.commit()
        
        result = await service.apply_pending_lessons(test_user)
        
        assert result["total"] == 1
        assert result["applied"] == 0
        assert result["skipped"] == 1
        assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_apply_pending_lessons_mixed_results(self, test_config, test_db, test_user):
        """Test batch application with mixed success/failure."""
        test_config.set("agency.lesson_application.dry_run", False)
        service = LessonApplicationService(test_config, test_db)
        
        # Create successful lesson (persona - simple)
        lesson1 = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PERSONA_STYLE,
            target_kind=TargetKind.PERSONA_TRAIT,
            target_id="trait1",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="formality",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        await service.lesson_store.create_lesson(lesson1)
        
        # Create failing lesson (skill doesn't exist)
        lesson2 = Lesson(
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
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        await service.lesson_store.create_lesson(lesson2)
        
        # Create low-confidence lesson (will be skipped)
        lesson3 = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.PERSONA_STYLE,
            target_kind=TargetKind.PERSONA_TRAIT,
            target_id="trait3",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="formality",
                old=0.5,
                new=0.6,
            ),
            confidence=0.5,  # Below threshold
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        await service.lesson_store.create_lesson(lesson3)
        
        result = await service.apply_pending_lessons(test_user)
        
        assert result["total"] == 3
        assert result["applied"] >= 1  # At least lesson1
        assert result["failed"] >= 1  # At least lesson2 or lesson3


class TestRateLimitChecking:
    """Tests for _check_policy_amendment_rate_limit method."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self, test_config, test_db, test_user):
        """Test rate limit check when within limit."""
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 5)
        service = LessonApplicationService(test_config, test_db)
        
        # Create 2 policy amendments (below limit of 5)
        for i in range(2):
            lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                user_id=test_user,
                lesson_type=LessonType.POLICY_SUGGESTION,
                target_kind=TargetKind.POLICY_RULE,
                target_id=f"policy_{i}",
                summary_text="Test",
                proposed_change=ProposedChange(
                    change_type=ChangeType.WEIGHT_TWEAK,
                    field="priority",
                    old=0.5,
                    new=0.6,
                ),
                confidence=0.8,
                status=LessonStatus.ACTIVE,
                scope=LessonScope.THIS_USER,
            )
            await service.lesson_store.create_lesson(lesson)
            test_db.execute(
                "UPDATE agency_lessons SET applied_at = ?, applied_by = ? WHERE lesson_id = ?",
                (datetime.now(UTC).isoformat(), "values_ethics_service", lesson.lesson_id)
            )
            test_db.commit()
        
        # Check rate limit
        result = await service._check_policy_amendment_rate_limit(test_user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_at_limit(self, test_config, test_db, test_user):
        """Test rate limit check when at exact limit."""
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 3)
        service = LessonApplicationService(test_config, test_db)
        
        # Create exactly 3 policy amendments (at limit)
        for i in range(3):
            lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                user_id=test_user,
                lesson_type=LessonType.POLICY_SUGGESTION,
                target_kind=TargetKind.POLICY_RULE,
                target_id=f"policy_{i}",
                summary_text="Test",
                proposed_change=ProposedChange(
                    change_type=ChangeType.WEIGHT_TWEAK,
                    field="priority",
                    old=0.5,
                    new=0.6,
                ),
                confidence=0.8,
                status=LessonStatus.ACTIVE,
                scope=LessonScope.THIS_USER,
            )
            await service.lesson_store.create_lesson(lesson)
            test_db.execute(
                "UPDATE agency_lessons SET applied_at = ?, applied_by = ? WHERE lesson_id = ?",
                (datetime.now(UTC).isoformat(), "values_ethics_service", lesson.lesson_id)
            )
            test_db.commit()
        
        # Check rate limit
        result = await service._check_policy_amendment_rate_limit(test_user)
        
        assert result is False  # At limit, should block
    
    @pytest.mark.asyncio
    async def test_rate_limit_old_amendments_ignored(self, test_config, test_db, test_user):
        """Test that old amendments (>24h) don't count toward limit."""
        test_config.set("agency.lesson_application.policy_amendment_limit_per_day", 2)
        service = LessonApplicationService(test_config, test_db)
        
        # Create old amendment (2 days ago)
        old_lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            user_id=test_user,
            lesson_type=LessonType.POLICY_SUGGESTION,
            target_kind=TargetKind.POLICY_RULE,
            target_id="old_policy",
            summary_text="Test",
            proposed_change=ProposedChange(
                change_type=ChangeType.WEIGHT_TWEAK,
                field="priority",
                old=0.5,
                new=0.6,
            ),
            confidence=0.8,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        await service.lesson_store.create_lesson(old_lesson)
        old_time = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        test_db.execute(
            "UPDATE agency_lessons SET applied_at = ?, applied_by = ? WHERE lesson_id = ?",
            (old_time, "values_ethics_service", old_lesson.lesson_id)
        )
        test_db.commit()
        
        # Check rate limit - old amendment shouldn't count
        result = await service._check_policy_amendment_rate_limit(test_user)
        
        assert result is True


class TestPolicyLessonModes:
    """Tests for different policy_mode configurations."""
    
    @pytest.mark.asyncio
    async def test_policy_lesson_unknown_mode(self, test_config, test_db, test_user):
        """Test policy lesson with unknown policy_mode."""
        test_config.set("agency.self_reflection.policy_mode", "unknown_mode")
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
                field="priority",
                old=0.5,
                new=0.7,
            ),
            confidence=0.85,
            status=LessonStatus.ACTIVE,
            scope=LessonScope.THIS_USER,
        )
        
        await service.lesson_store.create_lesson(lesson)
        result = await service.apply_lesson(lesson)
        
        # Should fail with unknown mode
        assert result is False
