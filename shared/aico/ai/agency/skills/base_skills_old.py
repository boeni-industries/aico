"""
Base Skills

Core skills for agency operations: memory, analysis, reflection, knowledge management.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List
from datetime import datetime

from .registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.base_skills")


class AnalyzeConversationSkill(Skill):
    """
    Analyze recent conversations to extract insights, patterns, and topics.
    
    Used for: User Understanding, Pattern Analysis goals
    """
    
    def __init__(self, db: EncryptedLibSQLConnection = None):
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
                        insights.append(f"User expressed preference in conversation")
                    
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


class SearchMemorySkill(Skill):
    """
    Search semantic memory for relevant information.
    
    Used for: Knowledge retrieval, context building
    """
    
    @property
    def skill_id(self) -> str:
        return "search_memory"
    
    @property
    def name(self) -> str:
        return "Search Memory"
    
    @property
    def description(self) -> str:
        return "Search semantic memory for relevant facts, conversations, and knowledge"
    
    @property
    def category(self) -> str:
        return "memory"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type=SkillParameterType.STRING,
                description="Search query",
                required=True,
            ),
            SkillParameter(
                name="limit",
                type=SkillParameterType.INTEGER,
                description="Maximum number of results",
                required=False,
                default=5,
            ),
            SkillParameter(
                name="memory_types",
                type=SkillParameterType.ARRAY,
                description="Types of memory to search (e.g., 'semantic', 'episodic')",
                required=False,
                default=["semantic"],
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute memory search."""
        query = input_data.get("query")
        limit = input_data.get("limit", 5)
        memory_types = input_data.get("memory_types", ["semantic"])
        
        logger.info(
            f"🧠 [SEARCH_MEMORY] Searching memory for user {user_id[:8]}... "
            f"query='{query}' limit={limit} types={memory_types}"
        )
        
        try:
            # TODO: Implement actual memory search
            # This would:
            # 1. Query semantic memory (ChromaDB)
            # 2. Query episodic memory (conversation history)
            # 3. Rank and filter results
            # 4. Return relevant memories
            
            # Placeholder implementation
            results = {
                "query": query,
                "results_found": 3,
                "memories": [
                    {
                        "type": "semantic",
                        "content": "User is implementing agency plan execution system",
                        "relevance": 0.95,
                        "timestamp": "2025-12-13T21:45:00Z",
                    },
                    {
                        "type": "semantic",
                        "content": "User prefers comprehensive logging for debugging",
                        "relevance": 0.87,
                        "timestamp": "2025-12-13T21:30:00Z",
                    },
                    {
                        "type": "semantic",
                        "content": "User is working on skill invocation system",
                        "relevance": 0.82,
                        "timestamp": "2025-12-13T22:45:00Z",
                    },
                ],
                "searched_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"🧠 [SEARCH_MEMORY] Found {results['results_found']} relevant memories "
                f"(avg relevance: {sum(m['relevance'] for m in results['memories']) / len(results['memories']):.2f})"
            )
            
            return SkillResult(
                success=True,
                output=results,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.utcnow().isoformat(),
                },
            )
            
        except Exception as e:
            logger.error(
                f"🧠 [SEARCH_MEMORY] Search failed: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Memory search failed: {str(e)}",
            )


