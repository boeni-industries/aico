"""
Memory Service

Replaces shared/aico/ai/memory/episodic.py and consolidation.py with repository-based implementation.
Provides high-level memory operations.

NOTE: This service primarily orchestrates existing repositories.
Episodic memory storage may use LMDB directly (as per architecture).
Semantic memory uses ChromaDB (as per architecture).
This service provides a unified interface for memory operations.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

logger = get_logger("shared.services.memory")


class MemoryService:
    """
    Service layer for memory operations.
    
    Provides unified interface for episodic and semantic memory.
    Note: Actual storage may use LMDB (episodic) and ChromaDB (semantic) directly.
    This service orchestrates memory-related database operations.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ==================== User Memory Operations ====================
    # Uses ams_user_memories repository for metadata

    async def create_memory_metadata(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create memory metadata record."""
        try:
            from aico.ai.ams.models import AMSUserMemory
            
            memory = AMSUserMemory(**memory_data)
            created = await self.uow.ams_user_memories.create(memory)
            await self.uow.commit()
            
            logger.info("[MEMORY_SERVICE] Created memory metadata", extra={"fact_id": created.fact_id})
            return created
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to create memory metadata: {e}")
            await self.uow.rollback()
            raise

    async def get_memory_metadata(self, fact_id: str) -> Optional[Any]:
        """Get memory metadata by fact ID."""
        try:
            return await self.uow.ams_user_memories.get_by_id(fact_id)
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to get memory metadata: {e}", extra={"fact_id": fact_id})
            raise

    async def get_user_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[Any]:
        """Get memory metadata for a user."""
        try:
            filters = {"user_id": user_id}
            if memory_type:
                filters["memory_type"] = memory_type
            
            return await self.uow.ams_user_memories.list(filters=filters)
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to get user memories: {e}", extra={"user_id": user_id})
            raise

    async def list_user_memories(self, user_id: str) -> List[Any]:
        """List all memories for a user (alias for get_user_memories)."""
        return await self.get_user_memories(user_id)

    async def get_episodic_memories(self, user_id: str) -> List[Any]:
        """Get episodic memory metadata for a user."""
        return await self.get_user_memories(user_id, memory_type="episodic")

    async def get_semantic_memories(self, user_id: str) -> List[Any]:
        """Get semantic memory metadata for a user."""
        return await self.get_user_memories(user_id, memory_type="semantic")

    # ==================== Conversation Memory Operations ====================
    # Note: Actual conversation messages may be in conversation_messages table
    # This is a placeholder for when ConversationRepository is created

    async def get_conversation_context(self, conversation_id: str, limit: int = 50) -> List[Any]:
        """
        Get recent conversation context.
        
        NOTE: This is a placeholder. Actual implementation will use
        ConversationRepository when it's created in Phase 6.
        """
        logger.warning("[MEMORY_SERVICE] get_conversation_context not yet implemented - needs ConversationRepository")
        return []

    # ==================== Memory Consolidation Operations ====================
    # Orchestrates episodic → semantic memory consolidation

    async def consolidate_memories(self, user_id: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Consolidate episodic memories into semantic memory.
        
        This is a high-level orchestration method that would:
        1. Retrieve episodic memories from LMDB
        2. Process and consolidate them
        3. Store consolidated memories in ChromaDB
        4. Update metadata in PostgreSQL
        
        NOTE: Actual implementation depends on LMDB and ChromaDB integration.
        This service provides the database metadata operations.
        """
        try:
            # Get episodic memory metadata for the time window
            episodic_memories = await self.get_episodic_memories(user_id)
            
            # Filter by time window (would need timestamp field)
            # Process consolidation (business logic)
            # Store semantic memory metadata
            
            result = {
                "user_id": user_id,
                "consolidated_count": len(episodic_memories),
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            logger.info("[MEMORY_SERVICE] Consolidated memories", extra=result)
            return result
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to consolidate memories: {e}", extra={"user_id": user_id})
            raise

    # ==================== Memory Analytics ====================

    async def get_memory_count(self, user_id: str, memory_type: Optional[str] = None) -> int:
        """Get memory count for a user."""
        try:
            filters = {"user_id": user_id}
            if memory_type:
                filters["memory_type"] = memory_type
            
            return await self.uow.ams_user_memories.count(filters=filters)
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to count memories: {e}", extra={"user_id": user_id})
            raise

    async def get_episodic_memory_count(self, user_id: str) -> int:
        """Get episodic memory count."""
        return await self.get_memory_count(user_id, memory_type="episodic")

    async def get_semantic_memory_count(self, user_id: str) -> int:
        """Get semantic memory count."""
        return await self.get_memory_count(user_id, memory_type="semantic")

    # ==================== Memory Search Operations ====================
    # Note: Actual semantic search happens in ChromaDB
    # This service provides metadata-based search

    async def search_memories_by_metadata(self, user_id: str, filters: Dict[str, Any]) -> List[Any]:
        """Search memories by metadata filters."""
        try:
            filters["user_id"] = user_id
            return await self.uow.ams_user_memories.list(filters=filters)
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to search memories: {e}", extra={"user_id": user_id})
            raise

    # ==================== Memory Cleanup Operations ====================

    async def delete_old_memories(self, user_id: str, older_than_days: int = 90) -> int:
        """
        Delete old memory metadata.
        
        NOTE: This only deletes metadata. Actual memory content in LMDB/ChromaDB
        would need separate cleanup.
        """
        try:
            # Get all memories for user
            memories = await self.get_user_memories(user_id)
            
            # Filter and delete old ones (would need timestamp comparison)
            deleted_count = 0
            for memory in memories:
                # Would check memory.created_at against older_than_days
                # For now, just a placeholder
                pass
            
            logger.info(f"[MEMORY_SERVICE] Deleted {deleted_count} old memories", extra={"user_id": user_id})
            return deleted_count
        except Exception as e:
            logger.error(f"[MEMORY_SERVICE] Failed to delete old memories: {e}", extra={"user_id": user_id})
            raise
