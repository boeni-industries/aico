"""
KG Consolidation Task

Scheduled task for Knowledge Graph extraction from working memory.
Runs periodically during idle periods to extract entities and relationships
from unconsolidated messages.

Schedule: Every 5 minutes (configurable via cron)
Architecture: Aligns with AMS design - fast hippocampal capture, slow cortical consolidation
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from aico.core.logging import get_logger

from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend", "scheduler.tasks.kg_consolidation")


class KGConsolidationTask(BaseTask):
    """
    Scheduled task for Knowledge Graph consolidation.
    
    Extracts entities and relationships from unconsolidated working memory
    messages and stores them in the knowledge graph.
    
    Configuration:
    - Schedule: core.memory.kg_consolidation.schedule.cron
    - Batch size: core.memory.kg_consolidation.batch_size
    - Enabled: core.memory.kg_consolidation.enabled
    """
    
    task_id = "ams.kg_consolidation"
    default_config = {
        "enabled": True,
        "schedule": "*/5 * * * *",  # Every 5 minutes
        "batch_size": 50,  # Max messages to process per run
        "max_age_hours": 24  # Only process messages from last 24h
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute KG consolidation task.
        
        Returns:
            TaskResult with consolidation statistics
        """
        start_time = datetime.utcnow()
        
        try:
            print("🕸️ [KG_TASK] ========================================")
            print("🕸️ [KG_TASK] Starting KG consolidation task")
            print("🕸️ [KG_TASK] ========================================")
            logger.info("🕸️ [KG_TASK] Starting KG consolidation task")
            
            # Load configuration
            kg_config = context.config_manager.get("core.memory.kg_consolidation", {})
            enabled = context.get_config("enabled", kg_config.get("enabled", True))
            batch_size = context.get_config("batch_size", 50)
            
            # Check if KG consolidation is enabled
            if not enabled:
                print("🕸️ [KG_TASK] ⚠️  KG consolidation disabled in configuration")
                logger.info("🕸️ [KG_TASK] KG consolidation disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="KG consolidation disabled in configuration",
                    data={"enabled": False}
                )
            
            # Get memory manager from backend services
            try:
                print("🕸️ [KG_TASK] Getting memory manager from backend services...")
                from backend.services import get_memory_manager
                memory_manager = get_memory_manager(context.config_manager, context.db_connection)
                
                # Ensure memory manager is initialized
                if not memory_manager._initialized:
                    print("🕸️ [KG_TASK] Initializing memory manager...")
                    logger.info("🕸️ [KG_TASK] Initializing memory manager...")
                    await memory_manager.initialize()
                
                # Check if KG is initialized
                if not memory_manager._kg_initialized:
                    print("🕸️ [KG_TASK] ❌ Knowledge Graph not initialized")
                    logger.error("🕸️ [KG_TASK] Knowledge Graph not initialized")
                    return TaskResult(
                        success=False,
                        message="Knowledge Graph not initialized",
                        data={"kg_initialized": False}
                    )
                
                print("🕸️ [KG_TASK] ✅ Memory manager ready")
                
            except Exception as e:
                print(f"🕸️ [KG_TASK] ❌ Failed to get memory manager: {e}")
                logger.error(f"🕸️ [KG_TASK] Failed to get memory manager: {e}")
                return TaskResult(
                    success=False,
                    message="Memory manager not available",
                    data={"error": str(e)}
                )
            
            # Check modelservice health
            try:
                print("🕸️ [KG_TASK] Checking modelservice health...")
                is_healthy = await memory_manager._kg_modelservice.check_health()
                if not is_healthy:
                    print("🕸️ [KG_TASK] ❌ Modelservice not healthy")
                    logger.error("🕸️ [KG_TASK] Modelservice not healthy")
                    return TaskResult(
                        success=False,
                        message="Modelservice not healthy",
                        data={"modelservice_healthy": False}
                    )
                print("🕸️ [KG_TASK] ✅ Modelservice healthy")
            except Exception as e:
                print(f"🕸️ [KG_TASK] ❌ Failed to check modelservice health: {e}")
                logger.error(f"🕸️ [KG_TASK] Failed to check modelservice health: {e}")
                return TaskResult(
                    success=False,
                    message="Modelservice health check failed",
                    data={"error": str(e)}
                )
            
            # Get users with unconsolidated messages
            print("🕸️ [KG_TASK] Getting users with unconsolidated messages...")
            users_with_pending = await self._get_users_with_pending_messages(
                memory_manager, 
                batch_size
            )
            
            if not users_with_pending:
                print("🕸️ [KG_TASK] ✅ No unconsolidated messages found")
                logger.info("🕸️ [KG_TASK] No unconsolidated messages found")
                return TaskResult(
                    success=True,
                    message="No unconsolidated messages",
                    data={"users_processed": 0, "messages_processed": 0}
                )
            
            print(f"🕸️ [KG_TASK] Found {len(users_with_pending)} users with unconsolidated messages")
            
            # Process each user
            total_messages = 0
            total_nodes = 0
            total_edges = 0
            errors = []
            
            for user_id, messages in users_with_pending.items():
                try:
                    print(f"🕸️ [KG_TASK] Processing user {user_id}: {len(messages)} messages")
                    
                    # Combine messages into single text for batch extraction
                    combined_text = " ".join([msg.get("content", "") for msg in messages])
                    
                    # Extract KG
                    await memory_manager._extract_knowledge_graph(user_id, combined_text)
                    
                    # Mark messages as consolidated
                    message_ids = [msg.get("_id") or msg.get("id") for msg in messages]
                    await self._mark_messages_consolidated(memory_manager, user_id, message_ids)
                    
                    total_messages += len(messages)
                    print(f"🕸️ [KG_TASK] ✅ User {user_id} processed successfully")
                    
                except Exception as e:
                    error_msg = f"Failed to process user {user_id}: {e}"
                    print(f"🕸️ [KG_TASK] ❌ {error_msg}")
                    logger.error(f"🕸️ [KG_TASK] {error_msg}")
                    errors.append(error_msg)
            
            # Summary
            duration = (datetime.utcnow() - start_time).total_seconds()
            print("🕸️ [KG_TASK] ========================================")
            print(f"🕸️ [KG_TASK] Consolidation complete in {duration:.2f}s")
            print(f"🕸️ [KG_TASK] Users processed: {len(users_with_pending)}")
            print(f"🕸️ [KG_TASK] Messages processed: {total_messages}")
            if errors:
                print(f"🕸️ [KG_TASK] Errors: {len(errors)}")
            print("🕸️ [KG_TASK] ========================================")
            
            logger.info(f"🕸️ [KG_TASK] Consolidation complete: {len(users_with_pending)} users, {total_messages} messages")
            
            return TaskResult(
                success=len(errors) == 0,
                message=f"Processed {total_messages} messages from {len(users_with_pending)} users",
                data={
                    "users_processed": len(users_with_pending),
                    "messages_processed": total_messages,
                    "errors": errors,
                    "duration_seconds": duration
                }
            )
            
        except Exception as e:
            print(f"🕸️ [KG_TASK] ❌ Task failed: {e}")
            logger.error(f"🕸️ [KG_TASK] Task failed: {e}")
            import traceback
            traceback.print_exc()
            
            return TaskResult(
                success=False,
                message=f"Task failed: {e}",
                data={"error": str(e)}
            )
    
    async def _get_users_with_pending_messages(
        self, 
        memory_manager, 
        batch_size: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get users with unconsolidated messages from working memory.
        
        Returns:
            Dict mapping user_id to list of unconsolidated messages
        """
        # Query working memory for messages without kg_consolidated flag
        # This is a simplified implementation - in production, you'd want
        # to track consolidation state more robustly
        
        users_with_pending = {}
        
        # Get all users from working memory store
        # Note: This is a simplified approach - in production, you'd want
        # a more efficient query
        try:
            # Access working memory store directly
            working_store = memory_manager._working_store
            
            # Get all conversations (simplified - in production, filter by timestamp)
            # For now, we'll just return empty dict as we don't have a direct API
            # to query unconsolidated messages
            
            # TODO: Implement proper tracking of consolidation state
            # Options:
            # 1. Add kg_consolidated flag to working memory messages
            # 2. Track last consolidation timestamp per user
            # 3. Use separate consolidation state table
            
            logger.info("🕸️ [KG_TASK] Note: Consolidation state tracking not yet implemented")
            return {}
            
        except Exception as e:
            logger.error(f"🕸️ [KG_TASK] Failed to get pending messages: {e}")
            return {}
    
    async def _mark_messages_consolidated(
        self,
        memory_manager,
        user_id: str,
        message_ids: List[str]
    ) -> None:
        """
        Mark messages as consolidated in working memory.
        
        Args:
            memory_manager: Memory manager instance
            user_id: User ID
            message_ids: List of message IDs to mark as consolidated
        """
        # TODO: Implement consolidation state tracking
        # For now, this is a no-op
        logger.info(f"🕸️ [KG_TASK] Would mark {len(message_ids)} messages as consolidated for user {user_id}")
        pass
