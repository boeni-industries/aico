"""
Phase 4 Integration Tests: Values & Ethics Service

Tests policy evaluation, goal/plan/signal assessment, and ethical gates.
"""

import pytest
from datetime import datetime, UTC

from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import GoalStatus, GoalOrigin, GoalPriority
from aico.ai.agency.values_ethics import PolicyEffect


@pytest.mark.asyncio
class TestPhase4ValuesEthics:
    """Test suite for Values & Ethics Service."""
    
    async def test_values_ethics_service_initialization(self, test_config, test_db):
        """Test that ValuesEthicsService initializes correctly."""
        # Arrange & Act
        engine = AgencyEngine(test_config, test_db)
        
        # Assert
        assert engine.values_ethics is not None
        assert hasattr(engine.values_ethics, 'db')
        assert engine.values_ethics.db is not None
    
    async def test_evaluate_user_explicit_goal_allowed(self, test_config, test_db, test_user):
        """Test that user-explicit goals are generally allowed."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Learn Python",
            description="Study Python programming",
            goal_type="learning",
            auto_plan=False,
        )
        
        # Act
        result = engine.values_ethics.evaluate_goal(goal, test_user)
        
        # Assert
        assert result is not None
        assert result.decision in [PolicyEffect.ALLOW, PolicyEffect.ALLOW_WITH_WARNING]
    
    async def test_evaluate_goal_returns_evaluation_result(self, test_config, test_db, test_user):
        """Test that goal evaluation returns proper EvaluationResult."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal",
            description="Test description",
            goal_type="project",
            auto_plan=False,
        )
        
        # Act
        result = engine.values_ethics.evaluate_goal(goal, test_user)
        
        # Assert
        assert hasattr(result, 'decision')
        assert hasattr(result, 'reason_codes')
        assert isinstance(result.reason_codes, list)
    
    async def test_evaluate_plan_works(self, test_config, test_db, test_user):
        """Test that plan evaluation works."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal with Plan",
            description="Test description",
            goal_type="project",
            auto_plan=True,
        )
        
        # Act
        result = engine.values_ethics.evaluate_plan(plan, test_user)
        
        # Assert
        assert result is not None
        assert hasattr(result, 'decision')
    
    async def test_get_or_create_profile_creates_profile(self, test_config, test_db, test_user):
        """Test that user profile is created if it doesn't exist."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        profile = engine.values_ethics._get_or_create_profile(test_user)
        
        # Assert
        assert profile is not None
        assert profile.user_id == test_user
    
    async def test_get_or_create_profile_returns_existing(self, test_config, test_db, test_user):
        """Test that existing profile is returned."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create profile first time
        profile1 = engine.values_ethics._get_or_create_profile(test_user)
        
        # Act - Get profile second time
        profile2 = engine.values_ethics._get_or_create_profile(test_user)
        
        # Assert - Should be same profile
        assert profile1.profile_id == profile2.profile_id
    
    async def test_policies_loaded_for_goal_evaluation(self, test_config, test_db, test_user):
        """Test that policies are loaded when evaluating goals."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal",
            description="Test",
            goal_type="project",
            auto_plan=False,
        )
        
        # Act
        from aico.ai.agency.values_ethics import PolicyTargetType
        policies = engine.values_ethics._get_policies_for_target(PolicyTargetType.GOAL, test_user)
        
        # Assert
        assert policies is not None
        assert isinstance(policies, list)
