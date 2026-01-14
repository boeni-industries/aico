"""
Integration tests for AMSBehavioralFeedbackRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.ams.models import BehavioralFeedback
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
    user_id = "behavioral_feedback_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Behavioral Feedback Test User",
            nickname="feedback_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestAMSBehavioralFeedbackRepository:
    
    @pytest.mark.asyncio
    async def test_create_feedback(self, uow, test_user):
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            skill_id="test_skill",
            reward=1,
            reason="positive",
            processed=0,
        )
        
        created = await uow.ams_behavioral_feedback.create(feedback)
        await uow.commit()
        
        assert created.feedback_id == feedback.feedback_id
        assert created.reward == 1
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_id(self, uow, test_user):
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            skill_id="get_skill",
            reward=-1,
            processed=0,
        )
        
        await uow.ams_behavioral_feedback.create(feedback)
        await uow.commit()
        
        found = await uow.ams_behavioral_feedback.get_by_id(feedback.feedback_id)
        assert found is not None
        assert found.skill_id == "get_skill"
    
    @pytest.mark.asyncio
    async def test_update_feedback(self, uow, test_user):
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            processed=0,
        )
        
        await uow.ams_behavioral_feedback.create(feedback)
        await uow.commit()
        
        feedback.processed = 1
        feedback.outcome = "success"
        updated = await uow.ams_behavioral_feedback.update(feedback)
        await uow.commit()
        
        assert updated.processed == 1
        
        found = await uow.ams_behavioral_feedback.get_by_id(feedback.feedback_id)
        assert found.outcome == "success"
    
    @pytest.mark.asyncio
    async def test_delete_feedback(self, uow, test_user):
        feedback = BehavioralFeedback(
            feedback_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            timestamp=datetime.now(UTC).isoformat(),
            processed=0,
        )
        
        await uow.ams_behavioral_feedback.create(feedback)
        await uow.commit()
        
        success = await uow.ams_behavioral_feedback.delete(feedback.feedback_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.ams_behavioral_feedback.get_by_id(feedback.feedback_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_feedback(self, uow, test_user):
        for i in range(3):
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                skill_id=f"list_skill_{i}",
                processed=0 if i < 2 else 1,
            )
            await uow.ams_behavioral_feedback.create(feedback)
        
        await uow.commit()
        
        all_feedback = await uow.ams_behavioral_feedback.list(filters={"user_id": test_user.uuid})
        assert len(all_feedback) >= 3
        
        unprocessed = await uow.ams_behavioral_feedback.list(filters={"processed": 0})
        assert len(unprocessed) >= 2
    
    @pytest.mark.asyncio
    async def test_count_feedback(self, uow, test_user):
        for i in range(3):
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                processed=0,
            )
            await uow.ams_behavioral_feedback.create(feedback)
        
        await uow.commit()
        
        count = await uow.ams_behavioral_feedback.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_unprocessed(self, uow, test_user):
        for i in range(3):
            feedback = BehavioralFeedback(
                feedback_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                timestamp=datetime.now(UTC).isoformat(),
                processed=0 if i < 2 else 1,
            )
            await uow.ams_behavioral_feedback.create(feedback)
        
        await uow.commit()
        
        unprocessed = await uow.ams_behavioral_feedback.get_unprocessed()
        assert len(unprocessed) >= 2
        for fb in unprocessed:
            assert fb.processed == 0
