from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class InteractionEventResponse(BaseModel):
    event_id: str
    interaction_id: str
    user_id: str
    correlation_id: str
    actor: str
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    payload_json: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class InteractionResponse(BaseModel):
    interaction_id: str
    user_id: str
    correlation_id: str

    interaction_type: str
    requirement: str
    status: str
    category: str
    severity: str

    title: Optional[str] = None
    prompt: Optional[str] = None

    context_json: Optional[dict[str, Any]] = None
    allowed_options: Optional[list[Any]] = None

    expected_answer_type: Optional[str] = None

    answer_text: Optional[str] = None
    answer_json: Optional[dict[str, Any]] = None
    answered_at: Optional[datetime] = None

    expires_at: Optional[datetime] = None
    idempotency_key: str

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InteractionDetailResponse(BaseModel):
    interaction: InteractionResponse
    events: list[InteractionEventResponse]


class InteractionListResponse(BaseModel):
    items: list[InteractionResponse]
    total: int


class AnswerInteractionRequest(BaseModel):
    answer_text: Optional[str] = None
    answer_json: Optional[dict[str, Any]] = None


class TransitionResponse(BaseModel):
    interaction: InteractionResponse
    event: InteractionEventResponse
