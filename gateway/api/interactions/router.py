from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from google.protobuf.struct_pb2 import Struct

from aico.common.errors import raise_api_error
from aico.common.postgres_dependencies import get_uow
from aico.core.bus import MessageBusClient
from aico.core.logging import get_logger
from aico.data.interaction.models import InteractionEvent, InteractionRequest
from aico.data.uow import UnitOfWork
from gateway.api.dependencies import get_current_user
from gateway.api.interactions.schemas import (
    AnswerInteractionRequest,
    InteractionDetailResponse,
    InteractionEventResponse,
    InteractionListResponse,
    InteractionResponse,
    TransitionResponse,
)

router = APIRouter()
logger = get_logger("gateway.api.interactions")
_message_bus_client_cache: MessageBusClient | None = None
_TERMINAL_STATUSES = {"answered", "approved", "rejected", "cancelled", "expired"}


async def get_message_bus_client(request: Request) -> Optional[MessageBusClient]:
    global _message_bus_client_cache
    if _message_bus_client_cache is not None:
        return _message_bus_client_cache
    start = time.perf_counter()
    try:
        client = MessageBusClient("gateway_interactions_api")
        await asyncio.wait_for(client.connect(), timeout=0.25)
        _message_bus_client_cache = client
        logger.info("Message bus client connected for interactions", extra={"elapsed_ms": int((time.perf_counter() - start) * 1000)})
        return client
    except asyncio.TimeoutError:
        logger.warning("Message bus client connect timed out for interactions", extra={"timeout_s": 0.25, "elapsed_ms": int((time.perf_counter() - start) * 1000)})
        return None
    except Exception:
        logger.exception("Message bus client connect failed for interactions", extra={"elapsed_ms": int((time.perf_counter() - start) * 1000)})
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def _to_interaction_response(i: InteractionRequest) -> InteractionResponse:
    data = i.model_dump()
    data["answered_at"] = _iso_or_none(data.get("answered_at"))
    data["expires_at"] = _iso_or_none(data.get("expires_at"))
    data["created_at"] = _iso_or_none(data.get("created_at"))
    data["updated_at"] = _iso_or_none(data.get("updated_at"))
    return InteractionResponse(**data)


def _to_event_response(e: InteractionEvent) -> InteractionEventResponse:
    data = e.model_dump()
    data["created_at"] = _iso_or_none(data.get("created_at"))
    return InteractionEventResponse(**data)


def _assert_not_expired(i: InteractionRequest) -> None:
    if i.expires_at is not None and i.expires_at <= _utcnow():
        raise_api_error(status_code=410, error_code="INTERACTION_EXPIRED", message="interaction expired")


def _assert_can_transition(i: InteractionRequest, to_status: str) -> None:
    if i.status in _TERMINAL_STATUSES:
        raise_api_error(status_code=409, error_code="INTERACTION_TERMINAL", message="interaction is terminal")
    if to_status in _TERMINAL_STATUSES and i.status == to_status:
        raise_api_error(status_code=409, error_code="INTERACTION_INVALID_TRANSITION", message="invalid state transition")


async def _get_owned_interaction(*, uow: UnitOfWork, interaction_id: str, user_id: str) -> InteractionRequest:
    interaction = await uow.interaction_requests.get_by_id(interaction_id)
    if interaction is None:
        raise_api_error(status_code=404, error_code="INTERACTION_NOT_FOUND", message="interaction not found")
    if interaction.user_id != user_id:
        raise_api_error(status_code=403, error_code="FORBIDDEN", message="forbidden")
    _assert_not_expired(interaction)
    return interaction


async def _append_event_and_update(*, uow: UnitOfWork, interaction: InteractionRequest, actor: str, event_type: str, to_status: Optional[str], payload_json: Optional[dict[str, Any]] = None) -> tuple[InteractionRequest, InteractionEvent]:
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


async def _publish_interaction_notification(*, user_id: str, correlation_id: str, interaction: InteractionRequest, event: InteractionEvent, bus_client: MessageBusClient) -> None:
    payload_struct = Struct()
    payload_struct.update({"interaction": interaction.model_dump(mode="json"), "event": event.model_dump(mode="json")})
    await bus_client.publish_durable(
        f"interaction.notifications.{user_id}",
        payload_struct,
        correlation_id=correlation_id,
        audit_subject="audit.events.interaction",
    )


