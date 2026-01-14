"""
Integration tests for ConversationInitiationsRepository.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.conversation.models import ConversationInitiation
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
    user_id = "conv_init_test_user"
    existing = await uow.users.get_by_id(user_id)
    if not existing:
        user = UserProfile(
            uuid=user_id,
            full_name="Conv Init Test User",
            nickname="conv_tester",
            user_type="parent",
            is_active=True,
            primary_language="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await uow.users.create(user)
        await uow.commit()
    return await uow.users.get_by_id(user_id)


class TestConversationInitiationsRepository:
    
    @pytest.mark.asyncio
    async def test_create_initiation(self, uow, test_user):
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id="conv_123",
            trigger_source="proactive",
            initiated_at=datetime.now(UTC),
        )
        
        created = await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        assert created.initiation_id == initiation.initiation_id
        assert created.trigger_source == "proactive"
    
    @pytest.mark.asyncio
    async def test_get_initiation_by_id(self, uow, test_user):
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id="conv_456",
            trigger_source="reminder",
            initiated_at=datetime.now(UTC),
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found is not None
        assert found.conversation_id == "conv_456"
    
    @pytest.mark.asyncio
    async def test_update_initiation(self, uow, test_user):
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id="conv_789",
            trigger_source="followup",
            initiated_at=datetime.now(UTC),
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        initiation.resolution_status = "resolved"
        initiation.resolved_at = datetime.now(UTC)
        updated = await uow.conversation_initiations.update(initiation)
        await uow.commit()
        
        assert updated.resolution_status == "resolved"
        
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found.resolved_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_initiation(self, uow, test_user):
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id="conv_del",
            trigger_source="test",
            initiated_at=datetime.now(UTC),
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        success = await uow.conversation_initiations.delete(initiation.initiation_id)
        await uow.commit()
        
        assert success is True
        
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_initiations(self, uow, test_user):
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=f"conv_list_{i}",
                trigger_source="list_test",
                initiated_at=datetime.now(UTC),
                resolution_status="pending" if i < 2 else "resolved",
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        all_initiations = await uow.conversation_initiations.list(filters={"user_id": test_user.uuid})
        assert len(all_initiations) >= 3
        
        pending = await uow.conversation_initiations.list(filters={"resolution_status": "pending"})
        assert len(pending) >= 2
    
    @pytest.mark.asyncio
    async def test_count_initiations(self, uow, test_user):
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=f"conv_count_{i}",
                trigger_source="count_test",
                initiated_at=datetime.now(UTC),
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        count = await uow.conversation_initiations.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_pending_initiations(self, uow, test_user):
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=f"conv_pending_{i}",
                trigger_source="pending_test",
                initiated_at=datetime.now(UTC),
                resolution_status="pending" if i < 2 else "resolved",
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        pending = await uow.conversation_initiations.get_pending_initiations(test_user.uuid)
        assert len(pending) >= 2
        for init in pending:
            assert init.resolution_status == "pending"
