"""
Additional coverage tests for agency/engine.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches in AgencyEngine.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch
import uuid

from aico.ai.agency.models import (
    Goal,
    GoalOrigin,
    GoalPriority,
    GoalStatus,
    Plan,
    PlanStatus,
    AgencyEvent,
)
from aico.ai.agency.engine import AgencyEngine
from aico.ai.agency.values_ethics import PolicyEffect


class TestEngineErrorHandling:
    """Tests for AgencyEngine error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_create_goal_blocked_by_ethics(self, test_config, test_db, test_user):
        """Test goal creation blocked by ethics policy."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock ethics evaluation to block
        with patch.object(engine.values_ethics, 'evaluate_goal') as mock_eval:
            mock_result = Mock()
            mock_result.decision = PolicyEffect.BLOCK
            mock_result.reason_codes = ["sensitive_topic"]
            mock_result.user_message = "This goal involves sensitive topics"
            mock_eval.return_value = mock_result
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="Goal blocked by ethics policy"):
                await engine.create_goal_with_optional_plan(
                    user_id=test_user,
                    title="Blocked Goal",
                    description="This should be blocked",
                    auto_plan=False,
                )
    
    @pytest.mark.asyncio
    async def test_create_goal_with_warning(self, test_config, test_db, test_user):
        """Test goal creation with ethics warning."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock ethics evaluation to allow with warning
        with patch.object(engine.values_ethics, 'evaluate_goal') as mock_eval:
            mock_result = Mock()
            mock_result.decision = PolicyEffect.ALLOW_WITH_WARNING
            mock_result.reason_codes = ["borderline_topic"]
            mock_result.user_message = "Proceed with caution"
            mock_eval.return_value = mock_result
            
            goal, _ = await engine.create_goal_with_optional_plan(
                user_id=test_user,
                title="Warning Goal",
                description="This has a warning",
                auto_plan=False,
            )
            
            assert goal is not None
            assert "ethics_warning" in goal.metadata
            assert goal.metadata["ethics_warning"] == "Proceed with caution"
    
    @pytest.mark.asyncio
    async def test_create_hobby_goal(self, test_config, test_db, test_user):
        """Test creating hobby goal with correct origin."""
        engine = AgencyEngine(test_config, test_db)
        
        goal, _ = await engine.create_hobby_goal_with_optional_plan(
            user_id=test_user,
            title="Learn Quantum Physics",
            description="Hobby learning goal",
            auto_plan=False,
        )
        
        assert goal is not None
        assert goal.origin == GoalOrigin.HOBBY
        assert goal.goal_type == "hobby"
    
    @pytest.mark.asyncio
    async def test_create_maintenance_goal(self, test_config, test_db, test_user):
        """Test creating maintenance goal with correct origin."""
        engine = AgencyEngine(test_config, test_db)
        
        goal, _ = await engine.create_maintenance_goal_with_optional_plan(
            user_id=test_user,
            title="Database Cleanup",
            description="System maintenance task",
            auto_plan=False,
        )
        
        assert goal is not None
        assert goal.origin == GoalOrigin.MAINTENANCE
        assert goal.goal_type == "maintenance"
    
    @pytest.mark.asyncio
    async def test_create_goal_with_world_context_no_world_model(self, test_config, test_db, test_user):
        """Test world context creation falls back when world model unavailable."""
        engine = AgencyEngine(test_config, test_db, world_model=None)
        
        goal, _ = await engine.create_goal_with_world_context(
            user_id=test_user,
            title="Test Goal",
            description="Should fall back to basic creation",
            auto_plan=False,
        )
        
        assert goal is not None
        assert "world_context" not in goal.metadata
    
    @pytest.mark.asyncio
    async def test_create_goal_with_world_context_error(self, test_config, test_db, test_user):
        """Test world context creation handles errors gracefully."""
        mock_world_model = Mock()
        mock_world_model.get_world_context = AsyncMock(side_effect=Exception("World model error"))
        
        engine = AgencyEngine(test_config, test_db, world_model=mock_world_model)
        
        # Should fall back to basic creation
        goal, _ = await engine.create_goal_with_world_context(
            user_id=test_user,
            title="Test Goal",
            description="Should handle error",
            auto_plan=False,
        )
        
        assert goal is not None
        assert "world_context" not in goal.metadata
    
    @pytest.mark.asyncio
    async def test_create_goal_with_full_context_no_services(self, test_config, test_db, test_user):
        """Test full context creation falls back when no Phase 2 services available."""
        engine = AgencyEngine(test_config, test_db, world_model=None, personality_service=None)
        
        goal, _ = await engine.create_goal_with_full_context(
            user_id=test_user,
            title="Test Goal",
            description="Should fall back",
            auto_plan=False,
        )
        
        assert goal is not None
        assert "world_context" not in goal.metadata
        assert "personality_context" not in goal.metadata
    
    @pytest.mark.asyncio
    async def test_create_goal_with_full_context_error(self, test_config, test_db, test_user):
        """Test full context creation handles errors gracefully."""
        mock_personality = Mock()
        mock_personality.get_personality_context = AsyncMock(side_effect=Exception("Personality error"))
        
        engine = AgencyEngine(test_config, test_db, personality_service=mock_personality)
        
        # Should fall back to basic creation
        goal, _ = await engine.create_goal_with_full_context(
            user_id=test_user,
            title="Test Goal",
            description="Should handle error",
            auto_plan=False,
        )
        
        assert goal is not None
    
    @pytest.mark.asyncio
    async def test_create_goal_from_curiosity_signal_blocked(self, test_config, test_db, test_user):
        """Test curiosity signal blocked by ethics."""
        from aico.ai.curiosity.models import IntrinsicSignal, CuriosityType
        
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Sensitive Topic",
            description="Test",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="high",
        )
        
        # Mock ethics to block
        with patch.object(engine.values_ethics, 'evaluate_curiosity_signal') as mock_eval:
            mock_result = Mock()
            mock_result.decision = PolicyEffect.BLOCK
            mock_result.reason_codes = ["sensitive"]
            mock_result.user_message = "Blocked"
            mock_eval.return_value = mock_result
            
            with pytest.raises(ValueError, match="Curiosity signal blocked by ethics policy"):
                await engine.create_goal_from_curiosity_signal(
                    user_id=test_user,
                    signal=signal,
                    auto_plan=False,
                )
    
    @pytest.mark.asyncio
    async def test_create_goal_from_curiosity_signal_needs_consent(self, test_config, test_db, test_user):
        """Test curiosity signal requiring consent."""
        from aico.ai.curiosity.models import IntrinsicSignal, CuriosityType
        
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Needs Consent",
            description="Test",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="high",
        )
        
        # Mock ethics to require consent
        with patch.object(engine.values_ethics, 'evaluate_curiosity_signal') as mock_eval:
            mock_result = Mock()
            mock_result.decision = PolicyEffect.NEEDS_CONSENT
            mock_result.consent_scope = "personal_data"
            mock_result.user_message = "Requires consent"
            mock_eval.return_value = mock_result
            
            with pytest.raises(ValueError, match="Curiosity signal requires consent"):
                await engine.create_goal_from_curiosity_signal(
                    user_id=test_user,
                    signal=signal,
                    auto_plan=False,
                )
    
    @pytest.mark.asyncio
    async def test_create_goal_from_curiosity_signal_with_warning(self, test_config, test_db, test_user):
        """Test curiosity signal allowed with warning."""
        from aico.ai.curiosity.models import IntrinsicSignal, CuriosityType
        
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="test-signal",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="Test Topic",
            description="Test",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="high",
        )
        
        # Mock ethics to allow with warning
        with patch.object(engine.values_ethics, 'evaluate_curiosity_signal') as mock_eval:
            mock_result = Mock()
            mock_result.decision = PolicyEffect.ALLOW_WITH_WARNING
            mock_result.reason_codes = ["borderline"]
            mock_result.user_message = "Warning message"
            mock_eval.return_value = mock_result
            
            goal, _ = await engine.create_goal_from_curiosity_signal(
                user_id=test_user,
                signal=signal,
                auto_plan=False,
            )
            
            assert goal is not None
            assert goal.origin == GoalOrigin.CURIOSITY
    
    @pytest.mark.asyncio
    async def test_create_goal_from_hobby_signal(self, test_config, test_db, test_user):
        """Test creating goal from hobby play signal."""
        from aico.ai.curiosity.models import IntrinsicSignal, CuriosityType
        
        engine = AgencyEngine(test_config, test_db)
        
        signal = IntrinsicSignal(
            signal_id="hobby-signal",
            user_id=test_user,
            signal_type=CuriosityType.HOBBY_PLAY,
            topic="Learn Chess",
            description="Hobby activity",
            novelty_score=0.8,
            uncertainty_score=0.7,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="normal",
            context={"template_id": "chess_template", "category": "games"},
        )
        
        goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        assert goal is not None
        assert goal.origin == GoalOrigin.HOBBY
        assert goal.goal_type == "hobby"
        assert "hobby_template_id" in goal.metadata
        assert goal.metadata["hobby_template_id"] == "chess_template"
    
    @pytest.mark.asyncio
    async def test_generate_and_store_plan_with_llm_refiner(self, test_config, test_db, test_user, sample_goal):
        """Test plan generation with LLM refinement."""
        # Create mock LLM refiner
        async def mock_refiner(goal, plan):
            plan.metadata["llm_refined"] = True
            return plan
        
        engine = AgencyEngine(test_config, test_db, llm_plan_refiner=mock_refiner)
        
        # Create goal first
        await engine.goal_store.create_goal(sample_goal)
        
        # Generate plan
        plan = await engine._generate_and_store_plan(sample_goal)
        
        assert plan is not None
        assert plan.metadata.get("llm_refined") is True
    
    @pytest.mark.asyncio
    async def test_generate_and_store_plan_llm_refiner_fails(self, test_config, test_db, test_user, sample_goal):
        """Test plan generation when LLM refiner fails."""
        # Create mock LLM refiner that fails
        async def failing_refiner(goal, plan):
            raise Exception("LLM refinement failed")
        
        engine = AgencyEngine(test_config, test_db, llm_plan_refiner=failing_refiner)
        
        # Create goal first
        await engine.goal_store.create_goal(sample_goal)
        
        # Should still generate plan using base planner
        plan = await engine._generate_and_store_plan(sample_goal)
        
        assert plan is not None
        assert plan.metadata.get("llm_refined", False) is False


