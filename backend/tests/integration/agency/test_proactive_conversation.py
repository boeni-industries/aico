"""
Tests for Proactive Conversation Initiation System (Phase 6.11)

Tests the complete proactive conversation flow:
- Contextual feature extraction
- Adaptivity and Civility scoring
- Contextual bandit strategy selection
- User preferences management
- Initiation creation and tracking
- Learning system updates
"""

import pytest

pytest.skip("Legacy proactive conversation initiation is deprecated; superseded by interaction request system", allow_module_level=True)

from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
import uuid

from aico.ai.agency.skills.communication.learning import (
    ContextualBanditLearner,
    AdaptivityScorer,
    CivilityScorer,
    extract_contextual_features,
    ContextualFeatures
)
from aico.ai.agency.skills.communication.user_preferences import (
    UserPreferencesManager,
    load_user_preferences
)


class TestContextualFeatureExtraction:
    """Test contextual feature extraction for proactive conversations."""
    
    @pytest.mark.asyncio
    async def test_extract_features_basic(self, test_db, test_user):
        """Test basic feature extraction."""
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        context = await extract_contextual_features(session_factory, test_user)
        
        assert isinstance(context, ContextualFeatures)
        assert context.hour_of_day >= 0 and context.hour_of_day < 24
        assert context.day_of_week >= 0 and context.day_of_week < 7
        assert context.time_since_last_interaction >= 0
        assert context.recent_response_rate >= 0 and context.recent_response_rate <= 1.0
        assert context.user_activity_level in ['low', 'medium', 'high']
    
    @pytest.mark.asyncio
    async def test_extract_features_with_history(self, test_db, test_user):
        """Test feature extraction with conversation history."""
        from aico.data.interaction.models import InteractionRequest
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        session_factory = await get_session_factory()

        # Seed initiation history
        now = datetime.now(UTC)
        async with UnitOfWork(session_factory) as uow:
            for i in range(5):
                await uow.interaction_requests.create(
                    InteractionRequest(
                        interaction_id=str(uuid.uuid4()),
                        user_id=test_user,
                        correlation_id=str(uuid.uuid4()),
                        interaction_type="question",
                        requirement="required",
                        status="answered" if i % 2 == 0 else "pending",
                        category="test",
                        severity="low",
                        title=None,
                        prompt="Test question",
                        context_json={"trigger_reason": "test"},
                        allowed_options=None,
                        expected_answer_type="text",
                        answer_text=None,
                        answer_json=None,
                        answered_at=None,
                        expires_at=None,
                        idempotency_key=f"test:{i}",
                        created_at=now - timedelta(hours=i),
                        updated_at=now - timedelta(hours=i),
                    )
                )
            await uow.commit()
        
        context = await extract_contextual_features(session_factory, test_user)
        
        # Should have detected recent activity
        assert context.time_since_last_interaction >= 0
        assert context.user_activity_level in ['low', 'medium', 'high']
        # Should have some pending initiations
        assert context.pending_initiations >= 0


class TestAdaptivityScoring:
    """Test adaptivity dimension scoring."""
    
    def test_patience_score_high(self):
        """Test patience score with high time since last interaction."""
        scorer = AdaptivityScorer()
        context = ContextualFeatures(
            hour_of_day=14,
            day_of_week=2,
            time_since_last_interaction=48.0,  # 2 days
            recent_response_rate=0.8,
            avg_response_time=300.0,
            conversation_frequency=2.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.6,
            recent_engagement_score=0.8,
            user_activity_level='medium'
        )
        
        score = scorer.calculate_patience_score(context, 48.0)
        
        # High patience - user hasn't been bothered recently
        assert score > 0.7
    
    def test_patience_score_low(self):
        """Test patience score with recent interaction."""
        scorer = AdaptivityScorer()
        context = ContextualFeatures(
            hour_of_day=14,
            day_of_week=2,
            time_since_last_interaction=0.5,  # 30 minutes
            recent_response_rate=0.8,
            avg_response_time=200.0,
            conversation_frequency=5.0,
            pending_initiations=2,
            recent_dismissals=1,
            topic_diversity=0.4,
            recent_engagement_score=0.6,
            user_activity_level='high'
        )
        
        score = scorer.calculate_patience_score(context, 0.5)
        
        # Low patience - recent interaction and pending initiations
        assert score < 0.5
    
    def test_timing_sensitivity(self):
        """Test timing sensitivity scoring."""
        scorer = AdaptivityScorer()
        
        # Morning context
        morning_context = ContextualFeatures(
            hour_of_day=8,
            day_of_week=1,  # Monday
            time_since_last_interaction=12.0,
            recent_response_rate=0.7,
            avg_response_time=250.0,
            conversation_frequency=3.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.7,
            recent_engagement_score=0.8,
            user_activity_level='high'
        )
        
        morning_score = scorer.calculate_timing_sensitivity(morning_context)
        
        # Late night context
        night_context = ContextualFeatures(
            hour_of_day=23,
            day_of_week=6,  # Sunday
            time_since_last_interaction=12.0,
            recent_response_rate=0.7,
            avg_response_time=400.0,
            conversation_frequency=1.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.5,
            recent_engagement_score=0.5,
            user_activity_level='low'
        )
        
        night_score = scorer.calculate_timing_sensitivity(night_context)
        
        # Morning on weekday should score higher than late night on weekend
        assert morning_score > night_score


