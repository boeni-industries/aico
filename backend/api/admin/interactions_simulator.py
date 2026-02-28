"""
Admin Interaction Simulator

Provides admin-only endpoints for creating simulated interaction requests
to test end-to-end flow (DB persistence + message bus + WebSocket delivery).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.data.interaction.models import InteractionEvent, InteractionRequest
from aico.data.uow import UnitOfWork
from backend.core.postgres_dependencies import get_uow
from backend.api.admin.dependencies import verify_admin_token
from google.protobuf.struct_pb2 import Struct

from backend.api.interactions.schemas import (
    InteractionResponse,
    InteractionEventResponse,
    TransitionResponse,
)


router = APIRouter()
logger = get_logger("backend.api.admin.interactions_simulator")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SimulateInteractionRequest(BaseModel):
    """Request schema for simulating an interaction."""
    
    user_id: str = Field(..., description="Target user UUID")
    interaction_type: str = Field(..., description="question | choice | dialogue | approval")
    requirement: str = Field(..., description="required | optional")
    severity: str = Field(default="medium", description="low | medium | high")
    category: str = Field(default="general", description="Interaction category")
    
    title: Optional[str] = Field(None, description="Interaction title")
    prompt: str = Field(..., description="Interaction prompt/question text")
    
    expected_answer_type: Optional[str] = Field(None, description="text | yes_no | number | date | choice")
    allowed_options: Optional[list[Any]] = Field(None, description="For choice type: list of allowed options")
    
    context_json: Optional[dict[str, Any]] = Field(None, description="Additional context metadata")
    
    expires_in_seconds: Optional[int] = Field(None, description="Expiration time in seconds from now")
    correlation_id: Optional[str] = Field(None, description="Correlation ID (auto-generated if not provided)")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key (auto-generated if not provided)")
    
    broadcast_admin: bool = Field(default=False, description="Also publish to interaction.notifications.admin")
    
    scenario: Optional[str] = Field(None, description="create_only | create_then_answer | create_then_cancel")
    answer_text: Optional[str] = Field(None, description="Answer text for scenario resolution")
    answer_json: Optional[dict[str, Any]] = Field(None, description="Answer JSON for scenario resolution")


class SimulateInteractionResponse(BaseModel):
    """Response schema for simulated interaction."""
    
    interaction: InteractionResponse
    event: InteractionEventResponse
    scenario_executed: Optional[str] = None
    additional_events: Optional[list[InteractionEventResponse]] = None


@router.post("/simulate", response_model=SimulateInteractionResponse)
async def simulate_interaction(
    request: SimulateInteractionRequest,
    uow: UnitOfWork = Depends(get_uow),
    _admin: dict = Depends(verify_admin_token),
):
    """
    Create a simulated interaction request for testing.
    
    This endpoint creates an interaction_request + interaction_event(created)
    and publishes to interaction.notifications.<user_uuid>.
    
    Optionally executes a scenario (answer/cancel) to test state transitions.
    """
    
    # Validate interaction_type
    valid_types = {"question", "choice", "dialogue", "approval"}
    if request.interaction_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"interaction_type must be one of {valid_types}")
    
    # Validate requirement
    if request.requirement not in {"required", "optional"}:
        raise HTTPException(status_code=400, detail="requirement must be 'required' or 'optional'")
    
    # Validate severity
    if request.severity not in {"low", "medium", "high"}:
        raise HTTPException(status_code=400, detail="severity must be 'low', 'medium', or 'high'")
    
    # Validate expected_answer_type if provided
    if request.expected_answer_type:
        valid_answer_types = {"text", "yes_no", "number", "date", "choice"}
        if request.expected_answer_type not in valid_answer_types:
            raise HTTPException(status_code=400, detail=f"expected_answer_type must be one of {valid_answer_types}")
    
    # Validate choice-specific fields
    if request.interaction_type == "choice" and not request.allowed_options:
        raise HTTPException(status_code=400, detail="allowed_options required for choice interaction_type")
    
    # Generate IDs
    interaction_id = str(uuid.uuid4())
    correlation_id = request.correlation_id or str(uuid.uuid4())
    idempotency_key = request.idempotency_key or f"sim_{interaction_id}"
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_seconds:
        expires_at = _utcnow() + timedelta(seconds=request.expires_in_seconds)
    
    # Create interaction request
    interaction = InteractionRequest(
        interaction_id=interaction_id,
        user_id=request.user_id,
        correlation_id=correlation_id,
        interaction_type=request.interaction_type,
        requirement=request.requirement,
        status="pending",
        category=request.category,
        severity=request.severity,
        title=request.title,
        prompt=request.prompt,
        context_json=request.context_json,
        allowed_options=request.allowed_options,
        expected_answer_type=request.expected_answer_type,
        expires_at=expires_at,
        idempotency_key=idempotency_key,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    
    # Create initial event
    event = InteractionEvent(
        event_id=str(uuid.uuid4()),
        interaction_id=interaction_id,
        user_id=request.user_id,
        correlation_id=correlation_id,
        actor="system:simulator",
        event_type="created",
        from_status=None,
        to_status="pending",
        payload_json={"simulated": True, "scenario": request.scenario},
        created_at=_utcnow(),
    )
    
    # Persist to database
    await uow.interaction_requests.create(interaction)
    await uow.interaction_events.create(event)
    await uow.commit()
    
    logger.info(
        f"Simulated interaction created",
        extra={
            "interaction_id": interaction_id,
            "user_id": request.user_id,
            "interaction_type": request.interaction_type,
            "correlation_id": correlation_id,
        },
    )
    
    # Publish notification
    bus_client = None
    try:
        bus_client = MessageBusClient(client_id=f"simulator_{interaction_id[:8]}")
        await bus_client.connect()
        
        logger.info(
            f"Simulator connected to message bus",
            extra={"interaction_id": interaction_id, "client_id": f"simulator_{interaction_id[:8]}"},
        )
        
        payload_struct = Struct()
        payload_struct.update({
            "interaction": interaction.model_dump(mode="json"),
            "event": event.model_dump(mode="json"),
        })
        
        # Publish to user topic (durable)
        topic = f"interaction.notifications.{request.user_id}"
        await bus_client.publish_durable(
            topic,
            payload_struct,
            correlation_id=correlation_id,
            audit_subject="audit.events.interaction",
        )
        
        logger.info(
            f"Published interaction notification to user topic",
            extra={
                "interaction_id": interaction_id,
                "topic": topic,
                "user_id": request.user_id,
                "correlation_id": correlation_id,
            },
        )
        
        # Optionally publish to admin topic
        if request.broadcast_admin:
            await bus_client.publish_durable(
                "interaction.notifications.admin",
                payload_struct,
                correlation_id=correlation_id,
                audit_subject="audit.events.interaction",
            )
            logger.info(
                f"Published interaction notification to admin topic",
                extra={"interaction_id": interaction_id},
            )
    
    finally:
        if bus_client:
            await bus_client.disconnect()
    
    # Execute scenario if requested
    additional_events = []
    scenario_executed = None
    
    if request.scenario == "create_then_answer":
        # Simulate answer transition
        interaction.status = "answered"
        interaction.answer_text = request.answer_text
        interaction.answer_json = request.answer_json
        interaction.answered_at = _utcnow()
        interaction.updated_at = _utcnow()
        
        answer_event = InteractionEvent(
            event_id=str(uuid.uuid4()),
            interaction_id=interaction_id,
            user_id=request.user_id,
            correlation_id=correlation_id,
            actor="system:simulator",
            event_type="answered",
            from_status="pending",
            to_status="answered",
            payload_json={
                "answer_text": request.answer_text,
                "answer_json": request.answer_json,
                "simulated": True,
            },
            created_at=_utcnow(),
        )
        
        await uow.interaction_requests.update(interaction)
        await uow.interaction_events.create(answer_event)
        await uow.commit()
        
        additional_events.append(InteractionEventResponse(**answer_event.model_dump()))
        scenario_executed = "create_then_answer"
        
        # Publish answer notification
        try:
            bus_client = MessageBusClient(client_id=f"simulator_{interaction_id[:8]}_answer")
            await bus_client.connect()
            
            payload_struct = Struct()
            payload_struct.update({
                "interaction": interaction.model_dump(mode="json"),
                "event": answer_event.model_dump(mode="json"),
            })
            
            await bus_client.publish(
                f"interaction.notifications.{request.user_id}",
                payload_struct,
                correlation_id=correlation_id,
            )
            
            if request.broadcast_admin:
                await bus_client.publish(
                    "interaction.notifications.admin",
                    payload_struct,
                    correlation_id=correlation_id,
                )
        
        finally:
            if bus_client:
                await bus_client.disconnect()
    
    elif request.scenario == "create_then_cancel":
        # Simulate cancel transition
        interaction.status = "cancelled"
        interaction.updated_at = _utcnow()
        
        cancel_event = InteractionEvent(
            event_id=str(uuid.uuid4()),
            interaction_id=interaction_id,
            user_id=request.user_id,
            correlation_id=correlation_id,
            actor="system:simulator",
            event_type="cancelled",
            from_status="pending",
            to_status="cancelled",
            payload_json={"reason": "simulated cancellation", "simulated": True},
            created_at=_utcnow(),
        )
        
        await uow.interaction_requests.update(interaction)
        await uow.interaction_events.create(cancel_event)
        await uow.commit()
        
        additional_events.append(InteractionEventResponse(**cancel_event.model_dump()))
        scenario_executed = "create_then_cancel"
        
        # Publish cancel notification
        try:
            bus_client = MessageBusClient(client_id=f"simulator_{interaction_id[:8]}_cancel")
            await bus_client.connect()
            
            payload_struct = Struct()
            payload_struct.update({
                "interaction": interaction.model_dump(mode="json"),
                "event": cancel_event.model_dump(mode="json"),
            })
            
            await bus_client.publish(
                f"interaction.notifications.{request.user_id}",
                payload_struct,
                correlation_id=correlation_id,
            )
            
            if request.broadcast_admin:
                await bus_client.publish(
                    "interaction.notifications.admin",
                    payload_struct,
                    correlation_id=correlation_id,
                )
        
        finally:
            if bus_client:
                await bus_client.disconnect()
    
    return SimulateInteractionResponse(
        interaction=InteractionResponse(**interaction.model_dump()),
        event=InteractionEventResponse(**event.model_dump()),
        scenario_executed=scenario_executed,
        additional_events=additional_events if additional_events else None,
    )
