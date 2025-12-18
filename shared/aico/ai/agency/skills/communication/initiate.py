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
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.communication.initiate")


class InitiateConversationSkill(Skill):
    """
    Initiate a conversation with the user about a topic, concern, or thought.
    
    More exploratory than AskUser - for expressing AICO's thoughts/concerns.
    Used for: Sharing concerns, discussing topics, expressing needs
    """
    
    def __init__(
        self, 
        db: Optional[EncryptedLibSQLConnection] = None,
        message_bus: Optional[Any] = None
    ):
        self.db = db
        self.message_bus = message_bus
    
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
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            if not topic or not message:
                raise ValueError("Topic and message are required")
            
            # Create conversation initiation record
            initiation_id = str(uuid.uuid4())
            conversation_id = f"{user_id}_{int(datetime.now(UTC).timestamp())}"
            now = datetime.now(UTC).isoformat()
            
            # Store initiation in database
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
                    reason or "proactive_dialogue",
                    message,
                    json.dumps({"topic": topic, "emotional_context": emotional_context}),
                    "low",  # Conversations are typically low urgency
                    "dialogue",
                    now,
                    "pending",
                )
            )
            self.db.commit()
            
            # Publish to conversation initiation topic
            message_published = False
            
            if self.message_bus and self.message_bus.running:
                try:
                    # Use provided message bus client (already connected in backend)
                    # Create protobuf message for message bus
                    from aico.proto.aico_conversation_pb2 import ConversationMessage, Message
                    from google.protobuf.timestamp_pb2 import Timestamp
                    
                    proto_timestamp = Timestamp()
                    proto_timestamp.FromDatetime(datetime.now(UTC))
                    
                    conv_message = ConversationMessage(
                        timestamp=proto_timestamp,
                        source="agency_skill",
                        message_id=initiation_id,
                        user_id=user_id
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
                        'initiated_at': now,
                    })
                    
                    # Publish using async message bus
                    await self.message_bus.publish(
                        topic='conversation/aico/initiate/v1',
                        payload=conv_message
                    )
                    
                    message_published = True
                    logger.info(f"💭 [INITIATE_CONVERSATION] Published to message bus: {initiation_id[:8]}...")
                    
                except Exception as e:
                    logger.warning(f"💭 [INITIATE_CONVERSATION] Failed to publish to message bus: {e}")
                    logger.debug(f"💭 [INITIATE_CONVERSATION] Message bus error details:", exc_info=True)
            else:
                logger.info(
                    f"💭 [INITIATE_CONVERSATION] Message bus not available or not connected - "
                    f"initiation stored in database only (will be polled by frontend)"
                )
            
            result = {
                "initiation_id": initiation_id,
                "conversation_id": conversation_id,
                "topic": topic,
                "message": message,
                "reason": reason,
                "emotional_context": emotional_context,
                "status": "pending",
                "initiated_at": now,
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
            logger.error(
                f"💭 [INITIATE_CONVERSATION] Failed to initiate conversation: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Failed to initiate conversation: {str(e)}",
            )
