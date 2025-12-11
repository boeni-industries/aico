"""
Integration tests for Phase 3 Curiosity Engine integration with AgencyEngine.

Tests goal creation from curiosity signals and end-to-end curiosity flow.
"""

import pytest
from datetime import datetime

from aico.ai.agency import AgencyEngine, GoalOrigin, GoalPriority
from aico.ai.curiosity import IntrinsicSignal, CuriosityType


@pytest.mark.asyncio
class TestPhase3CuriosityIntegration:
    """Test suite for Phase 3 curiosity integration."""
    
    async def test_create_goal_from_hobby_signal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating a hobby goal from a hobby_play signal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="hobby-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Deep Dive Learning",
            description="Explore a topic in depth through questions and research",
            novelty_score=0.7,
            uncertainty_score=0.5,
            user_relevance_score=0.8,
            feasibility_score=0.9,
            total_score=0.75,
            priority="high",
            context={"template_id": "deep_dive_learning", "category": "learning"},
        )
        
        # Act
        goal, plan = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=True,
        )
        
        # Assert
        assert goal is not None
        assert goal.origin == GoalOrigin.HOBBY
        assert goal.title == "Deep Dive Learning"
        assert goal.description == "Explore a topic in depth through questions and research"
        assert goal.priority == GoalPriority.HIGH
        
        # Check metadata enrichment
        assert "curiosity_signal_id" in goal.metadata
        assert goal.metadata["curiosity_signal_id"] == "hobby-signal-1"
        assert goal.metadata["curiosity_type"] == "hobby_play"
        assert goal.metadata["curiosity_score"] == 0.75
        assert goal.metadata["hobby_template_id"] == "deep_dive_learning"
        assert goal.metadata["hobby_category"] == "learning"
        
        # Check plan was created
        assert plan is not None
        
        # Check signal status updated
        assert signal.status == "converted"
    
    async def test_create_goal_from_knowledge_gap_signal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating a curiosity goal from a knowledge_gap signal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="gap-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="User's daily routine",
            description="Missing information about typical day structure",
            novelty_score=0.6,
            uncertainty_score=0.9,
            user_relevance_score=0.8,
            feasibility_score=0.7,
            total_score=0.72,
            priority="high",
        )
        
        # Act
        goal, plan = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=True,
        )
        
        # Assert
        assert goal is not None
        assert goal.origin == GoalOrigin.CURIOSITY
        assert goal.title == "User's daily routine"
        assert goal.priority == GoalPriority.HIGH
        
        # Check metadata
        assert goal.metadata["curiosity_type"] == "knowledge_gap"
        assert goal.metadata["novelty_score"] == 0.6
        assert goal.metadata["user_relevance_score"] == 0.8
    
    async def test_create_goal_from_novelty_signal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating a curiosity goal from a novelty signal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="novelty-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.NOVELTY,
            topic="Explore new conversation patterns",
            description="Under-explored but potentially meaningful area",
            novelty_score=0.9,
            uncertainty_score=0.6,
            user_relevance_score=0.6,
            feasibility_score=0.7,
            total_score=0.68,
            priority="normal",
        )
        
        # Act
        goal, plan = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,  # No plan
        )
        
        # Assert
        assert goal is not None
        assert goal.origin == GoalOrigin.CURIOSITY
        assert goal.priority == GoalPriority.NORMAL
        assert plan is None  # No plan requested
    
    async def test_create_goal_from_self_performance_signal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating a curiosity goal from a self_performance signal."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="performance-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.SELF_PERFORMANCE,
            topic="Improve conversation quality",
            description="Weak performance in technical discussions",
            novelty_score=0.5,
            uncertainty_score=0.4,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.65,
            priority="normal",
        )
        
        # Act
        goal, plan = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=True,
        )
        
        # Assert
        assert goal is not None
        assert goal.origin == GoalOrigin.CURIOSITY
        assert goal.metadata["curiosity_type"] == "self_performance"
    
    async def test_priority_mapping_from_signal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test that signal priority correctly maps to GoalPriority."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Test all priority levels
        priorities = [
            ("low", GoalPriority.LOW),
            ("normal", GoalPriority.NORMAL),
            ("high", GoalPriority.HIGH),
        ]
        
        for signal_priority, expected_goal_priority in priorities:
            signal = IntrinsicSignal(
                signal_id=f"priority-signal-{signal_priority}",
                user_id=test_user,
                signal_type=CuriosityType.HOBBY_PLAY,
                topic=f"Test {signal_priority} priority",
                description="Test",
                total_score=0.6,
                priority=signal_priority,
            )
            
            # Act
            goal, _ = await engine.create_goal_from_curiosity_signal(
                user_id=test_user,
                signal=signal,
                auto_plan=False,
            )
            
            # Assert
            assert goal.priority == expected_goal_priority
    
    async def test_goal_metadata_preserves_all_signal_info(self, test_config, test_db, test_user, permissive_value_profile):
        """Test that all relevant signal information is preserved in goal metadata."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="metadata-signal",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Test Topic",
            description="Test Description",
            novelty_score=0.7,
            uncertainty_score=0.6,
            user_relevance_score=0.8,
            feasibility_score=0.75,
            total_score=0.72,
            priority="high",
            source_component="gap_detector",
            topic_tags=["learning", "user_understanding"],
        )
        
        # Act
        goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert - All signal info should be in metadata
        assert goal.metadata["curiosity_signal_id"] == "metadata-signal"
        assert goal.metadata["curiosity_type"] == "knowledge_gap"
        assert goal.metadata["curiosity_score"] == 0.72
        assert goal.metadata["novelty_score"] == 0.7
        assert goal.metadata["user_relevance_score"] == 0.8
        assert goal.metadata["source_component"] == "gap_detector"
        assert goal.metadata["topic_tags"] == ["learning", "user_understanding"]
    
    async def test_multiple_goals_from_signals(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating multiple goals from different signals."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signals = [
            IntrinsicSignal(
                signal_id=f"signal-{i}",
                user_id=test_user,
                signal_type=CuriosityType.HOBBY_PLAY,
                topic=f"Hobby {i}",
                description=f"Description {i}",
                total_score=0.6 + (i * 0.05),
                priority="normal",
            )
            for i in range(3)
        ]
        
        # Act
        goals = []
        for signal in signals:
            goal, _ = await engine.create_goal_from_curiosity_signal(
                user_id=test_user,
                signal=signal,
                auto_plan=False,
            )
            goals.append(goal)
        
        # Assert
        assert len(goals) == 3
        assert all(g.origin == GoalOrigin.HOBBY for g in goals)
        assert all(g.user_id == test_user for g in goals)
        
        # Each goal should have unique signal_id in metadata
        signal_ids = [g.metadata["curiosity_signal_id"] for g in goals]
        assert len(set(signal_ids)) == 3  # All unique
    
    async def test_goal_creation_with_existing_hobby_goal(self, test_config, test_db, test_user, permissive_value_profile):
        """Test creating curiosity goals alongside existing hobby goals."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Create a regular hobby goal first
        hobby_goal, _ = await engine.create_hobby_goal_with_optional_plan(
            user_id=test_user,
            title="Manual Hobby",
            description="User-created hobby",
            auto_plan=False,
        )
        
        # Create a curiosity-driven hobby goal
        signal = IntrinsicSignal(
            signal_id="coexist-signal",
            user_id=test_user,
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Curiosity Hobby",
            description="Curiosity-driven hobby",
            total_score=0.7,
            priority="normal",
        )
        
        curiosity_goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert - Both should exist and be distinguishable
        assert hobby_goal.origin == GoalOrigin.HOBBY
        assert curiosity_goal.origin == GoalOrigin.HOBBY
        
        # Curiosity goal should have signal metadata
        assert "curiosity_signal_id" in curiosity_goal.metadata
        assert "curiosity_signal_id" not in hobby_goal.metadata
    
    async def test_signal_status_updated_after_conversion(self, test_config, test_db, test_user, permissive_value_profile):
        """Test that signal status is updated to 'converted' after goal creation."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="status-test-signal",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Status Test",
            description="Test status update",
            total_score=0.6,
            priority="normal",
            status="pending",
        )
        
        # Assert initial status
        assert signal.status == "pending"
        
        # Act
        await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert status updated
        assert signal.status == "converted"