class TestCivilityScoring:
    """Test civility dimension scoring."""
    
    @pytest.mark.asyncio
    async def test_boundary_respect_with_preferences(self, test_db, test_user):
        """Test boundary respect with user preferences."""
        scorer = CivilityScorer()
        
        # Load default preferences
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        prefs = await load_user_preferences(session_factory, test_user)
        
        context = ContextualFeatures(
            hour_of_day=14,
            day_of_week=2,
            time_since_last_interaction=24.0,
            recent_response_rate=0.8,
            avg_response_time=300.0,
            conversation_frequency=2.5,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.6,
            recent_engagement_score=0.75,
            user_activity_level='medium'
        )
        
        score = scorer.calculate_boundary_respect(context, prefs)
        
        # Should respect boundaries (no pending, reasonable time)
        assert score > 0.5
    
    @pytest.mark.asyncio
    async def test_boundary_respect_quiet_hours(self, test_db, test_user):
        """Test boundary respect during quiet hours."""
        scorer = CivilityScorer()
        
        # Set quiet hours (list of hours that are quiet)
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        prefs = await load_user_preferences(session_factory, test_user)
        prefs['quiet_hours'] = [22, 23, 0, 1, 2, 3, 4, 5, 6, 7]  # 10 PM to 7 AM
        
        # Context during quiet hours
        context = ContextualFeatures(
            hour_of_day=23,  # 11 PM
            day_of_week=2,
            time_since_last_interaction=24.0,
            recent_response_rate=0.8,
            avg_response_time=500.0,
            conversation_frequency=1.5,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.4,
            recent_engagement_score=0.6,
            user_activity_level='low'
        )
        
        score = scorer.calculate_boundary_respect(context, prefs)
        
        # Should penalize quiet hours (score reduced by 0.5)
        assert score == 0.5
    
    def test_emotional_intelligence(self):
        """Test emotional intelligence scoring."""
        scorer = CivilityScorer()
        
        context = ContextualFeatures(
            hour_of_day=14,
            day_of_week=2,
            time_since_last_interaction=24.0,
            recent_response_rate=0.9,  # High response rate
            avg_response_time=180.0,
            conversation_frequency=4.0,
            pending_initiations=0,
            recent_dismissals=0,  # Low dismissal rate
            topic_diversity=0.8,
            recent_engagement_score=0.9,
            user_activity_level='high'
        )
        
        score = scorer.calculate_emotional_intelligence(context, "casual_check_in")
        
        # Good emotional context (responsive user, low dismissals)
        assert score > 0.6


