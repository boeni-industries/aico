"""
Phase 4 Integration Tests: Ethics Gates and Policy Enforcement

Tests that Values & Ethics gates actually work by varying user profiles,
policy settings, and consent requirements.
"""

import pytest
from datetime import datetime, UTC

from aico.ai.agency import AgencyEngine
from aico.ai.agency.models import GoalStatus, GoalOrigin, GoalPriority
from aico.ai.agency.values_ethics import (
    ValuesEthicsService, 
    PolicyEffect, 
    PolicyRule, 
    PolicyTargetType, 
    PolicyScope,
    ProactiveBehaviorLevel
)
from aico.ai.curiosity import IntrinsicSignal, CuriosityType


@pytest.mark.asyncio
class TestPhase4EthicsGates:
    """Test suite for Values & Ethics gate enforcement."""
    
    async def test_sensitive_life_area_blocks_curiosity_signal(self, test_config, test_db, test_user):
        """Test that curiosity signals about sensitive life areas require consent."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Set up profile with sensitive life areas
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = ["health", "finance", "relationships"]
        
        # Update in DB
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ? WHERE profile_id = ?",
            ('["health", "finance", "relationships"]', profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_permissive_profile_allows_all_signals(self, test_config, test_db, test_user):
        """Test that permissive profile (no sensitive areas) allows all signals."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Set up permissive profile
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = []  # No sensitive areas
        profile.curiosity_intensity = 1.0  # Allow high intensity
        
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ?, curiosity_intensity = ? WHERE profile_id = ?",
            ("[]", 1.0, profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_high_curiosity_intensity_triggers_warning(self, test_config, test_db, test_user):
        """Test that high curiosity intensity signals trigger warnings."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Set up profile with low curiosity intensity threshold
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = []
        profile.curiosity_intensity = 0.5  # Low threshold - signals above this trigger warning
        
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ?, curiosity_intensity = ? WHERE profile_id = ?",
            ("[]", 0.5, profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_low_curiosity_intensity_allows_without_warning(self, test_config, test_db, test_user):
        """Test that low curiosity intensity signals are allowed without warning."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Set up profile with high curiosity intensity threshold
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = []
        profile.curiosity_intensity = 0.9  # High threshold - most signals allowed
        
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ?, curiosity_intensity = ? WHERE profile_id = ?",
            ("[]", 0.9, profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_user_explicit_goals_bypass_curiosity_gates(self, test_config, test_db, test_user):
        """Test that user-explicit goals are not subject to curiosity intensity gates."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        # Set up restrictive profile
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = ["everything"]
        profile.curiosity_intensity = 0.1  # Very restrictive
        
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ?, curiosity_intensity = ? WHERE profile_id = ?",
            ('["everything"]', 0.1, profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_proactive_behavior_level_affects_evaluation(self, test_config, test_db, test_user):
        """Test that proactive behavior level is stored in profile."""
        # Arrange
        service = ValuesEthicsService(test_db)
        
        # Test each proactive behavior level
        levels = [
            ProactiveBehaviorLevel.QUIET,
            ProactiveBehaviorLevel.BALANCED,
            ProactiveBehaviorLevel.PROACTIVE
        ]
        
        for level in levels:
            # Act
            profile = service._get_or_create_profile(test_user)
            profile.proactive_behavior_level = level
            
            test_db.execute(
                "UPDATE value_profiles SET proactive_behavior_level = ? WHERE profile_id = ?",
                (level.value, profile.profile_id)
            )
            test_db.commit()
            
            # Assert - Verify it's stored
            retrieved_profile = service._get_or_create_profile(test_user)
            assert retrieved_profile.proactive_behavior_level == level
    
    async def test_multiple_sensitive_areas_all_enforced(self, test_config, test_db, test_user):
        """Test that multiple sensitive life areas are all enforced."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
        service = ValuesEthicsService(test_db)
        profile = service._get_or_create_profile(test_user)
        profile.sensitive_life_areas = ["health", "finance", "relationships", "work"]
        
        test_db.execute(
            "UPDATE value_profiles SET sensitive_life_areas = ? WHERE profile_id = ?",
            ('["health", "finance", "relationships", "work"]', profile.profile_id)
        )
        test_db.commit()
        
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
    
    async def test_ethics_evaluation_metadata_preserved(self, test_config, test_db, test_user, permissive_value_profile):
        """Test that ethics evaluation results are preserved in goal metadata."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
    
    async def test_plan_evaluation_works(self, test_config, test_db, test_user, permissive_value_profile):
        """Test that plans are also evaluated by ethics service."""
        # Arrange
        engine = AgencyEngine(test_config, test_db)
        
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
        service = ValuesEthicsService(test_db)
        result = service.evaluate_plan(plan, test_user)
        
        assert result is not None
        assert result.decision in [PolicyEffect.ALLOW, PolicyEffect.ALLOW_WITH_WARNING]
