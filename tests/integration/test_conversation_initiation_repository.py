"""
Integration tests for ConversationInitiationRepository.

Tests ConversationInitiationRepository with real PostgreSQL database.
"""

import pytest
import uuid
from datetime import datetime, UTC

from aico.data.interaction.models import InteractionRequest
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


class TestInteractionRequestsRepository:
    """Test interaction_requests repository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_interaction(self, uow, test_user):
        interaction = InteractionRequest(
            interaction_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            correlation_id=str(uuid.uuid4()),
            interaction_type="question",
            requirement="required",
            status="pending",
            category="test",
            severity="low",
            title=None,
            prompt="How are you feeling today?",
            context_json={"trigger_reason": "test"},
            allowed_options=None,
            expected_answer_type="text",
            answer_text=None,
            answer_json=None,
            answered_at=None,
            expires_at=None,
            idempotency_key=f"test:{uuid.uuid4().hex}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        created = await uow.interaction_requests.create(interaction)
        await uow.commit()

        assert created.interaction_id == interaction.interaction_id
        assert created.user_id == test_user.uuid
        assert created.prompt == "How are you feeling today?"
    
    @pytest.mark.asyncio
    async def test_get_interaction_by_id(self, uow, test_user):
        interaction = InteractionRequest(
            interaction_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            correlation_id=str(uuid.uuid4()),
            interaction_type="question",
            requirement="required",
            status="pending",
            category="test",
            severity="low",
            title=None,
            prompt="Test prompt",
            context_json=None,
            allowed_options=None,
            expected_answer_type="text",
            answer_text=None,
            answer_json=None,
            answered_at=None,
            expires_at=None,
            idempotency_key=f"test:{uuid.uuid4().hex}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await uow.interaction_requests.create(interaction)
        await uow.commit()

        found = await uow.interaction_requests.get_by_id(interaction.interaction_id)
        assert found is not None
        assert found.interaction_id == interaction.interaction_id
    
    @pytest.mark.asyncio
    async def test_update_interaction(self, uow, test_user):
        interaction = InteractionRequest(
            interaction_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            correlation_id=str(uuid.uuid4()),
            interaction_type="question",
            requirement="required",
            status="pending",
            category="test",
            severity="low",
            title=None,
            prompt="Update me",
            context_json=None,
            allowed_options=None,
            expected_answer_type="text",
            answer_text=None,
            answer_json=None,
            answered_at=None,
            expires_at=None,
            idempotency_key=f"test_update:{uuid.uuid4().hex}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await uow.interaction_requests.create(interaction)
        await uow.commit()

        interaction.status = "answered"
        interaction.answer_text = "ok"
        interaction.answered_at = datetime.now(UTC)
        updated = await uow.interaction_requests.update(interaction)
        await uow.commit()

        assert updated.status == "answered"

        found = await uow.interaction_requests.get_by_id(interaction.interaction_id)
        assert found is not None
        assert found.status == "answered"
        assert found.answer_text == "ok"
    
    @pytest.mark.asyncio
    async def test_delete_interaction(self, uow, test_user):
        interaction = InteractionRequest(
            interaction_id=str(uuid.uuid4()),
            user_id=test_user.uuid,
            correlation_id=str(uuid.uuid4()),
            interaction_type="question",
            requirement="required",
            status="pending",
            category="test",
            severity="low",
            title=None,
            prompt="Delete me",
            context_json=None,
            allowed_options=None,
            expected_answer_type="text",
            answer_text=None,
            answer_json=None,
            answered_at=None,
            expires_at=None,
            idempotency_key=f"test_delete:{uuid.uuid4().hex}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await uow.interaction_requests.create(interaction)
        await uow.commit()

        await uow.interaction_requests.delete(interaction.interaction_id)
        await uow.commit()

        found = await uow.interaction_requests.get_by_id(interaction.interaction_id)
        assert found is None
    
    @pytest.mark.asyncio
    async def test_list_interactions(self, uow, test_user):
        for i in range(3):
            interaction = InteractionRequest(
                interaction_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                correlation_id=str(uuid.uuid4()),
                interaction_type="question",
                requirement="required",
                status="pending" if i < 2 else "answered",
                category="test",
                severity="low",
                title=None,
                prompt=f"List {i}",
                context_json=None,
                allowed_options=None,
                expected_answer_type="text",
                answer_text=None,
                answer_json=None,
                answered_at=None,
                expires_at=None,
                idempotency_key=f"test_list:{uuid.uuid4().hex}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.interaction_requests.create(interaction)

        await uow.commit()

        all_items = await uow.interaction_requests.list(filters={"user_id": test_user.uuid}, limit=1000)
        assert len(all_items) >= 3

        pending = await uow.interaction_requests.list(filters={"user_id": test_user.uuid, "status": "pending"}, limit=1000)
        assert len(pending) >= 2
    
    @pytest.mark.asyncio
    async def test_count_interactions(self, uow, test_user):
        for i in range(3):
            interaction = InteractionRequest(
                interaction_id=str(uuid.uuid4()),
                user_id=test_user.uuid,
                correlation_id=str(uuid.uuid4()),
                interaction_type="question",
                requirement="required",
                status="pending",
                category="test",
                severity="low",
                title=None,
                prompt=f"Count {i}",
                context_json=None,
                allowed_options=None,
                expected_answer_type="text",
                answer_text=None,
                answer_json=None,
                answered_at=None,
                expires_at=None,
                idempotency_key=f"test_count:{uuid.uuid4().hex}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.interaction_requests.create(interaction)

        await uow.commit()

        count = await uow.interaction_requests.count(filters={"user_id": test_user.uuid})
        assert count >= 3
    
    # @pytest.mark.asyncio
    # async def test_get_pending_for_user(self, uow, test_user):
    #     """Test getting pending initiations for a user - METHOD NOT IMPLEMENTED."""
    #     pass
    
    # @pytest.mark.asyncio
    # async def test_resolve_initiation(self, uow, test_user):
    #     """Test resolving an initiation - METHOD NOT IMPLEMENTED."""
    #     pass
