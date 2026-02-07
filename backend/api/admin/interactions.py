from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.data.interaction.models import InteractionEvent, InteractionRequest
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow
from backend.api.admin.dependencies import verify_admin_token
from google.protobuf.struct_pb2 import Struct

from backend.api.interactions.schemas import (
    InteractionDetailResponse,
    InteractionEventResponse,
    InteractionListResponse,
    InteractionResponse,
    TransitionResponse,
)


router = APIRouter()
logger = get_logger("backend.api.admin.interactions")


_TERMINAL_STATUSES = {"answered", "approved", "rejected", "cancelled", "expired"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_interaction_response(i: InteractionRequest) -> InteractionResponse:
    return InteractionResponse(**i.model_dump())


def _to_event_response(e: InteractionEvent) -> InteractionEventResponse:
    return InteractionEventResponse(**e.model_dump())


def _assert_can_transition(i: InteractionRequest, to_status: str) -> None:
    if i.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="interaction is terminal")
    if to_status in _TERMINAL_STATUSES and i.status == to_status:
        raise HTTPException(status_code=409, detail="invalid state transition")


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


async def _publish_admin_notifications(
    *,
    user_id: str,
    correlation_id: str,
    interaction: InteractionRequest,
    event: InteractionEvent,
) -> None:
    bus_client = MessageBusClient("interaction_admin_api")
    await bus_client.connect()
    try:
        payload_struct = Struct()
        payload_struct.update({"interaction": interaction.model_dump(), "event": event.model_dump()})
        await bus_client.publish(
            f"interaction.notifications.{user_id}",
            payload_struct,
            correlation_id=correlation_id,
        )
        await bus_client.publish(
            "interaction.notifications.admin",
            payload_struct,
            correlation_id=correlation_id,
        )
    finally:
        await bus_client.disconnect()


@router.get("", response_model=InteractionListResponse)
async def list_interactions_admin(
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    correlation_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user=Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    filters: dict[str, Any] = {}
    if user_id is not None:
        filters["user_id"] = user_id
    if status_filter is not None:
        filters["status"] = status_filter
    if correlation_id is not None:
        filters["correlation_id"] = correlation_id

    items = await uow.interaction_requests.list(filters=filters or None, limit=limit, offset=offset)
    total = await uow.interaction_requests.count(filters=filters or None)

    return InteractionListResponse(items=[_to_interaction_response(i) for i in items], total=total)


@router.get("/{interaction_id}", response_model=InteractionDetailResponse)
async def get_interaction_detail_admin(
    interaction_id: str,
    admin_user=Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    interaction = await uow.interaction_requests.get_by_id(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="interaction not found")

    events = await uow.interaction_events.list(filters={"interaction_id": interaction_id}, limit=10000)

    return InteractionDetailResponse(
        interaction=_to_interaction_response(interaction),
        events=[_to_event_response(e) for e in events],
    )


@router.post("/{interaction_id}/cancel", response_model=TransitionResponse)
async def cancel_interaction_admin(
    interaction_id: str,
    reason: str = Query(...),
    on_behalf_of: str = Query(...),
    admin_user=Depends(verify_admin_token),
    uow: UnitOfWork = Depends(get_uow),
):
    interaction = await uow.interaction_requests.get_by_id(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="interaction not found")

    interaction, event = await _append_event_and_update(
        uow=uow,
        interaction=interaction,
        actor=f"admin:{admin_user.get('user_uuid')}",
        event_type="cancelled",
        to_status="cancelled",
        payload_json={"reason": reason, "on_behalf_of": on_behalf_of},
    )

    try:
        await _publish_admin_notifications(
            user_id=interaction.user_id,
            correlation_id=interaction.correlation_id,
            interaction=interaction,
            event=event,
        )
    except Exception as e:
        logger.warning("Failed to publish interaction admin notification", extra={"error": str(e)})

    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))
