"""
Conversation Analysis Skill

Analyzes recent conversations to extract insights, patterns, and topics.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.analysis.conversation")


class AnalyzeConversationSkill(Skill):
    """
    Analyze recent conversations to extract insights, patterns, and topics.
    
    Used for: User Understanding, Pattern Analysis goals
    """
    
    def __init__(self, db: Optional[EncryptedLibSQLConnection] = None):
        self.db = db
    
    @property
    def skill_id(self) -> str:
        return "analyze_conversation"
    
    @property
    def name(self) -> str:
        return "Analyze Conversation"
    
    @property
    def description(self) -> str:
        return "Analyze recent conversations to extract insights, patterns, and user preferences"
    
    @property
    def category(self) -> str:
        return "analysis"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="conversation_limit",
                type=SkillParameterType.INTEGER,
                description="Number of recent conversations to analyze",
                required=False,
                default=10,
            ),
            SkillParameter(
                name="focus_areas",
                type=SkillParameterType.ARRAY,
                description="Specific areas to focus on (e.g., 'preferences', 'patterns', 'topics')",
                required=False,
                default=["preferences", "patterns"],
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute conversation analysis."""
        conversation_limit = input_data.get("conversation_limit", 10)
        focus_areas = input_data.get("focus_areas", ["preferences", "patterns"])
        
        logger.info(
            f"💬 [ANALYZE_CONVERSATION] Analyzing last {conversation_limit} conversations "
            f"for user {user_id[:8]}... (focus: {', '.join(focus_areas)})"
        )
        
        try:
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            # Query recent conversations
            conversations = self.db.execute(
                """SELECT conversation_id, created_at, message_count
                   FROM conversations
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (user_id, conversation_limit)
            ).fetchall()
            
            if not conversations:
                logger.warning(f"💬 [ANALYZE_CONVERSATION] No conversations found for user {user_id[:8]}...")
                return SkillResult(
                    success=True,
                    output={
                        "conversation_count": 0,
                        "insights": [],
                        "patterns": [],
                        "topics": [],
                        "note": "No conversations found for analysis",
                    },
                )
            
            logger.info(f"💬 [ANALYZE_CONVERSATION] Found {len(conversations)} conversations to analyze")
            
            # Analyze conversations
            insights = []
            patterns = []
            topics = set()
            total_messages = 0
            
            for conv in conversations:
                conv_id = conv["conversation_id"]
                total_messages += conv["message_count"] or 0
                
                # Get messages from conversation
                messages = self.db.execute(
                    """SELECT role, content, created_at
                       FROM conversation_messages
                       WHERE conversation_id = ?
                       ORDER BY created_at ASC""",
                    (conv_id,)
                ).fetchall()
                
                # Extract patterns from message timing
                if messages:
                    first_msg_time = datetime.fromisoformat(messages[0]["created_at"])
                    hour = first_msg_time.hour
                    
                    if hour >= 6 and hour < 12:
                        patterns.append("Morning activity")
                    elif hour >= 12 and hour < 18:
                        patterns.append("Afternoon activity")
                    elif hour >= 18 and hour < 24:
                        patterns.append("Evening activity")
                    else:
                        patterns.append("Night activity")
                
                # Analyze message content for insights
                user_messages = [m for m in messages if m["role"] == "user"]
                for msg in user_messages:
                    content = msg["content"].lower()
                    
                    # Detect preferences
                    if "prefer" in content or "like" in content:
                        insights.append("User expressed preference in conversation")
                    
                    # Detect question patterns
                    if "?" in content or "how" in content or "what" in content or "why" in content:
                        insights.append("User asks clarifying questions")
                    
                    # Extract potential topics (simple keyword extraction)
                    keywords = ["agency", "plan", "execution", "skill", "goal", "memory", "conversation"]
                    for keyword in keywords:
                        if keyword in content:
                            topics.add(keyword)
            
            # Deduplicate patterns
            patterns = list(set(patterns))
            
            # Generate summary insights
            if total_messages > 0:
                avg_messages = total_messages / len(conversations)
                if avg_messages > 10:
                    insights.append("User engages in detailed conversations")
                elif avg_messages > 5:
                    insights.append("User has moderate conversation depth")
                else:
                    insights.append("User prefers brief interactions")
            
            # Deduplicate insights
            insights = list(set(insights))[:10]  # Limit to top 10
            
            result = {
                "conversation_count": len(conversations),
                "total_messages_analyzed": total_messages,
                "focus_areas_analyzed": focus_areas,
                "insights": insights,
                "patterns": patterns,
                "topics": list(topics),
                "analyzed_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"💬 [ANALYZE_CONVERSATION] Analysis complete: "
                f"{len(insights)} insights, "
                f"{len(patterns)} patterns, "
                f"{len(topics)} topics from {total_messages} messages"
            )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.utcnow().isoformat(),
                    "conversations_analyzed": len(conversations),
                },
            )
            
        except Exception as e:
            logger.error(
                f"💬 [ANALYZE_CONVERSATION] Analysis failed: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Conversation analysis failed: {str(e)}",
            )
