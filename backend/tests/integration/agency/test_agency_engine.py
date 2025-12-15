"""
Phase 4 Integration Tests: Basic Values & Ethics and Goal Arbiter

Tests the basic functionality of Phase 4 components with minimal complexity.
"""

import pytest
from datetime import datetime, UTC

from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import GoalStatus, GoalOrigin, GoalPriority


@pytest.mark.asyncio
class TestPhase4Basic:
    """Basic test suite for Phase 4 components."""
    
    async def test_agency_engine_initializes_with_phase4_components(self, test_config, test_db):
        """Test that AgencyEngine initializes with Values & Ethics and Goal Arbiter."""
        # Act
        engine = AgencyEngine(test_config, test_db)
        
        # Assert
        assert engine is not None
        assert hasattr(engine, 'values_ethics')
        assert hasattr(engine, 'arbiter')
        assert engine.values_ethics is not None
        assert engine.arbiter is not None
    
    async def test_goal_arbiter_has_scoring_weights(self, test_config, test_db):
        """Test that Goal Arbiter loads scoring weights from config."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Assert
        assert hasattr(engine.arbiter, 'weights')
        assert engine.arbiter.weights is not None
        assert 'priority' in engine.arbiter.weights
        assert 'origin' in engine.arbiter.weights
        assert 'freshness' in engine.arbiter.weights
        
        # Check weights sum to approximately 1.0
        total = sum(engine.arbiter.weights.values())
        assert abs(total - 1.0) < 0.01
    
    async def test_values_ethics_service_exists(self, test_config, test_db):
        """Test that Values & Ethics service is accessible."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Assert
        assert engine.values_ethics is not None
        assert hasattr(engine.values_ethics, 'evaluate_goal')
        assert hasattr(engine.values_ethics, 'evaluate_plan')
    
    async def test_create_goal_with_phase4_engine(self, test_config, test_db, test_user):
        """Test creating a goal with Phase 4 engine (should work same as Phase 1)."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal",
            description="Test Phase 4",
            goal_type="project",
            auto_plan=False,
        )
        
        # Assert
        assert goal is not None
        assert goal.title == "Test Goal"
        assert goal.status == GoalStatus.PENDING
    
    async def test_intention_set_method_exists(self, test_config, test_db, test_user):
        """Test that intention set methods are available."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Assert
        assert hasattr(engine, 'get_intention_set')
        assert hasattr(engine, 'update_intention_set_for_user')
        
        # Test that we can call get_intention_set
        intention_set = await engine.get_intention_set(test_user)
        assert intention_set is not None
