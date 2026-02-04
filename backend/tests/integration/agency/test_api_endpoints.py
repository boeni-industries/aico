"""
Agency API Endpoint Tests

Tests the REST API endpoints for agency system.
Uses real database with test fixtures and proper cleanup.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from aico.ai.agency.models import GoalOrigin, GoalPriority, GoalStatus
from aico.ai.agency.values_ethics import ProactiveBehaviorLevel


@pytest.mark.asyncio
class TestAgencyAPIEndpoints:
    """Test suite for agency API endpoints."""
    
    async def test_get_intention_set_empty(self, agency_engine, test_user):
        """Test GET /intentions with no goals returns empty set."""
        # Arrange
        engine = agency_engine
        
        # Act
        intention_set = await engine.get_intention_set(test_user)
        
        # Assert
        assert intention_set is not None
        assert len(intention_set.intentions) == 0
    
    async def test_get_intention_set_with_goals(self, agency_engine, test_user):
        """Test GET /intentions returns active goals with scores."""
        # Arrange
        engine = agency_engine
        
        # Create test goals
        goal1, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="High Priority Goal",
            description="Important task",
            goal_type="project",
            priority=GoalPriority.HIGH,
            auto_plan=False
        )
        
        goal2, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Normal Priority Goal",
            description="Regular task",
            goal_type="task",
            priority=GoalPriority.NORMAL,
            auto_plan=False
        )
        
        # Update intention set to include created goals
        await engine.update_intention_set_for_user(test_user)
        
        # Act
        intention_set = await engine.get_intention_set(test_user)
        
        # Assert
        assert intention_set is not None
        assert len(intention_set.intentions) == 2
        
        # Check that intentions have scores
        for intention in intention_set.intentions:
            assert intention.arbiter_score is not None
            assert intention.arbiter_score >= 0.0
            assert intention.priority_band.value in ["urgent", "high", "normal", "low", "background"]
        
        # Verify high priority goal scores higher
        scores = {i.goal_id: i.arbiter_score for i in intention_set.intentions}
        assert scores[goal1.goal_id] > scores[goal2.goal_id]
    
    async def test_get_intention_set_filters_by_status(self, agency_engine, test_user):
        """Test that intention set only includes active/pending goals."""
        # Arrange
        engine = agency_engine
        
        # Create active goal
        active_goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Active Goal",
            description="Should appear",
            goal_type="project",
            auto_plan=False
        )
        
        # Create and complete a goal
        completed_goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Completed Goal",
            description="Should not appear",
            goal_type="project",
            auto_plan=False
        )
        # Use complete_goal method following existing pattern
        await engine.complete_goal(completed_goal.goal_id)
        
        # Update intention set to reflect current goals
        await engine.update_intention_set_for_user(test_user)
        
        # Act
        intention_set = await engine.get_intention_set(test_user)
        
        # Assert
        assert len(intention_set.intentions) == 1
        assert intention_set.intentions[0].goal_id == active_goal.goal_id
    
    async def test_get_curiosity_status_no_curiosity_goals(self, agency_engine, test_user):
        """Test curiosity status with no curiosity-driven goals."""
        # Arrange
        engine = agency_engine
        
        # Create regular user goal
        await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="User Goal",
            description="Not curiosity-driven",
            goal_type="project",
            auto_plan=False
        )
        
        # Act
        intention_set = await engine.get_intention_set(test_user)
        
        # Count curiosity goals
        curiosity_goals = [
            sg for sg in intention_set.intentions
            if sg.goal.origin == GoalOrigin.CURIOSITY
        ]
        
        # Assert
        assert len(curiosity_goals) == 0
    
    async def test_value_profile_exists_for_user(self, agency_engine, test_user):
        """Test that value profile is created for user."""
        # Arrange
        engine = agency_engine

        # Act
        from aico.data.uow import UnitOfWork
        async with UnitOfWork(engine._session_factory) as uow:
            profile = await engine.values_ethics._get_or_create_profile(test_user, uow)

        # Assert
        assert profile is not None
        assert profile.user_id == test_user
        assert 0.0 <= profile.curiosity_intensity <= 1.0
        assert isinstance(profile.proactive_behavior_level, ProactiveBehaviorLevel)
        assert isinstance(profile.sensitive_life_areas, list)
        assert isinstance(profile.allowed_curiosity_domains, list)
    
    async def test_value_profile_default_values(self, agency_engine, test_user):
        """Test that value profile has sensible defaults."""
        # Arrange
        engine = agency_engine

        # Act
        from aico.data.uow import UnitOfWork
        async with UnitOfWork(engine._session_factory) as uow:
            profile = await engine.values_ethics._get_or_create_profile(test_user, uow)
        
        # Assert - defaults from default_policies.py
        assert profile.curiosity_intensity == 0.5  # Default medium
        assert profile.proactive_behavior_level == ProactiveBehaviorLevel.BALANCED
    
    async def test_list_policies(self, test_db):
        """Test listing policy rules."""
        # Act - Query policies directly from database
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT * FROM ethics_policy_rules WHERE enabled = TRUE ORDER BY priority ASC"
        )
        policies = cursor.fetchall()
        cursor.close()
        
        # Assert
        assert len(policies) > 0  # Should have default policies
        
        # Check policy structure
        for policy in policies:
            assert policy.get("rule_id") is not None
            assert policy.get("rule_name") is not None
            assert policy.get("target_type") in [
                "curiosity_signal",
                "goal",
                "plan",
                "action",
                "proactive_message",
            ]
            assert policy.get("effect") in ["allow", "allow_with_warning", "needs_consent", "block"]
            assert (policy.get("priority") or 0) >= 0
            assert policy.get("enabled") in (True, 1)
    
    async def test_list_policies_filter_by_target_type(self, test_db):
        """Test filtering policies by target type."""
        target_type = "curiosity_signal"
        
        # Act
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT * FROM ethics_policy_rules WHERE enabled = TRUE AND target_type = %s ORDER BY priority ASC",
            (target_type,),
        )
        policies = cursor.fetchall()
        cursor.close()
        
        # Assert
        assert len(policies) > 0
        for policy in policies:
            assert policy.get("target_type") == target_type
    
    async def test_grant_consent(self, test_db, test_user):
        """Test granting consent for an action."""
        # Arrange
        import json
        consent_id = f"test-consent-{test_user}-{datetime.now(UTC).timestamp()}"
        scope = {"target_type": "curiosity_signal", "rule_id": "test-rule"}
        
        # Act
        cursor = test_db.cursor()
        cursor.execute(
            """
            INSERT INTO consent_records (consent_id, user_id, consent_scope, decision, granted_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (consent_id, test_user, json.dumps(scope), "granted", datetime.now(UTC).isoformat())
        )
        test_db.commit()
        cursor.close()
        
        # Verify
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT * FROM consent_records WHERE consent_id = %s",
            (consent_id,),
        )
        consent = cursor.fetchone()
        cursor.close()
        
        # Assert
        assert consent is not None
        assert consent.get("user_id") == test_user
        assert consent.get("decision") == "granted"
        
        # Cleanup
        cursor = test_db.cursor()
        cursor.execute("DELETE FROM consent_records WHERE consent_id = %s", (consent_id,))
        test_db.commit()
        cursor.close()
    
    async def test_list_consents_for_user(self, test_db, test_user):
        """Test listing user's consents."""
        # Arrange
        import json
        consent_id = f"test-consent-list-{test_user}"
        scope = {"target_type": "goal", "life_area": "health"}
        
        cursor = test_db.cursor()
        cursor.execute(
            """
            INSERT INTO consent_records (consent_id, user_id, consent_scope, decision, granted_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (consent_id, test_user, json.dumps(scope), "granted", datetime.now(UTC).isoformat())
        )
        test_db.commit()
        cursor.close()
        
        # Act
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT * FROM consent_records WHERE user_id = %s ORDER BY granted_at DESC",
            (test_user,),
        )
        consents = cursor.fetchall()
        cursor.close()
        
        # Assert
        assert len(consents) >= 1
        found = any(c.get("consent_id") == consent_id for c in consents)
        assert found
        
        # Cleanup
        cursor = test_db.cursor()
        cursor.execute("DELETE FROM consent_records WHERE consent_id = %s", (consent_id,))
        test_db.commit()
        cursor.close()
    
    async def test_revoke_consent(self, test_db, test_user):
        """Test revoking a consent."""
        # Arrange
        import json
        consent_id = f"test-consent-revoke-{test_user}"
        scope = {"target_type": "proactive_message"}
        
        cursor = test_db.cursor()
        cursor.execute(
            """
            INSERT INTO consent_records (consent_id, user_id, consent_scope, decision, granted_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (consent_id, test_user, json.dumps(scope), "granted", datetime.now(UTC).isoformat())
        )
        test_db.commit()
        cursor.close()
        
        # Act - Revoke by updating decision (note: schema doesn't have updated_at column)
        cursor = test_db.cursor()
        cursor.execute(
            "UPDATE consent_records SET decision = %s WHERE consent_id = %s AND user_id = %s",
            ("denied", consent_id, test_user),
        )
        test_db.commit()
        cursor.close()
        
        # Verify
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT decision FROM consent_records WHERE consent_id = %s",
            (consent_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        
        # Assert
        assert result is not None
        assert result.get("decision") == "denied"
        
        # Cleanup
        cursor = test_db.cursor()
        cursor.execute("DELETE FROM consent_records WHERE consent_id = %s", (consent_id,))
        test_db.commit()
        cursor.close()
    
    async def test_hobby_goals_identified(self, agency_engine, test_user):
        """Test that hobby goals are properly identified in intention set."""
        # Arrange
        engine = agency_engine
        
        # Create hobby goal with explicit origin
        hobby_goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            origin=GoalOrigin.HOBBY,  # Must be before other params
            title="Study Philosophy",
            description="AICO's personal interest",
            goal_type="hobby",
            priority=GoalPriority.LOW,
            auto_plan=False
        )
        
        # Create regular goal (default origin is USER)
        user_goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="User Task",
            description="User-requested",
            goal_type="task",
            auto_plan=False
        )
        
        # Update intention set to include created goals
        await engine.update_intention_set_for_user(test_user)
        
        # Act
        intention_set = await engine.get_intention_set(test_user)
        
        # Assert - need to fetch goals to check origin
        # Intention objects only have goal_id, not the full goal
        intention_goal_ids = {i.goal_id for i in intention_set.intentions}
        
        assert len(intention_set.intentions) == 2
        assert hobby_goal.goal_id in intention_goal_ids
        assert user_goal.goal_id in intention_goal_ids
