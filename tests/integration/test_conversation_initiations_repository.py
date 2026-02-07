"""
Integration tests for ConversationInitiationsRepository.
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


class TestInteractionRequestsRepository:
    
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
            prompt="test",
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

        created = await uow.interaction_requests.create(interaction)
        await uow.commit()

        assert created.interaction_id == interaction.interaction_id
        assert created.status == "pending"
    
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
            prompt="test",
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
                prompt=f"test {i}",
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
                prompt=f"count {i}",
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
