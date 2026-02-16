"""
Integration tests for ProactiveAnalyticsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.proactive.models import ProactiveAnalytics
from aico.data.user.models import UserProfile
from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


@pytest.fixture
async def session_factory():
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    user_id = f"proactive_test_user_{uuid.uuid4().hex[:8]}"
    user = UserProfile(
        uuid=user_id,
        full_name="Proactive Test User",
        nickname="proactive_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestProactiveAnalyticsRepository:
    
    @pytest.mark.asyncio
    async def test_create_analytics(self, uow, test_user):
        analytics = ProactiveAnalytics(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="reminder_pattern",
            created_at=datetime.now(UTC),
        )
        
        created = await uow.proactive_analytics.create(analytics)
        await uow.commit()
        
        assert created.id == analytics.id
        assert created.event_type == "reminder_pattern"
    
    @pytest.mark.asyncio
    async def test_get_analytics_by_id(self, uow, test_user):
        analytics = ProactiveAnalytics(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="goal_suggestion",
            confidence_score=0.85,
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_analytics.create(analytics)
        await uow.commit()
        
        found = await uow.proactive_analytics.get_by_id(analytics.id)
        assert found is not None
        assert found.confidence_score == 0.85
    
    @pytest.mark.asyncio
    async def test_update_analytics(self, uow, test_user):
        analytics = ProactiveAnalytics(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="behavior_insight",
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_analytics.create(analytics)
        await uow.commit()
        
        analytics.triggered_action = "notification_sent"
        analytics.confidence_score = 0.9
        updated = await uow.proactive_analytics.update(analytics)
        await uow.commit()
        
        assert updated.triggered_action == "notification_sent"
        
        found = await uow.proactive_analytics.get_by_id(analytics.id)
        assert found.confidence_score == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_analytics(self, uow, test_user):
        analytics = ProactiveAnalytics(
            id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            event_type="test_event",
            created_at=datetime.now(UTC),
        )
        
        await uow.proactive_analytics.create(analytics)
        await uow.commit()
        
        success = await uow.proactive_analytics.delete(analytics.id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.proactive_analytics.get_by_id(analytics.id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_analytics(self, uow, test_user):
        for i in range(3):
            analytics = ProactiveAnalytics(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="reminder_pattern" if i < 2 else "goal_suggestion",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_analytics.create(analytics)
        
        await uow.commit()
        
        all_analytics = await uow.proactive_analytics.list(filters={"user_id": test_user.uuid})
        assert len(all_analytics) >= 3
        
        reminders = await uow.proactive_analytics.list(filters={"event_type": "reminder_pattern"})
        assert len(reminders) >= 2
    
    @pytest.mark.asyncio
    async def test_count_analytics(self, uow, test_user):
        for i in range(3):
            analytics = ProactiveAnalytics(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="test_event",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_analytics.create(analytics)
        
        await uow.commit()
        
        count = await uow.proactive_analytics.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(self, uow, test_user):
        for i in range(3):
            analytics = ProactiveAnalytics(
                id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                event_type="reminder_pattern" if i < 2 else "goal_suggestion",
                created_at=datetime.now(UTC),
            )
            await uow.proactive_analytics.create(analytics)
        
        await uow.commit()
        
        all_user = await uow.proactive_analytics.get_user_analytics(test_user.uuid)
        assert len(all_user) >= 3
        
        reminders = await uow.proactive_analytics.get_user_analytics(test_user.uuid, event_type="reminder_pattern")
        assert len(reminders) >= 2
