"""
LMDB Working Memory Cleanup Task

Periodically removes expired entries from LMDB working memory to prevent
unbounded growth of stale data.
"""

from datetime import datetime
from typing import Dict, Any

from backend.scheduler.tasks.base import BaseTask, TaskContext, TaskResult
from aico.core.logging import get_logger

logger = get_logger("backend", "scheduler.tasks.lmdb_cleanup")


class LMDBCleanupTask(BaseTask):
    """
    Scheduled task to cleanup expired LMDB working memory entries.
    
    Runs daily to remove entries that have exceeded their TTL,
    preventing unbounded growth of stale data.
    """
    
    task_id = "system.lmdb_cleanup"
    description = "Clean up expired entries from LMDB working memory"
    
    default_config = {
        "enabled": True,
        "schedule": "30 4 * * *",  # 4:30 AM daily (staggered after Thompson Sampling)
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute LMDB cleanup task.
        
        Args:
            context: Task execution context
            
        Returns:
            TaskResult with cleanup statistics
        """
        try:
            logger.info("🧹 [LMDB_CLEANUP] Starting LMDB cleanup task")
            print("🧹 [LMDB_CLEANUP] Starting LMDB cleanup task")
            
            # Get memory manager from context
            memory_manager = await self._get_memory_manager(context)
            
            if not memory_manager:
                logger.error("🧹 [LMDB_CLEANUP] Memory manager not available")
                return TaskResult(
                    success=False,
                    message="Memory manager not available",
                    error="MemoryManager not initialized"
                )
            
            # Get working store
            working_store = memory_manager._working_store
            if not working_store:
                logger.error("🧹 [LMDB_CLEANUP] Working memory store not available")
                return TaskResult(
                    success=False,
                    message="Working memory store not available",
                    error="WorkingMemoryStore not initialized"
                )
            
            # Run cleanup
            logger.info("🧹 [LMDB_CLEANUP] Running cleanup_expired()")
            deleted_count = await working_store.cleanup_expired()
            
            logger.info(f"🧹 [LMDB_CLEANUP] ✅ Cleanup complete: {deleted_count} entries deleted")
            print(f"🧹 [LMDB_CLEANUP] ✅ Cleanup complete: {deleted_count} entries deleted")
            
            return TaskResult(
                success=True,
                message=f"Cleaned up {deleted_count} expired entries",
                data={
                    "deleted_count": deleted_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            error_msg = f"LMDB cleanup failed: {str(e)}"
            logger.error(f"🧹 [LMDB_CLEANUP] ❌ {error_msg}")
            print(f"🧹 [LMDB_CLEANUP] ❌ {error_msg}")
            
            return TaskResult(
                success=False,
                message="LMDB cleanup failed",
                error=error_msg
            )
    
    async def _get_memory_manager(self, context: TaskContext):
        """Get memory manager from service container."""
        try:
            from backend.services import get_memory_manager
            
            # Get memory manager (will initialize if needed)
            memory_manager = get_memory_manager(
                context.config,
                context.db_connection
            )
            
            # Ensure it's initialized
            if not memory_manager._initialized:
                await memory_manager.initialize()
            
            return memory_manager
            
        except Exception as e:
            logger.error(f"Failed to get memory manager: {e}")
            return None
