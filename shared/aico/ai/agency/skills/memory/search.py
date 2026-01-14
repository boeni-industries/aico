"""
Memory Search Skill

Searches semantic and episodic memory for relevant information.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from ..registry import (
    Skill,
    SkillParameter,
    SkillParameterType,
    SkillResult,
)
from aico.core.logging import get_logger


logger = get_logger("shared.ai.agency.skills.memory.search")


class SearchMemorySkill(Skill):
    """
    Search semantic memory for relevant information.
    
    Used for: Knowledge retrieval, context building
    """
    
    def __init__(self, db: Optional[Any  # Skills being redesigned] = None):
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
            
            # Search semantic memory (facts stored in user_memories table)
            if "semantic" in memory_types:
                try:
                    # Search user_memories table for relevant facts
                    query_lower = query.lower()
                    semantic_results = self.db.execute(
                        """SELECT fact_id, fact_type, content, category, confidence, 
                                  source_conversation_id, created_at
                           FROM ams_user_memories
                           WHERE user_id = ?
                           ORDER BY created_at DESC
                           LIMIT ?""",
                        (user_id, limit * 2)
                    ).fetchall()
                    
                    # Filter by query relevance
                    for result in semantic_results:
                        content = result["content"] or ""
                        if query_lower in content.lower():
                            memories.append({
                                "type": "semantic",
                                "content": content,
                                "fact_type": result["fact_type"],
                                "category": result["category"],
                                "confidence": result["confidence"],
                                "timestamp": result["created_at"],
                                "relevance": 0.85,
                            })
                            if len(memories) >= limit:
                                break
                except Exception as e:
                    logger.debug(f"🧠 [SEARCH_MEMORY] User memories search failed: {e}")
            
            # Search episodic memory (AICO-initiated conversations)
            if "episodic" in memory_types and len(memories) < limit:
                try:
                    # Search AICO conversation initiations for relevant content
                    query_lower = query.lower()
                    conversations = self.db.execute(
                        """SELECT initiation_id, conversation_id, question, context, 
                                  initiated_at, resolution_status
                           FROM conversation_initiations
                           WHERE user_id = ?
                           ORDER BY initiated_at DESC
                           LIMIT ?""",
                        (user_id, limit * 2)
                    ).fetchall()
                    
                    # Simple keyword matching for relevance
                    for conv in conversations:
                        question = conv["question"] or ""
                        context = conv["context"] or ""
                        combined = f"{question} {context}"
                        if query_lower in combined.lower():
                            memories.append({
                                "type": "episodic",
                                "content": question[:200],
                                "conversation_id": conv["conversation_id"],
                                "timestamp": conv["initiated_at"],
                                "relevance": 0.75,
                            })
                            if len(memories) >= limit:
                                break
                except Exception as e:
                    logger.debug(f"🧠 [SEARCH_MEMORY] Episodic memory search failed: {e}")
            
            # Sort by relevance and limit
            memories.sort(key=lambda x: x["relevance"], reverse=True)
            memories = memories[:limit]
            
            result = {
                "query": query,
                "results_found": len(memories),
                "memories": memories,
                "searched_at": datetime.now(UTC).isoformat(),
            }
            
            logger.info(
                f"🧠 [SEARCH_MEMORY] Found {len(memories)} relevant memories"
            )
            
            return SkillResult(
                success=True,
                output=result,
                metadata={
                    "skill_id": self.skill_id,
                    "execution_time": datetime.now(UTC).isoformat(),
                },
            )
            
        except Exception as e:
            logger.exception(
                f"🧠 [SEARCH_MEMORY] Search failed: {e}"
            )
            return SkillResult(
                success=False,
                error=f"Memory search failed: {str(e)}",
            )
