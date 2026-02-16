"""
Ask User Skill

AICO-initiated skill to ask the user targeted questions for information gathering.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from sqlalchemy.exc import IntegrityError

from google.protobuf.struct_pb2 import Struct

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.skills.communication.ask_user")


class AskUserSkill(Skill):
    """
    Ask the user a targeted question to fill an information gap.
    
    Creates a pending conversation initiation that waits for user response.
    Used for: Information gathering, clarification, preference discovery
    """
    
    def __init__(
        self,
        db: Optional[Any] = None,
        message_bus: Optional[Any] = None,
        session_factory: Optional[Any] = None,
    ):
        self.db = db
        self.message_bus = message_bus
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "ask_user"
    
    @property
    def name(self) -> str:
        return "Ask User"
    
    @property
    def description(self) -> str:
        return "Ask the user a targeted question to gather information or clarify understanding"
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="question",
                type=SkillParameterType.STRING,
                description="The question to ask the user",
                required=True,
            ),
            SkillParameter(
                name="context",
                type=SkillParameterType.STRING,
                description="Context explaining why you're asking",
                required=False,
                default="",
            ),
            SkillParameter(
                name="urgency",
                type=SkillParameterType.STRING,
                description="Urgency level: low, medium, high",
                required=False,
                default="medium",
            ),
            SkillParameter(
                name="expected_answer_type",
                type=SkillParameterType.STRING,
                description="Type of answer expected: text, yes_no, choice, number",
                required=False,
                default="text",
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute ask user skill - creates interaction request."""
        question = input_data.get("question")
        question_context = input_data.get("context", "")
        urgency = input_data.get("urgency", "medium")
        expected_answer_type = input_data.get("expected_answer_type", "text")
        
        logger.info(
            f"💬 [ASK_USER] Creating question for user {user_id[:8]}... "
            f"urgency={urgency}"
        )
        
        try:
            if not question:
                raise ValueError("Question is required")

            if self._session_factory is None:
                raise RuntimeError("session_factory is required for AskUserSkill")

            from aico.data.uow import UnitOfWork
            from aico.data.interaction.models import InteractionEvent, InteractionRequest
            from aico.core.bus import MessageBusClient

            interaction_id = str(uuid.uuid4())
            correlation_id = str(
                context.get("correlation_id")
                or context.get("correlationId")
                or uuid.uuid4()
            )
            now_dt = datetime.now(UTC)

            idempotency_key = f"ask_user:information_gap:{uuid.uuid5(uuid.NAMESPACE_URL, question).hex}"

            async with UnitOfWork(self._session_factory) as uow:
                existing = await uow.interaction_requests.get_by_idempotency_key(user_id, idempotency_key)
                if existing is not None:
                    return SkillResult(
                        success=True,
                        output={
                            "status": existing.status,
                            "interaction_id": existing.interaction_id,
                            "correlation_id": existing.correlation_id,
                            "created_at": existing.created_at.isoformat() if existing.created_at else None,
                        },
                        metadata={"skill_id": self.skill_id},
                    )

                interaction = InteractionRequest(
                    interaction_id=interaction_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    interaction_type="question",
                    requirement="required",
                    status="pending",
                    category="skill",
                    severity=urgency,
                    title=None,
                    prompt=question,
                    context_json={
                        "trigger_reason": "information_gap",
                        "context": question_context,
                    },
                    allowed_options=None,
                    expected_answer_type=expected_answer_type,
                    answer_text=None,
                    answer_json=None,
                    answered_at=None,
                    expires_at=None,
                    idempotency_key=idempotency_key,
                    created_at=now_dt,
                    updated_at=now_dt,
                )

                try:
                    await uow.interaction_requests.create(interaction)

                    event = InteractionEvent(
                        event_id=str(uuid.uuid4()),
                        interaction_id=interaction_id,
                        user_id=user_id,
                        correlation_id=correlation_id,
                        actor="system:agency_skill",
                        event_type="created",
                        from_status=None,
                        to_status="pending",
                        payload_json={"skill_id": self.skill_id},
                        created_at=now_dt,
                    )
                    await uow.interaction_events.create(event)
                    await uow.commit()
                except IntegrityError:
                    await uow.rollback()
                    existing = await uow.interaction_requests.get_by_idempotency_key(user_id, idempotency_key)
                    if existing is None:
                        raise
                    interaction = existing
                    interaction_id = existing.interaction_id
                    correlation_id = existing.correlation_id
                    event = InteractionEvent(
                        event_id=str(uuid.uuid4()),
                        interaction_id=existing.interaction_id,
                        user_id=existing.user_id,
                        correlation_id=existing.correlation_id,
                        actor="system:agency_skill",
                        event_type="created",
                        from_status=None,
                        to_status=existing.status,
                        payload_json={"skill_id": self.skill_id, "idempotent": True},
                        created_at=now_dt,
                    )

            try:
                bus_client = MessageBusClient(client_id=f"ask_user_skill_{interaction.interaction_id[:8]}")
                await bus_client.connect()
                payload_struct = Struct()
                payload_struct.update({"interaction": interaction.model_dump(mode="json"), "event": event.model_dump(mode="json")})
                await bus_client.publish(
                    f"interaction.notifications.{user_id}",
                    payload_struct,
                    correlation_id=correlation_id,
                )
            finally:
                try:
                    await bus_client.disconnect()
                except Exception:
                    pass
            
            result = {
                "question": question,
                "context": question_context,
                "urgency": urgency,
                "expected_answer_type": expected_answer_type,
                "status": "pending",
                "interaction_id": interaction_id,
                "correlation_id": correlation_id,
                "created_at": now_dt.isoformat(),
            }
            
            logger.info(
                f"💬 [ASK_USER] Question created: {interaction_id[:8]}... "
                f"waiting for user response"
            )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.now(UTC).isoformat(),
                    "interaction_id": interaction_id,
                },
            )
            
        except Exception as e:
            logger.exception(
                f"💬 [ASK_USER] Failed to create question: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Failed to ask user: {str(e)}",
            )