class UpdateKnowledgeGraphSkill(Skill):
    """
    Update knowledge graph with new facts and relationships.
    
    Used for: Knowledge Graph Curation goals
    """
    
    @property
    def skill_id(self) -> str:
        return "update_knowledge_graph"
    
    @property
    def name(self) -> str:
        return "Update Knowledge Graph"
    
    @property
    def description(self) -> str:
        return "Add or update facts and relationships in the knowledge graph"
    
    @property
    def category(self) -> str:
        return "knowledge"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="entities",
                type=SkillParameterType.ARRAY,
                description="Entities to add/update",
                required=True,
            ),
            SkillParameter(
                name="relationships",
                type=SkillParameterType.ARRAY,
                description="Relationships between entities",
                required=False,
                default=[],
            ),
            SkillParameter(
                name="source",
                type=SkillParameterType.STRING,
                description="Source of the information",
                required=False,
                default="conversation",
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute knowledge graph update."""
        entities = input_data.get("entities", [])
        relationships = input_data.get("relationships", [])
        source = input_data.get("source", "conversation")
        
        logger.info(
            f"📊 [UPDATE_KNOWLEDGE_GRAPH] Updating knowledge graph for user {user_id[:8]}... "
            f"entities={len(entities)} relationships={len(relationships)} source={source}"
        )
        
        try:
            # TODO: Implement actual knowledge graph update
            # This would:
            # 1. Validate entities and relationships
            # 2. Update knowledge graph database
            # 3. Create/update entity nodes
            # 4. Create/update relationship edges
            # 5. Update timestamps and metadata
            
            # Placeholder implementation
            updated = {
                "entities_added": len(entities),
                "relationships_added": len(relationships),
                "source": source,
                "entities": entities,
                "relationships": relationships,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"📊 [UPDATE_KNOWLEDGE_GRAPH] Updated: "
                f"{updated['entities_added']} entities, "
                f"{updated['relationships_added']} relationships"
            )
            
            return SkillResult(
                success=True,
                output=updated,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.utcnow().isoformat(),
                },
            )
            
        except Exception as e:
            logger.error(
                f"📊 [UPDATE_KNOWLEDGE_GRAPH] Update failed: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Knowledge graph update failed: {str(e)}",
            )


class ReflectOnGoalSkill(Skill):
    """
    Reflect on goal progress and generate insights.
    
    Used for: Deep Dive Learning, Skill Building goals
    """
    
    @property
    def skill_id(self) -> str:
        return "reflect_on_goal"
    
    @property
    def name(self) -> str:
        return "Reflect on Goal"
    
    @property
    def description(self) -> str:
        return "Analyze goal progress, identify blockers, and generate improvement insights"
    
    @property
    def category(self) -> str:
        return "reflection"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="goal_id",
                type=SkillParameterType.STRING,
                description="Goal to reflect on",
                required=True,
            ),
            SkillParameter(
                name="include_history",
                type=SkillParameterType.BOOLEAN,
                description="Include historical execution data",
                required=False,
                default=True,
            ),
        ]
    
    async def execute(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SkillResult:
        """Execute goal reflection."""
        goal_id = input_data.get("goal_id")
        include_history = input_data.get("include_history", True)
        
        logger.info(
            f"🤔 [REFLECT_ON_GOAL] Reflecting on goal {goal_id[:8]}... "
            f"for user {user_id[:8]}... (include_history={include_history})"
        )
        
        try:
            # TODO: Implement actual goal reflection
            # This would:
            # 1. Query goal status and history
            # 2. Analyze execution patterns
            # 3. Identify blockers and challenges
            # 4. Generate improvement suggestions
            # 5. Update goal metadata
            
            # Placeholder implementation
            reflection = {
                "goal_id": goal_id,
                "progress_assessment": "Making steady progress",
                "blockers": [
                    "Waiting for skill implementation completion",
                    "Need more test data for validation",
                ],
                "insights": [
                    "Plan execution is working well",
                    "Logging provides good visibility",
                    "Need to implement actual skill logic",
                ],
                "recommendations": [
                    "Complete skill implementation",
                    "Add integration tests",
                    "Monitor execution performance",
                ],
                "reflected_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"🤔 [REFLECT_ON_GOAL] Reflection complete: "
                f"{len(reflection['blockers'])} blockers, "
                f"{len(reflection['insights'])} insights, "
                f"{len(reflection['recommendations'])} recommendations"
            )
            
            return SkillResult(
                success=True,
                output=reflection,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.utcnow().isoformat(),
                },
            )
            
        except Exception as e:
            logger.error(
                f"🤔 [REFLECT_ON_GOAL] Reflection failed: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Goal reflection failed: {str(e)}",
            )
