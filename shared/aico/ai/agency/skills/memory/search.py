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
from aico.ai.memory.manager import MemoryManager, MemoryQuery


logger = get_logger("shared.ai.agency.skills.memory.search")


class SearchMemorySkill(Skill):
    """
    Search semantic memory for relevant information.
    
    Used for: Knowledge retrieval, context building
    """
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory_manager = memory_manager
    
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
            if not self.memory_manager:
                raise RuntimeError("Memory manager not available")

            # Build memory query for semantic search via MemoryManager
            query_obj = MemoryQuery(
                query_text=query,
                query_type="semantic",
                max_results=limit,
                user_id=user_id,
            )

            # Use MemoryManager to perform unified search
            memory_result = await self.memory_manager.query_memory(query_obj)

            # Normalize result shape to previous expectations
            memories: List[Dict[str, Any]] = []
            for mem, score in zip(memory_result.memories, memory_result.relevance_scores):
                base = {
                    "type": mem.get("type", "semantic"),
                    "content": mem.get("content", ""),
                    "timestamp": mem.get("timestamp"),
                    "relevance": score,
                }
                # Preserve useful fields if present
                if "fact_type" in mem:
                    base["fact_type"] = mem["fact_type"]
                if "category" in mem:
                    base["category"] = mem["category"]
                if "confidence" in mem:
                    base["confidence"] = mem["confidence"]
                if "conversation_id" in mem:
                    base["conversation_id"] = mem["conversation_id"]

                # Filter by requested memory_types if provided
                if base["type"] in memory_types:
                    memories.append(base)

            # Sort by relevance descending and trim to limit
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
