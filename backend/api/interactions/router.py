from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.data.interaction.models import InteractionEvent, InteractionRequest
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow
from backend.api.conversation.dependencies import get_current_user
from google.protobuf.struct_pb2 import Struct

from .schemas import (
    AnswerInteractionRequest,
    InteractionDetailResponse,
    InteractionEventResponse,
    InteractionListResponse,
    InteractionResponse,
    TransitionResponse,
)


router = APIRouter()
logger = get_logger("backend.api.interactions")


_TERMINAL_STATUSES = {"answered", "approved", "rejected", "cancelled", "expired"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_interaction_response(i: InteractionRequest) -> InteractionResponse:
    return InteractionResponse(**i.model_dump())


def _to_event_response(e: InteractionEvent) -> InteractionEventResponse:
    return InteractionEventResponse(**e.model_dump())


def _assert_not_expired(i: InteractionRequest) -> None:
    if i.expires_at is not None and i.expires_at <= _utcnow():
        raise HTTPException(status_code=410, detail="interaction expired")


def _assert_can_transition(i: InteractionRequest, to_status: str) -> None:
    if i.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="interaction is terminal")

    if to_status in _TERMINAL_STATUSES and i.status == to_status:
        raise HTTPException(status_code=409, detail="invalid state transition")


async def _get_owned_interaction(
    *,
    uow: UnitOfWork,
    interaction_id: str,
    user_id: str,
) -> InteractionRequest:
    interaction = await uow.interaction_requests.get_by_id(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="interaction not found")
    if interaction.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    _assert_not_expired(interaction)
    return interaction


async def _append_event_and_update(
    *,
    uow: UnitOfWork,
    interaction: InteractionRequest,
    actor: str,
    event_type: str,
    to_status: Optional[str],
    payload_json: Optional[dict[str, Any]] = None,
) -> tuple[InteractionRequest, InteractionEvent]:
    from_status = interaction.status

    if to_status is not None:
        _assert_can_transition(interaction, to_status)
        interaction.status = to_status
        interaction.updated_at = _utcnow()
        await uow.interaction_requests.update(interaction)

    event = InteractionEvent(
        event_id=str(uuid.uuid4()),
        interaction_id=interaction.interaction_id,
        user_id=interaction.user_id,
        correlation_id=interaction.correlation_id,
        actor=actor,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        payload_json=payload_json,
        created_at=_utcnow(),
    )
    await uow.interaction_events.create(event)

    await uow.commit()
    return interaction, event


async def _publish_interaction_notification(
    *,
    user_id: str,
    correlation_id: str,
    interaction: InteractionRequest,
    event: InteractionEvent,
) -> None:
    bus_client = MessageBusClient("interaction_api")
    await bus_client.connect()
    try:
        payload_struct = Struct()
        payload_struct.update({"interaction": interaction.model_dump(), "event": event.model_dump()})
        await bus_client.publish(
            f"interaction.notifications.{user_id}",
            payload_struct,
            correlation_id=correlation_id,
        )
    finally:
        await bus_client.disconnect()


@router.get("", response_model=InteractionListResponse)
async def list_interactions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]

    filters: dict[str, Any] = {"user_id": user_id}
    if status_filter is not None:
        filters["status"] = status_filter

    items = await uow.interaction_requests.list(filters=filters, limit=limit, offset=offset)
    total = await uow.interaction_requests.count(filters=filters)

    return InteractionListResponse(
        items=[_to_interaction_response(i) for i in items],
        total=total,
    )


@router.get("/{interaction_id}", response_model=InteractionDetailResponse)
async def get_interaction_detail(
    interaction_id: str,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)
    events = await uow.interaction_events.list(filters={"interaction_id": interaction_id}, limit=10000)

    return InteractionDetailResponse(
        interaction=_to_interaction_response(interaction),
        events=[_to_event_response(e) for e in events],
    )


@router.post("/{interaction_id}/answer", response_model=TransitionResponse)
async def answer_interaction(
    interaction_id: str,
    request: AnswerInteractionRequest,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)

    if interaction.interaction_type not in {"question", "choice", "dialogue"}:
        raise HTTPException(status_code=422, detail="interaction type not answerable")

    if request.answer_text is None and request.answer_json is None:
        raise HTTPException(status_code=400, detail="answer required")

    interaction.answer_text = request.answer_text
    interaction.answer_json = request.answer_json
    interaction.answered_at = _utcnow()

    interaction, event = await _append_event_and_update(
        uow=uow,
        interaction=interaction,
        actor=f"user:{user_id}",
        event_type="answered",
        to_status="answered",
        payload_json={"answer_text": request.answer_text, "answer_json": request.answer_json},
    )

    try:
        await _publish_interaction_notification(
            user_id=user_id,
            correlation_id=interaction.correlation_id,
            interaction=interaction,
            event=event,
        )
    except Exception as e:
        logger.warning("Failed to publish interaction notification", extra={"error": str(e)})

    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/approve", response_model=TransitionResponse)
async def approve_interaction(
    interaction_id: str,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)

    if interaction.interaction_type != "approval":
        raise HTTPException(status_code=422, detail="interaction type not approvable")

    interaction, event = await _append_event_and_update(
        uow=uow,
        interaction=interaction,
        actor=f"user:{user_id}",
        event_type="approved",
        to_status="approved",
        payload_json=None,
    )

    try:
        await _publish_interaction_notification(
            user_id=user_id,
            correlation_id=interaction.correlation_id,
            interaction=interaction,
            event=event,
        )
    except Exception as e:
        logger.warning("Failed to publish interaction notification", extra={"error": str(e)})

    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/reject", response_model=TransitionResponse)
async def reject_interaction(
    interaction_id: str,
    reason: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)

    if interaction.interaction_type != "approval":
        raise HTTPException(status_code=422, detail="interaction type not rejectable")

    interaction, event = await _append_event_and_update(
        uow=uow,
        interaction=interaction,
        actor=f"user:{user_id}",
        event_type="rejected",
        to_status="rejected",
        payload_json={"reason": reason} if reason else None,
    )

    try:
        await _publish_interaction_notification(
            user_id=user_id,
            correlation_id=interaction.correlation_id,
            interaction=interaction,
            event=event,
        )
    except Exception as e:
        logger.warning("Failed to publish interaction notification", extra={"error": str(e)})

    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/cancel", response_model=TransitionResponse)
async def cancel_interaction(
    interaction_id: str,
    reason: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)

    interaction, event = await _append_event_and_update(
        uow=uow,
        interaction=interaction,
        actor=f"user:{user_id}",
        event_type="cancelled",
        to_status="cancelled",
        payload_json={"reason": reason} if reason else None,
    )

    try:
        await _publish_interaction_notification(
            user_id=user_id,
            correlation_id=interaction.correlation_id,
            interaction=interaction,
            event=event,
        )
    except Exception as e:
        logger.warning("Failed to publish interaction notification", extra={"error": str(e)})

    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))
