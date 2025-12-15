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
from aico.data.libsql import EncryptedLibSQLConnection


logger = get_logger("shared", "ai.agency.skills.memory.search")


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
            logger.error(
                f"🧠 [SEARCH_MEMORY] Search failed: {e}",
                exc_info=True
            )
            return SkillResult(
                success=False,
                error=f"Memory search failed: {str(e)}",
            )
