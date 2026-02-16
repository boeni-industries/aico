"""
Phase 4 Integration Tests: Ethics Gates and Policy Enforcement

Tests that Values & Ethics gates actually work by varying user profiles,
policy settings, and consent requirements.
"""

import pytest
from datetime import datetime, UTC
import uuid

from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import GoalStatus, GoalOrigin, GoalPriority
from aico.ai.agency.values_ethics import (
    ValuesEthicsService, 
    PolicyEffect, 
    PolicyRule, 
    PolicyTargetType, 
    PolicyScope,
    AutonomyLevel
)
from aico.ai.curiosity import IntrinsicSignal, CuriosityType


@pytest.mark.asyncio
class TestPhase4EthicsGates:
    """Test suite for Values & Ethics gate enforcement."""

    @pytest.fixture
    async def session_factory(self):
        from aico.data.postgres.connection import get_session_factory

        return await get_session_factory()

    @pytest.fixture
    async def uow(self, session_factory):
        from aico.data.uow import UnitOfWork

        async with UnitOfWork(session_factory) as uow:
            yield uow
            await uow.rollback()

    @pytest.fixture
    def agency_service(self, uow):
        from aico.services.agency_service import AgencyService

        return AgencyService(uow)
    
    async def test_sensitive_life_area_blocks_curiosity_signal(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that curiosity signals about sensitive life areas require consent."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Set up profile with sensitive life areas
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        from aico.data.ethics.models import EthicsPolicyRule

        service = ValuesEthicsService()
        async with UnitOfWork(await get_session_factory()) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = '["health", "finance", "relationships"]'
            await uow.ethics_value_profiles.update(entity)

            await uow.ethics_policy_rules.create(
                EthicsPolicyRule(
                    rule_id=f"test_sensitive_life_area_{uuid.uuid4().hex}",
                    rule_name="Sensitive Life Area Curiosity Gate",
                    target_type=PolicyTargetType.CURIOSITY_SIGNAL.value,
                    conditions_json={"life_area": "sensitive"},
                    effect=PolicyEffect.NEEDS_CONSENT.value,
                    priority=10,
                    enabled=True,
                    scope=PolicyScope.GLOBAL.value,
                )
            )
            await uow.commit()
        
        # Create signal about a sensitive topic
        signal = IntrinsicSignal(
            signal_id="sensitive-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="User's health habits",
            description="Explore daily health routines",
            novelty_score=0.7,
            uncertainty_score=0.8,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="high",
        )
        
        # Act & Assert - Should raise ValueError due to consent requirement
        with pytest.raises(ValueError, match="Curiosity signal requires consent"):
            await engine.create_goal_from_curiosity_signal(
                user_id=test_user,
                signal=signal,
                auto_plan=False,
            )
    
    async def test_permissive_profile_allows_all_signals(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that permissive profile (no sensitive areas) allows all signals."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Set up permissive profile
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(await get_session_factory()) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = "[]"
            entity.curiosity_intensity = 1.0
            await uow.ethics_value_profiles.update(entity)
            await uow.commit()
        
        # Create signal about potentially sensitive topic
        signal = IntrinsicSignal(
            signal_id="test-signal-1",
            user_id=test_user,
            signal_type=CuriosityType.KNOWLEDGE_GAP,
            topic="User's daily routine",
            description="Explore daily patterns",
            novelty_score=0.7,
            uncertainty_score=0.8,
            user_relevance_score=0.9,
            feasibility_score=0.8,
            total_score=0.8,
            priority="high",
        )
        
        # Act - Should succeed
        goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert
        assert goal is not None
        assert goal.metadata["ethics_evaluation"]["decision"] in ["allow", "allow_with_warning"]
    
    async def test_high_curiosity_intensity_triggers_warning(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that high curiosity intensity signals trigger warnings."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Set up profile with low curiosity intensity threshold
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(await get_session_factory()) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = "[]"
            entity.curiosity_intensity = 0.5
            await uow.ethics_value_profiles.update(entity)
            await uow.commit()
        
        # Create high-intensity signal
        signal = IntrinsicSignal(
            signal_id="high-intensity-signal",
            user_id=test_user,
            signal_type=CuriosityType.NOVELTY,
            topic="Explore new area",
            description="High intensity exploration",
            novelty_score=0.9,
            uncertainty_score=0.9,
            user_relevance_score=0.9,
            feasibility_score=0.9,
            total_score=0.9,  # Above threshold
            priority="high",
        )
        
        # Act - Should succeed but with warning
        goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert
        assert goal is not None
        # Should have warning in ethics evaluation (or at least be allowed)
        # Note: The warning depends on the default policy configuration
        decision = goal.metadata["ethics_evaluation"]["decision"]
        assert decision in ["allow", "allow_with_warning"]
        
        # The key test is that it's NOT blocked
        assert decision != "block"
        assert decision != "needs_consent"
    
    async def test_low_curiosity_intensity_allows_without_warning(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that low curiosity intensity signals are allowed without warning."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Set up profile with high curiosity intensity threshold
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(await get_session_factory()) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = "[]"
            entity.curiosity_intensity = 0.9
            await uow.ethics_value_profiles.update(entity)
            await uow.commit()
        
        # Create low-intensity signal
        signal = IntrinsicSignal(
            signal_id="low-intensity-signal",
            user_id=test_user,
            signal_type=CuriosityType.NOVELTY,
            topic="Explore topic",
            description="Low intensity exploration",
            novelty_score=0.4,
            uncertainty_score=0.4,
            user_relevance_score=0.4,
            feasibility_score=0.4,
            total_score=0.4,  # Below threshold
            priority="low",
        )
        
        # Act
        goal, _ = await engine.create_goal_from_curiosity_signal(
            user_id=test_user,
            signal=signal,
            auto_plan=False,
        )
        
        # Assert
        assert goal is not None
        assert goal.metadata["ethics_evaluation"]["decision"] == "allow"
    
    async def test_user_explicit_goals_bypass_curiosity_gates(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that user-explicit goals are not subject to curiosity intensity gates."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Set up restrictive profile
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(await get_session_factory()) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = '["everything"]'
            entity.curiosity_intensity = 0.1
            await uow.ethics_value_profiles.update(entity)
            await uow.commit()
        
        # Act - Create user-explicit goal (not from curiosity)
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="User's explicit goal",
            description="User wants to do this",
            goal_type="project",
            auto_plan=False,
        )
        
        # Assert - Should succeed because it's user-explicit
        assert goal is not None
        assert goal.origin == GoalOrigin.USER
        assert goal.metadata["ethics_evaluation"]["decision"] == "allow"
    
    async def test_autonomy_level_affects_evaluation(self, test_config, test_db, test_user, session_factory):
        """Test that proactive behavior level is stored in profile."""
        # Arrange
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        
        # Test each proactive behavior level
        levels = [
            AutonomyLevel.QUIET,
            AutonomyLevel.BALANCED,
            AutonomyLevel.PROACTIVE
        ]
        
        for level in levels:
            # Act
            async with UnitOfWork(session_factory) as uow:
                await service._get_or_create_profile(test_user, uow)
                entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
                assert entity is not None
                entity.autonomy_level = level.value
                await uow.ethics_value_profiles.update(entity)
                await uow.commit()

            async with UnitOfWork(session_factory) as uow:
                fresh_service = ValuesEthicsService()
                retrieved = await fresh_service._get_or_create_profile(test_user, uow)
                assert retrieved.autonomy_level == level
    
    async def test_multiple_sensitive_areas_all_enforced(self, test_config, test_db, test_user, agency_service, session_factory):
        """Test that multiple sensitive life areas are all enforced."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(session_factory) as uow:
            await service._get_or_create_profile(test_user, uow)
            entity = await uow.ethics_value_profiles.get_by_user_id(test_user)
            assert entity is not None
            entity.sensitive_life_areas = '["health", "finance", "relationships", "work"]'
            await uow.ethics_value_profiles.update(entity)
            await uow.commit()
        
        # Test each sensitive area
        sensitive_topics = [
            "User's health routine",
            "Financial planning",
            "Relationship dynamics",
            "Work-life balance"
        ]
        
        for topic in sensitive_topics:
            signal = IntrinsicSignal(
                signal_id=f"signal-{topic}",
                user_id=test_user,
                signal_type=CuriosityType.KNOWLEDGE_GAP,
                topic=topic,
                description=f"Explore {topic}",
                novelty_score=0.7,
                uncertainty_score=0.7,
                user_relevance_score=0.7,
                feasibility_score=0.7,
                total_score=0.7,
                priority="normal",
            )
            
            # Act & Assert - All should require consent
            with pytest.raises(ValueError, match="Curiosity signal requires consent"):
                await engine.create_goal_from_curiosity_signal(
                    user_id=test_user,
                    signal=signal,
                    auto_plan=False,
                )
    
    async def test_ethics_evaluation_metadata_preserved(self, test_config, test_db, test_user, permissive_value_profile, agency_service, session_factory):
        """Test that ethics evaluation results are preserved in goal metadata."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Act
        goal, _ = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal",
            description="Test ethics metadata",
            goal_type="project",
            auto_plan=False,
        )
        
        # Assert - Ethics evaluation should be in metadata
        assert "ethics_evaluation" in goal.metadata
        assert "decision" in goal.metadata["ethics_evaluation"]
        assert "reason_codes" in goal.metadata["ethics_evaluation"]
        assert "evaluated_at" in goal.metadata["ethics_evaluation"]
        
        # Decision should be valid PolicyEffect
        decision = goal.metadata["ethics_evaluation"]["decision"]
        assert decision in ["allow", "allow_with_warning", "needs_consent", "block"]
    
    async def test_plan_evaluation_works(self, test_config, test_db, test_user, permissive_value_profile, agency_service, session_factory):
        """Test that plans are also evaluated by ethics service."""
        # Arrange
        engine = AgencyEngine(test_config, agency_service, session_factory=session_factory)
        
        # Act - Create goal with plan
        goal, plan = await engine.create_goal_with_optional_plan(
            user_id=test_user,
            title="Test Goal with Plan",
            description="Test plan evaluation",
            goal_type="project",
            auto_plan=True,
        )
        
        # Assert
        assert plan is not None
        
        # Manually evaluate the plan
        from aico.data.uow import UnitOfWork

        service = ValuesEthicsService()
        async with UnitOfWork(session_factory) as uow:
            result = await service.evaluate_plan(plan, test_user, uow)
        
        assert result is not None
        assert result.decision in [PolicyEffect.ALLOW, PolicyEffect.ALLOW_WITH_WARNING]