async def _publish_interaction_notification_safely(*, user_id: str, correlation_id: str, interaction: InteractionRequest, event: InteractionEvent, bus_client: Optional[MessageBusClient], timeout_s: float = 0.25) -> None:
    if bus_client is None:
        return
    try:
        await asyncio.wait_for(
            _publish_interaction_notification(
                user_id=user_id,
                correlation_id=correlation_id,
                interaction=interaction,
                event=event,
                bus_client=bus_client,
            ),
            timeout=timeout_s,
        )
    except Exception:
        logger.exception("Interaction notification publish failed", extra={"interaction_id": interaction.interaction_id, "correlation_id": correlation_id, "user_id": user_id})


@router.get("", response_model=InteractionListResponse)
async def list_interactions(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    requirement: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    filters: dict[str, Any] = {"user_id": current_user["user_uuid"]}
    if status is not None:
        filters["status"] = status
    if type is not None:
        filters["interaction_type"] = type
    if requirement is not None:
        filters["requirement"] = requirement
    if severity is not None:
        filters["severity"] = severity
    items = await uow.interaction_requests.list(filters=filters, limit=limit, offset=offset)
    total = await uow.interaction_requests.count(filters=filters)
    return InteractionListResponse(items=[_to_interaction_response(i) for i in items], total=total)


@router.get("/{interaction_id}", response_model=InteractionDetailResponse)
async def get_interaction_detail(
    interaction_id: str,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=current_user["user_uuid"])
    events = await uow.interaction_events.list(filters={"interaction_id": interaction_id}, limit=10000)
    return InteractionDetailResponse(interaction=_to_interaction_response(interaction), events=[_to_event_response(e) for e in events])


@router.post("/{interaction_id}/answer", response_model=TransitionResponse)
async def answer_interaction(
    interaction_id: str,
    request: AnswerInteractionRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    bus_client: Optional[MessageBusClient] = Depends(get_message_bus_client),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)
    if interaction.interaction_type not in {"question", "choice", "dialogue", "ack"}:
        raise_api_error(status_code=422, error_code="INTERACTION_NOT_ANSWERABLE", message="interaction type not answerable")
    if request.answer_text is None and request.answer_json is None:
        raise_api_error(status_code=400, error_code="INTERACTION_ANSWER_REQUIRED", message="answer required")
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
    background_tasks.add_task(_publish_interaction_notification_safely, user_id=user_id, correlation_id=interaction.correlation_id, interaction=interaction, event=event, bus_client=bus_client)
    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/approve", response_model=TransitionResponse)
async def approve_interaction(
    interaction_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    bus_client: Optional[MessageBusClient] = Depends(get_message_bus_client),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)
    if interaction.interaction_type != "approval":
        raise_api_error(status_code=422, error_code="INTERACTION_NOT_APPROVABLE", message="interaction type not approvable")
    interaction, event = await _append_event_and_update(uow=uow, interaction=interaction, actor=f"user:{user_id}", event_type="approved", to_status="approved")
    background_tasks.add_task(_publish_interaction_notification_safely, user_id=user_id, correlation_id=interaction.correlation_id, interaction=interaction, event=event, bus_client=bus_client)
    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/reject", response_model=TransitionResponse)
async def reject_interaction(
    interaction_id: str,
    background_tasks: BackgroundTasks,
    reason: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    bus_client: Optional[MessageBusClient] = Depends(get_message_bus_client),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)
    if interaction.interaction_type != "approval":
        raise_api_error(status_code=422, error_code="INTERACTION_NOT_REJECTABLE", message="interaction type not rejectable")
    interaction, event = await _append_event_and_update(uow=uow, interaction=interaction, actor=f"user:{user_id}", event_type="rejected", to_status="rejected", payload_json={"reason": reason} if reason else None)
    background_tasks.add_task(_publish_interaction_notification_safely, user_id=user_id, correlation_id=interaction.correlation_id, interaction=interaction, event=event, bus_client=bus_client)
    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))


@router.post("/{interaction_id}/cancel", response_model=TransitionResponse)
async def cancel_interaction(
    interaction_id: str,
    background_tasks: BackgroundTasks,
    reason: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    bus_client: Optional[MessageBusClient] = Depends(get_message_bus_client),
):
    user_id = current_user["user_uuid"]
    interaction = await _get_owned_interaction(uow=uow, interaction_id=interaction_id, user_id=user_id)
    interaction, event = await _append_event_and_update(uow=uow, interaction=interaction, actor=f"user:{user_id}", event_type="cancelled", to_status="cancelled", payload_json={"reason": reason} if reason else None)
    background_tasks.add_task(_publish_interaction_notification_safely, user_id=user_id, correlation_id=interaction.correlation_id, interaction=interaction, event=event, bus_client=bus_client)
    return TransitionResponse(interaction=_to_interaction_response(interaction), event=_to_event_response(event))