class TestContextualBandit:
    """Test contextual bandit strategy selection."""
    
    @pytest.mark.asyncio
    async def test_bandit_initialization(self, test_db):
        """Test bandit initialization with default arms."""
        bandit = ContextualBanditLearner(test_db)
        
        # Should have default strategies
        assert len(bandit.arms) > 0
        assert 'time_morning' in bandit.arms
        assert 'time_evening' in bandit.arms
        # Check for any strategy (arms may vary)
        
        # Each arm should have alpha and beta
        for arm_id, arm in bandit.arms.items():
            assert arm.alpha >= 1.0
            assert arm.beta >= 1.0
    
    @pytest.mark.asyncio
    async def test_strategy_selection(self, test_db):
        """Test Thompson sampling strategy selection."""
        bandit = ContextualBanditLearner(test_db)
        
        context = ContextualFeatures(
            hour_of_day=9,
            day_of_week=1,
            time_since_last_interaction=24.0,
            recent_response_rate=0.8,
            avg_response_time=250.0,
            conversation_frequency=3.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.7,
            recent_engagement_score=0.8,
            user_activity_level='high'
        )
        
        strategy_id, expected_reward = bandit.select_strategy(context)
        
        assert strategy_id is not None
        assert strategy_id in bandit.arms
        assert expected_reward >= 0 and expected_reward <= 1.0
    
    @pytest.mark.asyncio
    async def test_update_from_outcome_success(self, test_db):
        """Test bandit update from successful outcome."""
        bandit = ContextualBanditLearner(test_db)
        
        strategy_id = 'time_morning'
        initial_alpha = bandit.arms[strategy_id].alpha
        initial_beta = bandit.arms[strategy_id].beta
        
        context = ContextualFeatures(
            hour_of_day=9,
            day_of_week=1,
            time_since_last_interaction=24.0,
            recent_response_rate=0.8,
            avg_response_time=250.0,
            conversation_frequency=3.0,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.7,
            recent_engagement_score=0.8,
            user_activity_level='high'
        )
        
        bandit.update_from_outcome(
            strategy_id=strategy_id,
            context=context,
            outcome='answered',
            response_time=300.0  # 5 minutes
        )
        
        # Alpha should increase (success)
        assert bandit.arms[strategy_id].alpha > initial_alpha
        # Beta should stay same or increase slightly
        assert bandit.arms[strategy_id].beta >= initial_beta
    
    @pytest.mark.asyncio
    async def test_update_from_outcome_failure(self, test_db):
        """Test bandit update from failed outcome."""
        bandit = ContextualBanditLearner(test_db)
        
        strategy_id = 'time_evening'
        initial_alpha = bandit.arms[strategy_id].alpha
        initial_beta = bandit.arms[strategy_id].beta
        
        context = ContextualFeatures(
            hour_of_day=20,
            day_of_week=1,
            time_since_last_interaction=24.0,
            recent_response_rate=0.8,
            avg_response_time=300.0,
            conversation_frequency=2.5,
            pending_initiations=0,
            recent_dismissals=0,
            topic_diversity=0.6,
            recent_engagement_score=0.75,
            user_activity_level='medium'
        )
        
        bandit.update_from_outcome(
            strategy_id=strategy_id,
            context=context,
            outcome='dismissed',
            response_time=None
        )
        
        # Beta should increase (failure)
        assert bandit.arms[strategy_id].beta > initial_beta
        # Alpha should stay same
        assert bandit.arms[strategy_id].alpha == initial_alpha
    
    @pytest.mark.asyncio
    async def test_get_arm_statistics(self, test_db):
        """Test getting arm statistics."""
        bandit = ContextualBanditLearner(test_db)
        
        stats = bandit.get_arm_statistics()
        
        assert isinstance(stats, dict)
        assert len(stats) > 0
        
        for arm_id, arm_stats in stats.items():
            assert 'alpha' in arm_stats
            assert 'beta' in arm_stats
            assert 'expected_reward' in arm_stats
            assert 'trials' in arm_stats
            # Note: 'uncertainty' is returned, not 'confidence'
            assert 'uncertainty' in arm_stats


class TestUserPreferences:
    """Test user preferences management."""
    
    @pytest.mark.asyncio
    async def test_load_default_preferences(self, test_db, test_user):
        """Test loading default preferences."""
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        prefs = await load_user_preferences(session_factory, test_user)
        
        assert isinstance(prefs, dict)
        assert 'enabled' in prefs
        assert 'quiet_hours' in prefs
        assert 'max_initiations_per_day' in prefs
        assert 'max_pending' in prefs
        assert 'min_hours_between' in prefs
        
        # Defaults should be reasonable
        assert prefs['enabled'] is True
        assert prefs['max_initiations_per_day'] > 0
        assert prefs['max_pending'] > 0
    
    @pytest.mark.asyncio
    async def test_preferences_caching(self, test_db, test_user):
        """Test preferences caching."""
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        manager = UserPreferencesManager(session_factory)
        
        # First load
        prefs1 = await manager.get_preferences(test_user)
        
        # Second load should use cache
        prefs2 = await manager.get_preferences(test_user)
        
        assert prefs1 == prefs2
        assert test_user in manager._cache


