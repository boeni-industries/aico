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
        db: Optional[Any] = None,  # Skills being redesigned
        message_bus: Optional[Any] = None
    ):
        self.db = db
        self.message_bus = message_bus
    
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
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            if not question:
                raise ValueError("Question is required")
            
            # Check for duplicate question in last 24 hours
            duplicate = self.db.execute(
                """SELECT COUNT(*) as count
                   FROM conversation_initiations
                   WHERE user_id = ?
                   AND question = ?
                   AND trigger_reason = 'information_gap'
                   AND datetime(initiated_at) > datetime('now', '-24 hours')""",
                (user_id, question)
            ).fetchone()
            
            if duplicate and duplicate['count'] > 0:
                logger.debug(
                    f"💬 [ASK_USER] Duplicate question detected for user {user_id[:8]}, "
                    f"skipping creation"
                )
                return SkillResult(
                    success=True,
                    output={
                        "status": "skipped",
                        "reason": "duplicate_question",
                        "message": "Question already asked recently"
                    },
                    metadata={"skill_id": self.skill_id}
                )
            
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
                    "information_gap",
                    question,
                    question_context,
                    urgency,
                    expected_answer_type,
                    now,
                    "pending",
                )
            )
            self.db.commit()
            
            # Publish to conversation initiation topic
            # This will be picked up by ConversationEngine
            try:
                from aico.core.bus import MessageBusClient
                from aico.proto.aico_conversation_pb2 import ConversationMessage, Message
                from google.protobuf.timestamp_pb2 import Timestamp
                
                # Create message bus client (if available)
                bus_client = MessageBusClient(client_id=f"ask_user_skill_{initiation_id[:8]}")
                await bus_client.connect()
                
                # Create conversation message
                proto_timestamp = Timestamp()
                proto_timestamp.FromDatetime(datetime.now(UTC))
                
                conv_message = ConversationMessage(
                    timestamp=proto_timestamp,
                    source="agency_skill",
                    message_id=initiation_id,
                    user_id=user_id
                )
                
                # Build question with context
                full_message = question
                if question_context:
                    full_message = f"{question_context}\n\n{question}"
                
                conv_message.message.text = full_message
                conv_message.message.type = Message.MessageType.AICO_INITIATED
                conv_message.message.conversation_id = conversation_id
                conv_message.message.turn_number = 1
                
                # Publish to AICO initiation topic
                await bus_client.publish("conversation/aico/initiate/v1", conv_message)
                await bus_client.disconnect()
                
                logger.info(f"💬 [ASK_USER] Published to message bus: {initiation_id[:8]}...")
                
            except Exception as e:
                logger.warning(f"💬 [ASK_USER] Failed to publish to message bus: {e}")
                # Continue anyway - initiation is stored in DB
            
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
