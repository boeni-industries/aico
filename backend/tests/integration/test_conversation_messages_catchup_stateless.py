import uuid
from datetime import datetime, timedelta, UTC

import warnings

import pytest

try:
    from pydantic.warnings import PydanticDeprecatedSince20

    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
except Exception:
    pass

from aico.data.conversation.models import ConversationMessage
from aico.data.uow import UnitOfWork
from backend.api.conversation.router import catchup_my_messages


@pytest.mark.asyncio
async def test_conversation_messages_catchup_after_message_id(session_factory):
    tenant_id = "test-tenant"
    user_id = "user-1"
    conversation_id = f"{user_id}_{uuid.uuid4().hex}"

    t0 = datetime.now(UTC)
    msg_user_id = f"m-{uuid.uuid4().hex}"
    msg_ai_1_id = f"m-{uuid.uuid4().hex}"
    msg_ai_2_id = f"m-{uuid.uuid4().hex}"

    async with UnitOfWork(session_factory) as uow:
        await uow.conversation_messages.create(
            ConversationMessage(
                message_id=msg_user_id,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                actor_type="user",
                actor_id=user_id,
                message_type="user_input",
                content="hello",
                request_id=f"req-{uuid.uuid4().hex}",
                created_at=t0,
            )
        )
        await uow.conversation_messages.create(
            ConversationMessage(
                message_id=msg_ai_1_id,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                actor_type="assistant",
                actor_id="assistant",
                message_type="ai_response",
                content="hi",
                request_id=f"req-{uuid.uuid4().hex}",
                created_at=t0 + timedelta(seconds=1),
            )
        )
        await uow.conversation_messages.create(
            ConversationMessage(
                message_id=msg_ai_2_id,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                actor_type="assistant",
                actor_id="assistant",
                message_type="ai_response",
                content="how can I help?",
                request_id=f"req-{uuid.uuid4().hex}",
                created_at=t0 + timedelta(seconds=2),
            )
        )
        await uow.commit()

    async with UnitOfWork(session_factory) as uow:
        res = await catchup_my_messages(
            conversation_id=conversation_id,
            after_message_id=msg_ai_1_id,
            limit=100,
            current_user={"user_uuid": user_id, "tenant_id": tenant_id},
            uow=uow,
        )

    ids = [m["id"] for m in res.messages]
    assert ids == [msg_ai_2_id]
    assert res.conversation_id == conversation_id
