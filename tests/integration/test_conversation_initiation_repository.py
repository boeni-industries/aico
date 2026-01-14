"""
Integration tests for ConversationInitiationRepository.

Tests ConversationInitiationRepository with real PostgreSQL database.
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
    """Create async session factory for tests."""
    factory = await get_session_factory()
    return factory


@pytest.fixture
async def uow(session_factory):
    """Create Unit of Work for tests."""
    uow = UnitOfWork(session_factory)
    async with uow:
        yield uow


@pytest.fixture
async def test_user(uow):
    """Create a test user for conversation tests."""
    user = UserProfile(
        uuid=str(uuid.uuid4()),
        full_name="Conversation Test User",
        nickname="conv_tester",
        user_type="parent",
        is_active=True,
        primary_language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.users.create(user)
    await uow.commit()
    return user


class TestConversationInitiationRepository:
    """Test ConversationInitiationRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_initiation(self, uow, test_user):
        """Test creating a new conversation initiation."""
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id=str(uuid.uuid4()),
            trigger_source="proactive",
            initiated_at=datetime.now(UTC),
            question="How are you feeling today?",
            urgency="medium",
        )
        
        created = await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        assert created.initiation_id == initiation.initiation_id
        assert created.user_id == test_user.uuid
        assert created.question == "How are you feeling today?"
    
    @pytest.mark.asyncio
    async def test_get_initiation_by_id(self, uow, test_user):
        """Test retrieving initiation by ID."""
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id=str(uuid.uuid4()),
            trigger_source="scheduled",
            initiated_at=datetime.now(UTC),
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found is not None
        assert found.initiation_id == initiation.initiation_id
        assert found.trigger_source == "scheduled"
    
    @pytest.mark.asyncio
    async def test_update_initiation(self, uow, test_user):
        """Test updating an initiation."""
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id=str(uuid.uuid4()),
            trigger_source="proactive",
            initiated_at=datetime.now(UTC),
            resolution_status="pending",
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        # Update the initiation
        initiation.resolution_status = "resolved"
        initiation.engagement_score = 0.85
        updated = await uow.conversation_initiations.update(initiation)
        await uow.commit()
        
        assert updated.resolution_status == "resolved"
        
        # Verify update persisted
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found.engagement_score == 0.85
    
    @pytest.mark.asyncio
    async def test_delete_initiation(self, uow, test_user):
        """Test deleting an initiation."""
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id=str(uuid.uuid4()),
            trigger_source="manual",
            initiated_at=datetime.now(UTC),
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        # Delete the initiation
        success = await uow.conversation_initiations.delete(initiation.initiation_id)
        await uow.commit()
        
        assert success is True
        
        # Verify it's gone
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_initiations(self, uow, test_user):
        """Test listing initiations with filters."""
        conv_id = str(uuid.uuid4())
        
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=conv_id if i < 2 else str(uuid.uuid4()),
                trigger_source="proactive" if i < 2 else "scheduled",
                initiated_at=datetime.now(UTC),
                resolution_status="pending" if i < 2 else "resolved",
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        # List all initiations for user
        all_initiations = await uow.conversation_initiations.list(filters={"user_id": test_user.uuid})
        assert len(all_initiations) >= 3
        
        # List by conversation
        conv_initiations = await uow.conversation_initiations.list(filters={"conversation_id": conv_id})
        assert len(conv_initiations) >= 2
        
        # List by status
        pending = await uow.conversation_initiations.list(filters={"resolution_status": "pending"})
        assert len(pending) >= 2
    
    @pytest.mark.asyncio
    async def test_count_initiations(self, uow, test_user):
        """Test counting initiations."""
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=str(uuid.uuid4()),
                trigger_source="proactive",
                initiated_at=datetime.now(UTC),
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        count = await uow.conversation_initiations.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_get_pending_for_user(self, uow, test_user):
        """Test getting pending initiations for user."""
        for i in range(3):
            initiation = ConversationInitiation(
                initiation_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                conversation_id=str(uuid.uuid4()),
                trigger_source="proactive",
                initiated_at=datetime.now(UTC),
                resolution_status="pending" if i < 2 else "resolved",
            )
            await uow.conversation_initiations.create(initiation)
        
        await uow.commit()
        
        pending = await uow.conversation_initiations.get_pending_for_user(test_user.uuid)
        assert len(pending) >= 2
        for init in pending:
            assert init.resolution_status == "pending"
    
    @pytest.mark.asyncio
    async def test_resolve_initiation(self, uow, test_user):
        """Test resolving an initiation."""
        initiation = ConversationInitiation(
            initiation_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            conversation_id=str(uuid.uuid4()),
            trigger_source="proactive",
            initiated_at=datetime.now(UTC),
            resolution_status="pending",
        )
        
        await uow.conversation_initiations.create(initiation)
        await uow.commit()
        
        # Resolve the initiation
        success = await uow.conversation_initiations.resolve_initiation(
            initiation.initiation_id,
            engagement_score=0.92
        )
        await uow.commit()
        
        assert success is True
        
        # Verify it's resolved
        found = await uow.conversation_initiations.get_by_id(initiation.initiation_id)
        assert found.resolution_status == "resolved"
        assert found.resolved_at is not None
        assert found.engagement_score == 0.92
