"""
Ask User Skill

AICO-initiated skill to ask the user targeted questions for information gathering.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

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
        """Execute ask user skill - creates conversation initiation."""
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

            initiation_id = str(uuid.uuid4())
            conversation_id = f"{user_id}_{int(datetime.now(UTC).timestamp())}"
            now_dt = datetime.now(UTC)
            now_iso = now_dt.isoformat()

            # Prefer PostgreSQL UnitOfWork/session_factory path when available
            if self._session_factory is not None:
                from aico.data.uow import UnitOfWork
                from aico.data.conversation.models import ConversationInitiation

                async with UnitOfWork(self._session_factory) as uow:
                    recent_initiations = await uow.conversation_initiations.list(
                        filters={"user_id": user_id},
                        limit=1000,
                    )

                    duplicate_found = False
                    twenty_four_hours_ago = now_dt.replace(microsecond=0) - (datetime.now(UTC) - datetime.now(UTC))
                    for init in recent_initiations:
                        if (
                            init.question == question
                            and init.trigger_reason == "information_gap"
                            and init.initiated_at
                            and (now_dt - init.initiated_at).total_seconds() < 86400
                        ):
                            duplicate_found = True
                            break

                    if duplicate_found:
                        logger.debug(
                            f"💬 [ASK_USER] Duplicate question detected for user {user_id[:8]}, "
                            f"skipping creation"
                        )
                        return SkillResult(
                            success=True,
                            output={
                                "status": "skipped",
                                "reason": "duplicate_question",
                                "message": "Question already asked recently",
                            },
                            metadata={"skill_id": self.skill_id},
                        )

                    initiation = ConversationInitiation(
                        initiation_id=initiation_id,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        trigger_source="skill",
                        trigger_reason="information_gap",
                        question=question,
                        context=question_context,
                        urgency=urgency,
                        expected_answer_type=expected_answer_type,
                        initiated_at=now_dt,
                        resolution_status="pending",
                        resolved_at=None,
                        user_response_time=None,
                        engagement_score=None,
                    )

                    await uow.conversation_initiations.create(initiation)
                    await uow.commit()

            else:
                if not self.db:
                    raise RuntimeError("Database connection not available")

                duplicate = self.db.execute(
                    """SELECT COUNT(*) as count
                       FROM conversation_initiations
                       WHERE user_id = ?
                       AND question = ?
                       AND trigger_reason = 'information_gap'
                       AND datetime(initiated_at) > datetime('now', '-24 hours')""",
                    (user_id, question),
                ).fetchone()

                if duplicate and duplicate["count"] > 0:
                    logger.debug(
                        f"💬 [ASK_USER] Duplicate question detected for user {user_id[:8]}, "
                        f"skipping creation"
                    )
                    return SkillResult(
                        success=True,
                        output={
                            "status": "skipped",
                            "reason": "duplicate_question",
                            "message": "Question already asked recently",
                        },
                        metadata={"skill_id": self.skill_id},
                    )

                self.db.execute(
                    """INSERT INTO conversation_initiations 
                       (initiation_id, user_id, conversation_id, trigger_source, 
                        trigger_reason, question, context, urgency, expected_answer_type,
                        initiated_at, resolution_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        initiation_id,
                        user_id,
                        conversation_id,
                        "skill",
                        "information_gap",
                        question,
                        question_context,
                        urgency,
                        expected_answer_type,
                        now_iso,
                        "pending",
                    ),
                )
                self.db.commit()
            
            try:
                from aico.proto.aico_conversation_pb2 import ConversationMessage, Message
                from google.protobuf.timestamp_pb2 import Timestamp

                proto_timestamp = Timestamp()
                proto_timestamp.FromDatetime(datetime.now(UTC))

                conv_message = ConversationMessage(
                    timestamp=proto_timestamp,
                    source="agency_skill",
                    message_id=initiation_id,
                    user_id=user_id,
                )

                full_message = question
                if question_context:
                    full_message = f"{question_context}\n\n{question}"

                conv_message.message.text = full_message
                conv_message.message.type = Message.MessageType.AICO_INITIATED
                conv_message.message.conversation_id = conversation_id
                conv_message.message.turn_number = 1

                if self.message_bus and getattr(self.message_bus, "running", False):
                    await self.message_bus.publish(
                        topic="conversation/aico/initiate/v1",
                        payload=conv_message,
                    )
                else:
                    from aico.core.bus import MessageBusClient

                    bus_client = MessageBusClient(client_id=f"ask_user_skill_{initiation_id[:8]}")
                    await bus_client.connect()
                    await bus_client.publish("conversation/aico/initiate/v1", conv_message)
                    await bus_client.disconnect()

                logger.info(f"💬 [ASK_USER] Published to message bus: {initiation_id[:8]}...")

            except Exception as e:
                logger.warning(f"💬 [ASK_USER] Failed to publish to message bus: {e}")
            
            result = {
                "initiation_id": initiation_id,
                "conversation_id": conversation_id,
                "question": question,
                "context": question_context,
                "urgency": urgency,
                "expected_answer_type": expected_answer_type,
                "status": "pending",
                "initiated_at": now,
            }
            
            logger.info(
                f"💬 [ASK_USER] Question created: {initiation_id[:8]}... "
                f"waiting for user response"
            )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.now(UTC).isoformat(),
                    "initiation_id": initiation_id,
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