class TestEngineGoalLifecycle:
    """Tests for goal lifecycle methods."""
    
    @pytest.mark.asyncio
    async def test_change_goal_status_nonexistent_goal(self, test_config, test_db):
        """Test changing status of nonexistent goal returns None."""
        engine = AgencyEngine(test_config, test_db)
        
        result = await engine._change_goal_status(
            goal_id="nonexistent",
            new_status=GoalStatus.ACTIVE,
            event_type="test",
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_activate_goal(self, test_config, test_db, test_user, sample_goal):
        """Test activating a goal."""
        engine = AgencyEngine(test_config, test_db)
        
        # Create goal
        await engine.goal_store.create_goal(sample_goal)
        
        # Activate it
        updated = await engine.activate_goal(sample_goal.goal_id)
        
        assert updated is not None
        assert updated.status == GoalStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_pause_goal(self, test_config, test_db, test_user, sample_goal):
        """Test pausing a goal."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        updated = await engine.pause_goal(sample_goal.goal_id)
        
        assert updated is not None
        assert updated.status == GoalStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_complete_goal(self, test_config, test_db, test_user, sample_goal):
        """Test completing a goal."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        updated = await engine.complete_goal(sample_goal.goal_id)
        
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_retire_goal(self, test_config, test_db, test_user, sample_goal):
        """Test retiring a goal."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        updated = await engine.retire_goal(sample_goal.goal_id)
        
        assert updated is not None
        assert updated.status == GoalStatus.RETIRED
    
    @pytest.mark.asyncio
    async def test_get_goal(self, test_config, test_db, test_user, sample_goal):
        """Test retrieving a goal."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        retrieved = await engine.get_goal(sample_goal.goal_id)
        
        assert retrieved is not None
        assert retrieved.goal_id == sample_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_list_goals_for_user(self, test_config, test_db, test_user, sample_goal):
        """Test listing goals for a user."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        goals = await engine.list_goals_for_user(test_user)
        
        assert len(goals) == 1
        assert goals[0].goal_id == sample_goal.goal_id
    
    @pytest.mark.asyncio
    async def test_list_goals_with_status_filter(self, test_config, test_db, test_user, sample_goal):
        """Test listing goals with status filter."""
        engine = AgencyEngine(test_config, test_db)
        
        await engine.goal_store.create_goal(sample_goal)
        
        # Filter for pending
        pending = await engine.list_goals_for_user(test_user, status=GoalStatus.PENDING)
        assert len(pending) == 1
        
        # Filter for active (should be empty)
        active = await engine.list_goals_for_user(test_user, status=GoalStatus.ACTIVE)
        assert len(active) == 0


class TestEngineIntentionSet:
    """Tests for intention set management."""
    
    @pytest.mark.asyncio
    async def test_get_intention_set(self, test_config, test_db, test_user):
        """Test getting intention set."""
        engine = AgencyEngine(test_config, test_db)
        
        intention_set = await engine.get_intention_set(test_user)
        
        assert intention_set is not None
        assert hasattr(intention_set, 'active_intentions')
        assert hasattr(intention_set, 'proposed_intentions')
    
    @pytest.mark.asyncio
    async def test_update_intention_set_for_user(self, test_config, test_db, test_user, sample_goal):
        """Test updating intention set."""
        engine = AgencyEngine(test_config, test_db)
        
        # Create a goal
        await engine.goal_store.create_goal(sample_goal)
        
        # Update intention set
        intention_set = await engine.update_intention_set_for_user(test_user)
        
        assert intention_set is not None


class TestEngineBaseProcessor:
    """Tests for BaseAIProcessor interface methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_turn(self, test_config, test_db, test_user):
        """Test analyze_conversation_turn returns contract-compliant response."""
        engine = AgencyEngine(test_config, test_db)
        
        result = await engine.analyze_conversation_turn(
            user_id=test_user,
            conversation_id="test-conv",
            message="Hello",
            context={},
        )
        
        assert "goal_suggestions" in result
        assert "plan_updates" in result
        assert "proactive_actions" in result
        assert "metadata" in result
        assert result["metadata"]["phase"] == "1"
    
    @pytest.mark.asyncio
    async def test_health_check(self, test_config, test_db):
        """Test health check."""
        engine = AgencyEngine(test_config, test_db)
        
        is_healthy = await engine.health_check()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, test_config, test_db):
        """Test health check when database fails."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock store to fail
        with patch.object(engine.goal_store, 'list_goals', side_effect=Exception("DB error")):
            is_healthy = await engine.health_check()
            
            assert is_healthy is False
    
    def test_get_supported_operations(self, test_config, test_db):
        """Test getting supported operations."""
        engine = AgencyEngine(test_config, test_db)
        
        operations = engine.get_supported_operations()
        
        assert "analyze_conversation_turn" in operations
        assert "create_goal" in operations
        assert "activate_goal" in operations
        assert "list_goals" in operations


class TestEngineSelfReflection:
    """Tests for self-reflection methods."""
    
    @pytest.mark.asyncio
    async def test_run_self_reflection(self, test_config, test_db, test_user):
        """Test running self-reflection."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock the self_reflection engine
        with patch.object(engine.self_reflection, 'run_reflection') as mock_run:
            from aico.ai.agency.models import RunType, RunStatus, ReflectionRun
            
            mock_run.return_value = ReflectionRun(
                run_id="test-run",
                user_id=test_user,
                run_type=RunType.SCHEDULED,
                trigger_reason="test",
                analysis_window_start=datetime.now(UTC),
                analysis_window_end=datetime.now(UTC),
                lessons_generated=0,
                lessons_applied=0,
                started_at=datetime.now(UTC),
                status=RunStatus.COMPLETED,
            )
            
            result = await engine.run_self_reflection(
                user_id=test_user,
                trigger_reason="test",
            )
            
            assert result is not None
            assert result.run_id == "test-run"
    
    @pytest.mark.asyncio
    async def test_get_active_lessons(self, test_config, test_db, test_user):
        """Test getting active lessons."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock the self_reflection engine
        with patch.object(engine.self_reflection, 'get_active_lessons') as mock_get:
            mock_get.return_value = []
            
            lessons = await engine.get_active_lessons(test_user)
            
            assert lessons == []
    
    @pytest.mark.asyncio
    async def test_get_skill_performance(self, test_config, test_db, test_user):
        """Test getting skill performance."""
        engine = AgencyEngine(test_config, test_db)
        
        # Mock the self_reflection engine
        with patch.object(engine.self_reflection, 'get_skill_performance') as mock_get:
            mock_get.return_value = 0.85
            
            perf = await engine.get_skill_performance(test_user, "test-skill")
            
            assert perf == 0.85
    
    @pytest.mark.asyncio
    async def test_get_goal_type_performance_context(self, test_config, test_db, test_user, sample_goal):
        """Test getting goal type performance context."""
        engine = AgencyEngine(test_config, test_db)
        
        # Create a goal to have data
        await engine.goal_store.create_goal(sample_goal)
        
        # Mock the self_reflection engine
        with patch.object(engine.self_reflection, 'get_goal_type_performance') as mock_get:
            mock_get.return_value = {"success_rate": 0.8, "completion_rate": 0.7}
            
            context = await engine.get_goal_type_performance_context(test_user)
            
            assert isinstance(context, dict)
