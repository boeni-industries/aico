"""
Base Skills - Full Implementation

Core skills for agency operations with real database integration.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

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


class SearchMemorySkill(Skill):
    """
    Search semantic memory for relevant information.
    
    Used for: Knowledge retrieval, context building
    """
    
    def __init__(self, db: Optional[EncryptedLibSQLConnection] = None):
        self.db = db
    
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
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            memories = []
            
            # Search semantic memory (facts stored in database)
            if "semantic" in memory_types:
                # Search in semantic_memory table if it exists
                try:
                    semantic_results = self.db.execute(
                        """SELECT content, metadata, created_at
                           FROM semantic_memory
                           WHERE user_id = ?
                           ORDER BY created_at DESC
                           LIMIT ?""",
                        (user_id, limit)
                    ).fetchall()
                    
                    for result in semantic_results:
                        memories.append({
                            "type": "semantic",
                            "content": result["content"],
                            "metadata": json.loads(result["metadata"]) if result["metadata"] else {},
                            "timestamp": result["created_at"],
                            "relevance": 0.85,  # Placeholder relevance score
                        })
                except Exception as e:
                    logger.debug(f"🧠 [SEARCH_MEMORY] Semantic memory table not available: {e}")
            
            # Search episodic memory (conversation history)
            if "episodic" in memory_types or not memories:
                # Search recent conversations for relevant content
                conversations = self.db.execute(
                    """SELECT c.conversation_id, c.created_at, cm.content
                       FROM conversations c
                       JOIN conversation_messages cm ON c.conversation_id = cm.conversation_id
                       WHERE c.user_id = ? AND cm.role = 'user'
                       ORDER BY c.created_at DESC
                       LIMIT ?""",
                    (user_id, limit * 2)
                ).fetchall()
                
                # Simple keyword matching for relevance
                query_lower = query.lower()
                for conv in conversations:
                    content = conv["content"]
                    if query_lower in content.lower():
                        memories.append({
                            "type": "episodic",
                            "content": content[:200],  # Truncate long content
                            "conversation_id": conv["conversation_id"],
                            "timestamp": conv["created_at"],
                            "relevance": 0.75,
                        })
                        if len(memories) >= limit:
                            break
            
            # Sort by relevance and limit
            memories.sort(key=lambda x: x["relevance"], reverse=True)
            memories = memories[:limit]
            
            result = {
                "query": query,
                "results_found": len(memories),
                "memories": memories,
                "searched_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"🧠 [SEARCH_MEMORY] Found {len(memories)} relevant memories"
            )
            
            return SkillResult(
                success=True,
                output=result,
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
    
    def __init__(self, db: Optional[EncryptedLibSQLConnection] = None):
        self.db = db
    
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
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            now = datetime.utcnow().isoformat()
            entities_added = 0
            relationships_added = 0
            
            # Store entities in knowledge_entities table
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get("type", "unknown")
                    entity_value = entity.get("value", "")
                    entity_metadata = entity.get("metadata", {})
                else:
                    entity_type = "unknown"
                    entity_value = str(entity)
                    entity_metadata = {}
                
                try:
                    self.db.execute(
                        """INSERT OR REPLACE INTO knowledge_entities 
                           (user_id, entity_type, entity_value, metadata, source, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            user_id,
                            entity_type,
                            entity_value,
                            json.dumps(entity_metadata),
                            source,
                            now,
                            now,
                        )
                    )
                    entities_added += 1
                except Exception as e:
                    logger.warning(f"📊 [UPDATE_KNOWLEDGE_GRAPH] Failed to add entity: {e}")
            
            # Store relationships in knowledge_relationships table
            for rel in relationships:
                if isinstance(rel, dict):
                    from_entity = rel.get("from", "")
                    to_entity = rel.get("to", "")
                    rel_type = rel.get("type", "related_to")
                    rel_metadata = rel.get("metadata", {})
                    
                    try:
                        self.db.execute(
                            """INSERT OR REPLACE INTO knowledge_relationships
                               (user_id, from_entity, to_entity, relationship_type, metadata, source, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                user_id,
                                from_entity,
                                to_entity,
                                rel_type,
                                json.dumps(rel_metadata),
                                source,
                                now,
                            )
                        )
                        relationships_added += 1
                    except Exception as e:
                        logger.warning(f"📊 [UPDATE_KNOWLEDGE_GRAPH] Failed to add relationship: {e}")
            
            self.db.commit()
            
            result = {
                "entities_added": entities_added,
                "relationships_added": relationships_added,
                "source": source,
                "entities": entities,
                "relationships": relationships,
                "updated_at": now,
            }
            
            logger.info(
                f"📊 [UPDATE_KNOWLEDGE_GRAPH] Updated: "
                f"{entities_added} entities, "
                f"{relationships_added} relationships"
            )
            
            return SkillResult(
                success=True,
                output=result,
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
    
    def __init__(self, db: Optional[EncryptedLibSQLConnection] = None):
        self.db = db
    
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
            if not self.db:
                raise RuntimeError("Database connection not available")
            
            # Get goal details
            goal = self.db.execute(
                """SELECT goal_id, title, description, status, priority, origin, created_at
                   FROM agency_goals
                   WHERE goal_id = ? AND user_id = ?""",
                (goal_id, user_id)
            ).fetchone()
            
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")
            
            logger.info(f"🤔 [REFLECT_ON_GOAL] Analyzing goal: {goal['title']}")
            
            # Get plans for this goal
            plans = self.db.execute(
                """SELECT plan_id, status, created_at
                   FROM agency_plans
                   WHERE goal_id = ?
                   ORDER BY created_at DESC""",
                (goal_id,)
            ).fetchall()
            
            # Get executions if history is requested
            executions = []
            if include_history and plans:
                for plan in plans:
                    execs = self.db.execute(
                        """SELECT execution_id, status, steps_completed, steps_total, 
                                  started_at, completed_at, error_message
                           FROM plan_executions
                           WHERE plan_id = ?
                           ORDER BY created_at DESC
                           LIMIT 5""",
                        (plan["plan_id"],)
                    ).fetchall()
                    executions.extend(execs)
            
            # Analyze progress
            blockers = []
            insights = []
            recommendations = []
            
            # Check goal status
            if goal["status"] == "pending":
                insights.append("Goal is pending - no active work yet")
                recommendations.append("Consider activating this goal if it's a priority")
            elif goal["status"] == "active":
                insights.append("Goal is actively being worked on")
            elif goal["status"] == "paused":
                blockers.append("Goal is currently paused")
                recommendations.append("Review why goal was paused and consider resuming")
            
            # Analyze plans
            if not plans:
                blockers.append("No plans created for this goal yet")
                recommendations.append("Create a plan to start making progress")
            else:
                draft_plans = [p for p in plans if p["status"] == "draft"]
                active_plans = [p for p in plans if p["status"] == "active"]
                
                if draft_plans:
                    insights.append(f"{len(draft_plans)} draft plan(s) available")
                if active_plans:
                    insights.append(f"{len(active_plans)} active plan(s) in progress")
            
            # Analyze executions
            if executions:
                completed = [e for e in executions if e["status"] == "completed"]
                failed = [e for e in executions if e["status"] == "failed"]
                running = [e for e in executions if e["status"] == "running"]
                
                if completed:
                    insights.append(f"{len(completed)} execution(s) completed successfully")
                if failed:
                    blockers.append(f"{len(failed)} execution(s) failed")
                    # Extract error messages
                    for exec in failed[:3]:  # Show up to 3 errors
                        if exec["error_message"]:
                            blockers.append(f"Error: {exec['error_message'][:100]}")
                if running:
                    insights.append(f"{len(running)} execution(s) currently running")
                
                # Calculate progress
                total_steps = sum(e["steps_total"] or 0 for e in executions)
                completed_steps = sum(e["steps_completed"] or 0 for e in executions)
                if total_steps > 0:
                    progress_pct = (completed_steps / total_steps) * 100
                    insights.append(f"Overall progress: {progress_pct:.1f}% ({completed_steps}/{total_steps} steps)")
            
            # Generate recommendations
            if not blockers:
                recommendations.append("Continue current approach - no major blockers identified")
            else:
                recommendations.append("Address identified blockers to improve progress")
            
            if failed:
                recommendations.append("Review failed executions and adjust plan if needed")
            
            # Check goal age
            created_at = datetime.fromisoformat(goal["created_at"])
            age_days = (datetime.utcnow() - created_at).days
            if age_days > 30 and goal["status"] == "pending":
                insights.append(f"Goal has been pending for {age_days} days")
                recommendations.append("Consider prioritizing or retiring this goal")
            
            reflection = {
                "goal_id": goal_id,
                "goal_title": goal["title"],
                "goal_status": goal["status"],
                "progress_assessment": "Making progress" if executions else "Not started",
                "blockers": blockers,
                "insights": insights,
                "recommendations": recommendations,
                "plans_count": len(plans),
                "executions_analyzed": len(executions),
                "reflected_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"🤔 [REFLECT_ON_GOAL] Reflection complete: "
                f"{len(blockers)} blockers, "
                f"{len(insights)} insights, "
                f"{len(recommendations)} recommendations"
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
