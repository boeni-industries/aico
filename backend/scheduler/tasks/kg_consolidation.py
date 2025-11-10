"""
KG Consolidation Task

Scheduled task for Knowledge Graph extraction from working memory.
Runs periodically during idle periods to extract entities and relationships
from unconsolidated messages.

Schedule: Daily at 2:00 AM (configurable via cron)
Architecture: Aligns with AMS design - fast hippocampal capture, slow cortical consolidation
"""

import asyncio
import json
import time
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
        "schedule": "0 2 * * *",  # Daily at 2:00 AM
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
            
            # Load configuration from core.memory.consolidation.kg_extraction
            memory_config = context.config_manager.get("core.memory", {})
            consolidation_config = memory_config.get("consolidation", {})
            kg_config = consolidation_config.get("kg_extraction", {})
            
            if not kg_config:
                print("🕸️ [KG_TASK] ⚠️  Configuration 'core.memory.consolidation.kg_extraction' not found, using defaults")
                logger.warning("🕸️ [KG_TASK] Configuration 'core.memory.consolidation.kg_extraction' not found")
            
            enabled = context.get_config("enabled", kg_config.get("enabled", True))
            batch_size = context.get_config("batch_size", kg_config.get("batch_size", 50))
            
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
            
            # Get memory manager from AI registry (via conversation engine)
            try:
                print("🕸️ [KG_TASK] Getting memory manager from AI registry...")
                
                # Access conversation engine from service container
                if not hasattr(context, 'service_container') or not context.service_container:
                    print("🕸️ [KG_TASK] ❌ Service container not available in context")
                    logger.error("🕸️ [KG_TASK] Service container not available")
                    return TaskResult(
                        success=False,
                        message="Service container not available",
                        data={"error": "No service container in task context"}
                    )
                
                # Get conversation engine which has access to memory manager
                conversation_engine = context.service_container.get_service('conversation_engine')
                if not conversation_engine:
                    print("🕸️ [KG_TASK] ❌ Conversation engine not found")
                    logger.error("🕸️ [KG_TASK] Conversation engine not found")
                    return TaskResult(
                        success=False,
                        message="Conversation engine not available",
                        data={"error": "Conversation engine not in service container"}
                    )
                
                # Get memory manager from AI registry
                from backend.services.conversation_engine import ai_registry
                memory_manager = ai_registry.get("memory")
                if not memory_manager:
                    print("🕸️ [KG_TASK] ❌ Memory manager not found in AI registry")
                    logger.error("🕸️ [KG_TASK] Memory manager not found in AI registry")
                    return TaskResult(
                        success=False,
                        message="Memory manager not available",
                        data={"error": "Memory manager not in AI registry"}
                    )
                
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
                import traceback
                traceback.print_exc()
                return TaskResult(
                    success=False,
                    message="Memory manager not available",
                    data={"error": str(e)}
                )
            
            # Check if modelservice client is available (health check will happen on first use)
            if not memory_manager._kg_modelservice:
                print("🕸️ [KG_TASK] ❌ Modelservice client not initialized")
                logger.error("🕸️ [KG_TASK] Modelservice client not initialized")
                return TaskResult(
                    success=False,
                    message="Modelservice client not initialized",
                    data={"modelservice_initialized": False}
                )
            print("🕸️ [KG_TASK] ✅ Modelservice client available")
            
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
            
            for user_idx, (user_id, messages) in enumerate(users_with_pending.items(), 1):
                try:
                    user_start = time.time()
                    print(f"\n🕸️ [KG_TASK] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    print(f"🕸️ [KG_TASK] Processing user {user_idx}/{len(users_with_pending)}: {user_id[:8]}...")
                    print(f"🕸️ [KG_TASK] Messages to process: {len(messages)}")
                    print(f"🕸️ [KG_TASK] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    # Process messages individually to preserve conversational context
                    # This maximizes entity extraction quality and relationship detection
                    processed_count = 0
                    for msg_idx, msg in enumerate(messages, 1):
                        try:
                            msg_content = msg.get("content", "").strip()
                            if not msg_content:
                                continue
                            
                            msg_start = time.time()
                            print(f"\n🕸️ [KG_TASK] 📝 Message {msg_idx}/{len(messages)}: {msg_content[:60]}...")
                            
                            # Extract KG from individual message
                            await memory_manager._extract_knowledge_graph(user_id, msg_content)
                            
                            msg_time = time.time() - msg_start
                            processed_count += 1
                            
                            # Progress indicator
                            avg_time = (time.time() - user_start) / processed_count
                            remaining = len(messages) - processed_count
                            eta_seconds = avg_time * remaining
                            print(f"🕸️ [KG_TASK] ⏱️  Message completed in {msg_time:.2f}s | Avg: {avg_time:.2f}s/msg | ETA: {eta_seconds:.0f}s ({remaining} remaining)")
                            
                        except Exception as e:
                            error_msg = f"Failed to process message for user {user_id}: {e}"
                            print(f"🕸️ [KG_TASK] ⚠️  {error_msg}")
                            logger.warning(f"🕸️ [KG_TASK] {error_msg}")
                            # Continue processing other messages
                    
                    # Mark messages as consolidated (get unique conversation IDs)
                    conversation_ids = list(set([msg.get("conversation_id") for msg in messages if msg.get("conversation_id")]))
                    await self._mark_messages_consolidated(memory_manager, user_id, conversation_ids)
                    
                    total_messages += processed_count
                    user_time = time.time() - user_start
                    print(f"\n🕸️ [KG_TASK] ✅ User {user_id[:8]}... completed in {user_time:.2f}s")
                    print(f"🕸️ [KG_TASK]    Messages: {processed_count}/{len(messages)}")
                    print(f"🕸️ [KG_TASK]    Avg time: {user_time/processed_count:.2f}s per message")
                    
                except Exception as e:
                    error_msg = f"Failed to process user {user_id}: {e}"
                    print(f"🕸️ [KG_TASK] ❌ {error_msg}")
                    logger.error(f"🕸️ [KG_TASK] {error_msg}")
                    errors.append(error_msg)
            
            # Summary
            duration = (datetime.utcnow() - start_time).total_seconds()
            print("\n🕸️ [KG_TASK] ════════════════════════════════════════════════════════")
            print(f"🕸️ [KG_TASK] 🎉 CONSOLIDATION COMPLETE")
            print(f"🕸️ [KG_TASK] ════════════════════════════════════════════════════════")
            print(f"🕸️ [KG_TASK] ⏱️  Total time:     {duration:.2f}s ({duration/60:.1f} minutes)")
            print(f"🕸️ [KG_TASK] 👥 Users:          {len(users_with_pending)}")
            print(f"🕸️ [KG_TASK] 📨 Messages:       {total_messages}")
            print(f"🕸️ [KG_TASK] ⚡ Avg per message: {duration/total_messages:.2f}s" if total_messages > 0 else "")
            if errors:
                print(f"🕸️ [KG_TASK] ⚠️  Errors:         {len(errors)}")
            print(f"🕸️ [KG_TASK] ════════════════════════════════════════════════════════")
            
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
        users_with_pending = {}
        
        try:
            # Access working memory store directly
            working_store = memory_manager._working_store
            
            if not working_store:
                logger.warning("🕸️ [KG_TASK] Working memory store not available")
                return {}
            
            # Ensure working store is initialized
            if not working_store._initialized:
                print("🕸️ [KG_TASK] Initializing working memory store...")
                await working_store.initialize()
            
            print(f"🕸️ [KG_TASK] Scanning LMDB at: {working_store._db_path}")
            print(f"🕸️ [KG_TASK] Available databases: {list(working_store.dbs.keys())}")
            
            # Get all conversations from working memory
            # Scan session_memory database for user messages
            db = working_store.dbs.get("session_memory")
            if not db:
                logger.warning("🕸️ [KG_TASK] session_memory database not available")
                return {}
            
            with working_store.env.begin(db=db) as txn:
                cursor = txn.cursor()
                message_count = 0
                total_keys = 0
                
                # Iterate through all messages (stored as conversation_id:timestamp keys)
                for key, value in cursor:
                    total_keys += 1
                    try:
                        # Parse message data (each key is a single message, not a conversation)
                        msg = json.loads(value.decode('utf-8'))
                        
                        # Only process user messages (not assistant responses)
                        if msg.get('role') != 'user':
                            continue
                        
                        # Check if message has been consolidated
                        if msg.get('kg_consolidated', False):
                            continue
                        
                        # Get user_id
                        user_id = msg.get('user_id')
                        if not user_id:
                            continue
                        
                        # Add to pending messages
                        if user_id not in users_with_pending:
                            users_with_pending[user_id] = []
                        
                        users_with_pending[user_id].append(msg)
                        message_count += 1
                        
                        # Limit batch size per user
                        if len(users_with_pending[user_id]) >= batch_size:
                            break
                        
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"🕸️ [KG_TASK] Failed to parse message: {e}")
                        continue
                
                print(f"🕸️ [KG_TASK] Scanned {total_keys} total keys, found {message_count} unconsolidated user messages")
                logger.info(f"🕸️ [KG_TASK] Found {message_count} unconsolidated messages from {len(users_with_pending)} users")
                return users_with_pending
            
        except Exception as e:
            logger.error(f"🕸️ [KG_TASK] Failed to get pending messages: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def _mark_messages_consolidated(
        self,
        memory_manager,
        user_id: str,
        conversation_ids: List[str]
    ) -> None:
        """
        Mark messages as consolidated in working memory.
        
        Args:
            memory_manager: Memory manager instance
            user_id: User ID
            conversation_ids: List of conversation IDs that were processed
        """
        try:
            working_store = memory_manager._working_store
            
            if not working_store or not working_store._initialized:
                logger.warning("🕸️ [KG_TASK] Working memory store not initialized")
                return
            
            db = working_store.dbs.get("session_memory")
            if not db:
                logger.warning("🕸️ [KG_TASK] session_memory database not available")
                return
            
            # Update messages in LMDB by scanning for matching conversation_ids
            updated_count = 0
            with working_store.env.begin(db=db, write=True) as txn:
                cursor = txn.cursor()
                
                for key, value in cursor:
                    try:
                        # Check if this message belongs to one of the processed conversations
                        key_str = key.decode('utf-8')
                        conv_id = key_str.split(':')[0] if ':' in key_str else None
                        
                        if conv_id not in conversation_ids:
                            continue
                        
                        # Parse and update message
                        msg = json.loads(value.decode('utf-8'))
                        
                        if msg.get('role') == 'user' and msg.get('user_id') == user_id:
                            if not msg.get('kg_consolidated', False):
                                msg['kg_consolidated'] = True
                                msg['kg_consolidated_at'] = datetime.utcnow().isoformat()
                                
                                # Write back to LMDB
                                txn.put(key, json.dumps(msg).encode('utf-8'))
                                updated_count += 1
                    
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.warning(f"🕸️ [KG_TASK] Failed to update message: {e}")
                        continue
            
            logger.info(f"🕸️ [KG_TASK] Marked {updated_count} messages as consolidated for user {user_id}")
            
        except Exception as e:
            logger.error(f"🕸️ [KG_TASK] Failed to mark messages as consolidated: {e}")
            import traceback
            traceback.print_exc()
