"""
Initiate Conversation Skill

AICO-initiated skill for proactive dialogue about concerns, thoughts, or topics.
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

            initiation_id = str(uuid.uuid4())
            conversation_id = f"{user_id}_{int(datetime.now(UTC).timestamp())}"
            now_dt = datetime.now(UTC)
            now_iso = now_dt.isoformat()

            # Use UnitOfWork pattern for database operations
            if self._session_factory is None:
                raise RuntimeError("session_factory is required for InitiateConversationSkill")
            
            from aico.data.uow import UnitOfWork
            from aico.data.conversation.models import ConversationInitiation

            async with UnitOfWork(self._session_factory) as uow:
                recent_initiations = await uow.conversation_initiations.list(
                    filters={"user_id": user_id},
                    limit=1000,
                )

                duplicate_found = False
                for init in recent_initiations:
                    if (
                        init.question == message
                        and init.trigger_reason == trigger_reason
                        and init.initiated_at
                        and (now_dt - init.initiated_at).total_seconds() < 86400
                    ):
                        duplicate_found = True
                        break

                if duplicate_found:
                    logger.debug(
                        f"💭 [INITIATE_CONVERSATION] Duplicate conversation detected for user {user_id[:8]}, "
                        f"skipping creation"
                    )
                    return SkillResult(
                        success=True,
                        output={
                            "status": "skipped",
                            "reason": "duplicate_conversation",
                            "message": "Conversation already initiated recently",
                        },
                        metadata={"skill_id": self.skill_id},
                    )

                initiation = ConversationInitiation(
                    initiation_id=initiation_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    trigger_source="skill",
                    trigger_reason=trigger_reason,
                    question=message,
                    context=json.dumps({"topic": topic, "emotional_context": emotional_context}),
                    urgency="low",
                    expected_answer_type="dialogue",
                    initiated_at=now_dt,
                    resolution_status="pending",
                    resolved_at=None,
                    user_response_time=None,
                    engagement_score=None,
                )

                await uow.conversation_initiations.create(initiation)
                await uow.commit()
            
            # Publish to conversation initiation topic
            message_published = False

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

                conv_message.message.text = message
                conv_message.message.type = Message.MessageType.AICO_INITIATED
                conv_message.message.conversation_id = conversation_id
                conv_message.message.turn_number = 1

                # Add metadata as JSON in message metadata
                conv_message.message.metadata = json.dumps({
                    'topic': topic,
                    'reason': reason,
                    'emotional_context': emotional_context,
                    'urgency': 'low',
                    'expected_answer_type': 'dialogue',
                    'initiated_at': now_iso,
                })

                if self.message_bus and getattr(self.message_bus, "running", False):
                    await self.message_bus.publish(
                        topic='conversation/aico/initiate/v1',
                        payload=conv_message,
                    )
                else:
                    from aico.core.bus import MessageBusClient

                    bus_client = MessageBusClient(client_id=f"initiate_conversation_skill_{initiation_id[:8]}")
                    await bus_client.connect()
                    await bus_client.publish('conversation/aico/initiate/v1', conv_message)
                    await bus_client.disconnect()

                message_published = True
                logger.info(f"💭 [INITIATE_CONVERSATION] Published to message bus: {initiation_id[:8]}...")

            except Exception as e:
                logger.warning(f"💭 [INITIATE_CONVERSATION] Failed to publish to message bus: {e}")
            
            result = {
                "initiation_id": initiation_id,
                "conversation_id": conversation_id,
                "topic": topic,
                "message": message,
                "reason": reason,
                "emotional_context": emotional_context,
                "status": "pending",
                "initiated_at": now_iso,
            }
            
            logger.info(
                f"💭 [INITIATE_CONVERSATION] Conversation initiated: {initiation_id[:8]}... "
                f"topic='{topic}'"
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
                f"💭 [INITIATE_CONVERSATION] Failed to initiate conversation: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Failed to initiate conversation: {str(e)}",
            )
