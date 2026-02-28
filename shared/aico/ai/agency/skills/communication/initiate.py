"""
Initiate Conversation Skill

AICO-initiated skill for proactive dialogue about concerns, thoughts, or topics.
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


logger = get_logger("shared.ai.agency.skills.communication.initiate")


class InitiateConversationSkill(Skill):
    """
    Initiate a conversation with the user about a topic, concern, or thought.
    
    More exploratory than AskUser - for expressing AICO's thoughts/concerns.
    Used for: Sharing concerns, discussing topics, expressing needs
    """
    
    def __init__(
        self,
        db: Optional[Any] = None,  # Skills being redesigned
        message_bus: Optional[Any] = None,
        session_factory: Optional[Any] = None,
    ):
        self.db = db
        self.message_bus = message_bus
        self._session_factory = session_factory
    
    @property
    def skill_id(self) -> str:
        return "initiate_conversation"
    
    @property
    def name(self) -> str:
        return "Initiate Conversation"
    
    @property
    def description(self) -> str:
        return "Start a conversation with the user about a topic, concern, or thought"
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="topic",
                type=SkillParameterType.STRING,
                description="The topic or subject to discuss",
                required=True,
            ),
            SkillParameter(
                name="message",
                type=SkillParameterType.STRING,
                description="Opening message to start the conversation",
                required=True,
            ),
            SkillParameter(
                name="reason",
                type=SkillParameterType.STRING,
                description="Why AICO wants to discuss this",
                required=False,
                default="",
            ),
            SkillParameter(
                name="emotional_context",
                type=SkillParameterType.STRING,
                description="Emotional tone: curious, concerned, excited, thoughtful",
                required=False,
                default="thoughtful",
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute initiate conversation skill."""
        topic = input_data.get("topic")
        message = input_data.get("message")
        reason = input_data.get("reason", "")
        emotional_context = input_data.get("emotional_context", "thoughtful")
        
        logger.info(
            f"💭 [INITIATE_CONVERSATION] Starting conversation for user {user_id[:8]}... "
            f"topic='{topic}' emotion={emotional_context}"
        )
        
        try:
            if not topic or not message:
                raise ValueError("Topic and message are required")

            trigger_reason = reason or "proactive_dialogue"

            now_dt = datetime.now(UTC)

            if self._session_factory is None:
                raise RuntimeError("session_factory is required for InitiateConversationSkill")

            from aico.data.uow import UnitOfWork
            from aico.data.interaction.models import InteractionEvent, InteractionRequest
            from aico.core.bus import MessageBusClient

            interaction_id = str(uuid.uuid4())
            correlation_id = str(
                context.get("correlation_id")
                or context.get("correlationId")
                or uuid.uuid4()
            )

            idempotency_key = f"initiate_conversation:{uuid.uuid5(uuid.NAMESPACE_URL, message).hex}"

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
                    interaction_type="dialogue",
                    requirement="optional",
                    status="pending",
                    category="skill",
                    severity="low",
                    title=topic,
                    prompt=message,
                    context_json={
                        "trigger_reason": trigger_reason,
                        "topic": topic,
                        "reason": reason,
                        "emotional_context": emotional_context,
                    },
                    allowed_options=None,
                    expected_answer_type="dialogue",
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
                bus_client = MessageBusClient(client_id=f"initiate_conversation_skill_{interaction.interaction_id[:8]}")
                await bus_client.connect()
                payload_struct = Struct()
                payload_struct.update({"interaction": interaction.model_dump(mode="json"), "event": event.model_dump(mode="json")})
                await bus_client.publish_durable(
                    f"interaction.notifications.{user_id}",
                    payload_struct,
                    correlation_id=correlation_id,
                    audit_subject="audit.events.interaction",
                )
            finally:
                try:
                    await bus_client.disconnect()
                except Exception:
                    pass
            
            result = {
                "topic": topic,
                "message": message,
                "reason": reason,
                "emotional_context": emotional_context,
                "status": "pending",
                "interaction_id": interaction_id,
                "correlation_id": correlation_id,
                "created_at": now_dt.isoformat(),
            }
            
            logger.info(
                f"💭 [INITIATE_CONVERSATION] Interaction initiated: {interaction_id[:8]}... "
                f"topic='{topic}'"
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
                f"💭 [INITIATE_CONVERSATION] Failed to initiate conversation: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Failed to initiate conversation: {str(e)}",
            )
