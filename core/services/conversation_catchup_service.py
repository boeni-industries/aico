from typing import Any

from pydantic import BaseModel

from aico.data.uow import UnitOfWork


class CatchupMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[dict[str, Any]]


async def catchup_my_messages(
    *,
    conversation_id: str,
    after_message_id: str | None,
    limit: int,
    current_user: dict,
    uow: UnitOfWork,
) -> CatchupMessagesResponse:
    tenant_id = str(current_user.get("tenant_id") or "")
    user_id = str(current_user.get("user_uuid") or current_user.get("user_id") or "")
    if not tenant_id or not user_id:
        raise ValueError("current_user must include tenant_id and user_uuid/user_id")

    after_turn = 0
    if after_message_id:
        after_message = await uow.conversation_messages.get_by_id(str(after_message_id))
        if after_message and after_message.tenant_id == tenant_id and after_message.conversation_id == conversation_id:
            after_turn = int(after_message.turn_number or 0)

    rows = await uow.conversation_messages.list_after_turn(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        after_turn=after_turn,
        limit=int(limit),
    )

    messages = []
    for row in rows:
        if str(row.user_id) != user_id:
            continue
        messages.append(
            {
                "id": row.message_id,
                "conversation_id": row.conversation_id,
                "user_id": row.user_id,
                "actor_type": row.actor_type,
                "actor_id": row.actor_id,
                "message_type": row.message_type,
                "content": row.content,
                "request_id": row.request_id,
                "turn_number": row.turn_number,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    return CatchupMessagesResponse(conversation_id=conversation_id, messages=messages)
