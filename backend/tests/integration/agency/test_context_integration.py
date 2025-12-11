"""
Phase 2 Integration Tests

Tests for world model and personality integration in agency system.
"""

import pytest
from datetime import datetime

from aico.ai.agency.engine import AgencyEngine
from aico.ai.agency.models import GoalOrigin, GoalPriority, GoalStatus
from aico.ai.world_model import WorldModelService
from aico.ai.personality import PersonalityService


@pytest.mark.asyncio
class TestPhase2ContextIntegration:
    """Test Phase 2 world model and personality integration."""
    
    async def test_create_goal_without_phase2_services(self, test_config, test_db, test_user):
        """Test that goal creation works without Phase 2 services (backward compatibility)."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act - Create goal without Phase 2 services
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test goal without Phase 2",
            description="Should work in Phase 1 mode",
            auto_plan=True,
        )
        
        # Assert
        assert goal is not None
        assert goal.title == "Test goal without Phase 2"
        assert goal.status == GoalStatus.PENDING
        assert plan is not None
        assert len(plan.steps) > 0
    
    async def test_create_goal_with_world_context_no_service(self, test_config, test_db, test_user):
        """Test create_goal_with_world_context falls back gracefully without service."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act - Call Phase 2 method without world model service
        goal, plan = await engine.create_goal_with_world_context(
            user_id=test_user,
            title="Test goal with world context fallback",
            description="Should fall back to basic creation",
            auto_plan=True,
        )
        
        # Assert - Should still create goal successfully
        assert goal is not None
        assert goal.title == "Test goal with world context fallback"
        assert goal.status == GoalStatus.PENDING
        # Metadata should not have world_context since service unavailable
        assert 'world_context' not in (goal.metadata or {})
    
    async def test_create_goal_with_full_context_no_services(self, test_config, test_db, test_user):
        """Test create_goal_with_full_context falls back gracefully without services."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act - Call Phase 2 full context method without services
        goal, plan = await engine.create_goal_with_full_context(
            user_id=test_user,
            title="Test goal with full context fallback",
            description="Should fall back to basic creation",
            priority=GoalPriority.NORMAL,
            auto_plan=True,
        )
        
        # Assert - Should still create goal successfully
        assert goal is not None
        assert goal.title == "Test goal with full context fallback"
        assert goal.status == GoalStatus.PENDING
        assert goal.priority == GoalPriority.NORMAL
        # Metadata should not have Phase 2 context since services unavailable
        assert 'world_context' not in (goal.metadata or {})
        assert 'personality_context' not in (goal.metadata or {})
    
    async def test_personality_service_basic_functionality(self, test_config, test_db, test_user):
        """Test PersonalityService basic operations."""
        # Arrange
        personality = PersonalityService(db_connection=test_db)
        
        # Act - Get personality context
        context = await personality.get_personality_context(test_user)
        
        # Assert - Should return default AICO personality
        assert context is not None
        assert context.user_id == test_user
        assert context.traits is not None
        assert 0.0 <= context.traits.extraversion <= 1.0
        assert 0.0 <= context.traits.agreeableness <= 1.0
        assert 0.0 <= context.traits.conscientiousness <= 1.0
        assert context.relationship is not None
        assert context.relationship.user_id == test_user
    
    async def test_personality_priority_adjustment(self, test_config, test_db, test_user):
        """Test personality-based priority adjustment."""
        # Arrange
        personality = PersonalityService(db_connection=test_db)
        context = await personality.get_personality_context(test_user)
        
        # Act - Adjust priority based on personality
        adjusted = personality.adjust_priority_for_personality(
            base_priority="normal",
            personality=context,
        )
        
        # Assert - Should return valid priority
        assert adjusted in ["low", "normal", "high"]
    
    async def test_personality_proactivity_calculation(self, test_config, test_db, test_user):
        """Test proactivity level calculation."""
        # Arrange
        personality = PersonalityService(db_connection=test_db)
        context = await personality.get_personality_context(test_user)
        
        # Act - Calculate proactivity
        proactivity = personality.calculate_proactivity_level(context)
        
        # Assert - Should return value between 0 and 1
        assert 0.0 <= proactivity <= 1.0
    
    async def test_agency_engine_with_personality_service(self, test_config, test_db, test_user):
        """Test AgencyEngine with PersonalityService integration."""
        # Arrange
        personality = PersonalityService(db_connection=test_db)
        engine = AgencyEngine(
            test_config,
            test_db,
            personality_service=personality,
        )
        
        # Act - Create goal with full context (only personality available)
        goal, plan = await engine.create_goal_with_full_context(
            user_id=test_user,
            title="Test goal with personality",
            description="Should include personality context",
            priority=GoalPriority.NORMAL,
            auto_plan=True,
        )
        
        # Assert
        assert goal is not None
        assert goal.title == "Test goal with personality"
        # Should have personality context in metadata
        assert 'personality_context' in goal.metadata
        assert 'proactivity_level' in goal.metadata['personality_context']
        assert 'relationship_closeness' in goal.metadata['personality_context']
        # Priority might be adjusted
        assert goal.priority in [GoalPriority.LOW, GoalPriority.NORMAL, GoalPriority.HIGH]
    
    async def test_goal_metadata_enrichment(self, test_config, test_db, test_user):
        """Test that Phase 2 enriches goal metadata correctly."""
        # Arrange
        personality = PersonalityService(db_connection=test_db)
        engine = AgencyEngine(
            test_config,
            test_db,
            personality_service=personality,
        )
        
        # Act - Create goal with custom metadata
        custom_metadata = {"custom_field": "custom_value"}
        goal, _ = await engine.create_goal_with_full_context(
            user_id=test_user,
            title="Test metadata enrichment",
            priority=GoalPriority.HIGH,
            metadata=custom_metadata,
            auto_plan=False,
        )
        
        # Assert - Custom metadata preserved, Phase 2 context added
        assert goal.metadata is not None
        assert goal.metadata["custom_field"] == "custom_value"
        assert 'personality_context' in goal.metadata
        # Original priority should be tracked if adjusted
        if goal.priority != GoalPriority.HIGH:
            assert goal.metadata['personality_context']['original_priority'] == 'high'
    
    async def test_create_goal_with_world_context_fallback(self, test_config, test_db, test_user):
        """Test world context creation falls back when no world model."""
        # Arrange
        engine = AgencyEngine(test_config, test_db, world_model=None)
        
        # Act
        goal, _ = await engine.create_goal_with_world_context(
            user_id=test_user,
            title="Test fallback",
            auto_plan=False,
        )
        
        # Assert - Should create without world context
        assert goal is not None
        assert 'world_context' not in goal.metadata
    
    async def test_hobby_goal_creation(self, test_config, test_db, test_user):
        """Test hobby goal creation helper."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        goal, plan = await engine.create_hobby_goal_with_optional_plan(
            user_id=test_user,
            title="Learn guitar",
            description="Self-improvement",
            auto_plan=True,
        )
        
        # Assert
        assert goal.origin == GoalOrigin.HOBBY
        assert goal.title == "Learn guitar"
        assert plan is not None
    
    async def test_maintenance_goal_creation(self, test_config, test_db, test_user):
        """Test maintenance goal creation helper."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Act
        goal, plan = await engine.create_maintenance_goal_with_optional_plan(
            user_id=test_user,
            title="Clean database",
            description="System maintenance",
            auto_plan=False,
        )
        
        # Assert
        assert goal.origin == GoalOrigin.MAINTENANCE
        assert goal.title == "Clean database"
        assert plan is None