class TestProactiveInitiationFlow:
    """Test complete proactive conversation initiation flow."""
    
    @pytest.mark.asyncio
    async def test_create_initiation(self, test_db, test_user):
        """Test creating a proactive initiation."""
        from aico.data.interaction.models import InteractionRequest
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        session_factory = await get_session_factory()

        interaction_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        async with UnitOfWork(session_factory) as uow:
            await uow.interaction_requests.create(
                InteractionRequest(
                    interaction_id=interaction_id,
                    user_id=test_user,
                    correlation_id=str(uuid.uuid4()),
                    interaction_type="question",
                    requirement="required",
                    status="pending",
                    category="proactive",
                    severity="low",
                    title=None,
                    prompt="How are you doing today?",
                    context_json={
                        "trigger_reason": "strategy_time_morning",
                        "scores": {"adaptivity": 0.75, "civility": 0.82},
                    },
                    allowed_options=None,
                    expected_answer_type="text",
                    answer_text=None,
                    answer_json=None,
                    answered_at=None,
                    expires_at=None,
                    idempotency_key=f"test_create:{interaction_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
            await uow.commit()
        
        # Verify creation
        async with UnitOfWork(session_factory) as uow:
            row = await uow.interaction_requests.get_by_id(interaction_id)
        assert row is not None
        assert row.user_id == test_user
        assert row.status == 'pending'
    
    @pytest.mark.asyncio
    async def test_respond_to_initiation(self, test_db, test_user):
        """Test responding to an initiation."""
        from aico.data.interaction.models import InteractionRequest
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        session_factory = await get_session_factory()

        # Create initiation
        interaction_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)

        async with UnitOfWork(session_factory) as uow:
            await uow.interaction_requests.create(
                InteractionRequest(
                    interaction_id=interaction_id,
                    user_id=test_user,
                    correlation_id=str(uuid.uuid4()),
                    interaction_type="question",
                    requirement="required",
                    status="pending",
                    category="proactive",
                    severity="low",
                    title=None,
                    prompt="How are you?",
                    context_json={"trigger_reason": "strategy_time_morning"},
                    allowed_options=None,
                    expected_answer_type="text",
                    answer_text=None,
                    answer_json=None,
                    answered_at=None,
                    expires_at=None,
                    idempotency_key=f"test_respond:{interaction_id}",
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            await uow.commit()
        
        # Respond to initiation
        resolved_at = datetime.now(UTC)
        response_time = int((resolved_at - created_at).total_seconds())

        async with UnitOfWork(session_factory) as uow:
            entity = await uow.interaction_requests.get_by_id(interaction_id)
            assert entity is not None
            entity.status = "answered"
            entity.answer_text = "ok"
            entity.answered_at = resolved_at
            entity.updated_at = resolved_at
            await uow.interaction_requests.update(entity)
            await uow.commit()
        
        # Verify update
        async with UnitOfWork(session_factory) as uow:
            row = await uow.interaction_requests.get_by_id(interaction_id)
        assert row.status == 'answered'
        assert row.answered_at is not None
    
    @pytest.mark.asyncio
    async def test_check_pending_initiations(self, test_db, test_user):
        """Test checking for pending initiations."""
        from aico.data.interaction.models import InteractionRequest
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork

        session_factory = await get_session_factory()

        # Create pending initiation
        interaction_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        async with UnitOfWork(session_factory) as uow:
            await uow.interaction_requests.create(
                InteractionRequest(
                    interaction_id=interaction_id,
                    user_id=test_user,
                    correlation_id=str(uuid.uuid4()),
                    interaction_type="question",
                    requirement="required",
                    status="pending",
                    category="proactive",
                    severity="low",
                    title=None,
                    prompt="Test question",
                    context_json={"trigger_reason": "test"},
                    allowed_options=None,
                    expected_answer_type="text",
                    answer_text=None,
                    answer_json=None,
                    answered_at=None,
                    expires_at=None,
                    idempotency_key=f"test_pending:{interaction_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
            await uow.commit()

        # Check for pending
        async with UnitOfWork(session_factory) as uow:
            pending = await uow.interaction_requests.list(
                filters={"user_id": test_user, "status": "pending"},
                limit=100,
            )
        assert len(pending) >= 1


class TestIntegrationFlow:
    """Test complete integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_initiation_flow(self, test_db, test_user):
        """Test complete decision flow from context to initiation."""
        # Extract context
        from aico.data.postgres.connection import get_session_factory

        session_factory = await get_session_factory()
        context = await extract_contextual_features(session_factory, test_user)
        
        # Score dimensions
        adaptivity_scorer = AdaptivityScorer()
        civility_scorer = CivilityScorer()
        user_prefs = await load_user_preferences(session_factory, test_user)
        
        patience = adaptivity_scorer.calculate_patience_score(context, context.time_since_last_interaction)
        timing = adaptivity_scorer.calculate_timing_sensitivity(context)
        adaptivity = (patience + timing) / 2
        
        boundary = civility_scorer.calculate_boundary_respect(context, user_prefs)
        emotional = civility_scorer.calculate_emotional_intelligence(context, "test")
        civility = (boundary + emotional) / 2
        
        overall = adaptivity * 0.6 + civility * 0.4
        
        # Select strategy
        bandit = ContextualBanditLearner(session_factory)
        strategy_id, expected_reward = bandit.select_strategy(context)
        
        # Verify all components work together
        assert 0 <= adaptivity <= 1.0
        assert 0 <= civility <= 1.0
        assert 0 <= overall <= 1.0
        assert strategy_id is not None
        assert 0 <= expected_reward <= 1.0
