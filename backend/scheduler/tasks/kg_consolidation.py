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
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from aico.core.logging import get_logger
from aico.ai.knowledge_graph.models import PropertyGraph

from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend.scheduler.tasks.kg_consolidation")


class KGConsolidationTask(BaseTask):
    """
    Scheduled task for Knowledge Graph consolidation.
    
    Extracts entities and relationships from unconsolidated working memory
    messages and stores them in the knowledge graph.
    
    Configuration:
    - Schedule: memory.kg_consolidation.schedule.cron
    - Batch size: memory.kg_consolidation.batch_size
    - Enabled: memory.kg_consolidation.enabled
    """
    
    task_id = "ams.kg_consolidation"
    default_config = {
        "enabled": True,
        "schedule": "30 2 * * *",  # Daily at 2:30 AM (staggered after memory consolidation)
        "batch_size": 50,  # Max messages to process per run
        "max_age_hours": 24,  # Only process messages from last 24h
        "max_concurrent_extractions": 4  # Parallel message processing (10x speedup)
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute KG consolidation task.
        
        Returns:
            TaskResult with consolidation statistics
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            print("🕸️ [KG_TASK] ========================================")
            print("🕸️ [KG_TASK] Starting KG consolidation task")
            print("🕸️ [KG_TASK] ========================================")
            logger.info("🕸️ [KG_TASK] Starting KG consolidation task")
            
            # Load configuration from memory.consolidation.kg_extraction
            memory_config = context.config_manager.get("memory", {})
            consolidation_config = memory_config.get("consolidation", {})
            kg_config = consolidation_config.get("kg_extraction", {})
            
            if not kg_config:
                print("🕸️ [KG_TASK] ⚠️  Configuration 'memory.consolidation.kg_extraction' not found, using defaults")
                logger.warning("🕸️ [KG_TASK] Configuration 'memory.consolidation.kg_extraction' not found")
            
            enabled = context.get_config("enabled", kg_config.get("enabled", True))
            batch_size = context.get_config("batch_size", kg_config.get("batch_size", 50))
            max_concurrent = context.get_config("max_concurrent_extractions", kg_config.get("max_concurrent_extractions", 4))
            
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
            users_with_pending = await memory_manager._get_users_with_unconsolidated_messages(
                max_age_hours=max_age_hours,
                batch_size=batch_size,
            )

            # Filter to non-technical active users via Postgres user_profiles
            if users_with_pending:
                from aico.data.postgres.connection import get_session_factory
                from aico.data.uow import UnitOfWork

                session_factory = await get_session_factory()
                async with UnitOfWork(session_factory) as uow:
                    non_technical_users = await uow.user_profiles.list(
                        filters={"is_active": True, "is_technical": False},
                        limit=100000,
                    )
                    allowed_ids = {u.uuid for u in non_technical_users}

                users_with_pending = {
                    user_id: msgs
                    for user_id, msgs in users_with_pending.items()
                    if user_id in allowed_ids
                }
            
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
                    print(f"🕸️ [KG_TASK] Parallel batches: {max_concurrent}")
                    print(f"🕸️ [KG_TASK] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    # Process messages in parallel batches for 10x speedup
                    # Each message is independent, so parallel processing is safe
                    processed_count = 0
                    
                    # Create shared entity resolver for incremental HNSW indexing (2x speedup)
                    # The resolver maintains HNSW index state across messages in the batch
                    # This avoids re-indexing existing nodes for each message
                    from aico.ai.knowledge_graph.entity_resolution import EntityResolver
                    
                    print(f"🕸️ [KG_TASK] 🔧 Creating shared entity resolver for batch (incremental HNSW)...")
                    shared_resolver = EntityResolver(
                        modelservice_client=memory_manager._kg_modelservice,
                        config=context.config_manager
                    )
                    
                    # Pre-populate resolver with existing nodes for deduplication
                    print(f"🕸️ [KG_TASK] 🔍 Loading existing nodes for deduplication...")
                    existing_nodes = await memory_manager._kg_storage.get_user_nodes(user_id, current_only=True)
                    if existing_nodes:
                        print(f"🕸️ [KG_TASK] 📊 Indexing {len(existing_nodes)} existing nodes in HNSW...")
                        await shared_resolver._index_existing_nodes(existing_nodes)
                    else:
                        print(f"🕸️ [KG_TASK] ℹ️  No existing nodes found (first-time extraction)")
                    
                    # Helper function to process a single message
                    async def process_message(msg_idx: int, msg: Dict[str, Any]) -> bool:
                        """Process a single message and return success status."""
                        try:
                            msg_content = msg.get("content", "").strip()
                            if not msg_content:
                                return False
                            
                            msg_start = time.time()
                            print(f"\n🕸️ [KG_TASK] 📝 Message {msg_idx}/{len(messages)}: {msg_content[:60]}...")
                            
                            # Extract KG from individual message using shared resolver
                            # This enables incremental HNSW indexing across batch
                            await memory_manager._extract_knowledge_graph_with_resolver(
                                user_id, msg_content, shared_resolver
                            )
                            
                            msg_time = time.time() - msg_start
                            print(f"🕸️ [KG_TASK] ⏱️  Message {msg_idx} completed in {msg_time:.2f}s")
                            return True
                            
                        except Exception as e:
                            error_msg = f"Failed to process message {msg_idx} for user {user_id}: {e}"
                            print(f"🕸️ [KG_TASK] ⚠️  {error_msg}")
                            logger.warning(f"🕸️ [KG_TASK] {error_msg}")
                            return False
                    
                    # Process messages in parallel batches
                    for batch_start in range(0, len(messages), max_concurrent):
                        batch_end = min(batch_start + max_concurrent, len(messages))
                        batch = messages[batch_start:batch_end]
                        
                        batch_start_time = time.time()
                        print(f"\n🕸️ [KG_TASK] 🚀 Processing batch {batch_start//max_concurrent + 1} ({len(batch)} messages in parallel)...")
                        
                        # Process batch in parallel
                        results = await asyncio.gather(
                            *[process_message(batch_start + i + 1, msg) for i, msg in enumerate(batch)],
                            return_exceptions=True
                        )
                        
                        # Count successes
                        batch_successes = sum(1 for r in results if r is True)
                        processed_count += batch_successes
                        
                        batch_time = time.time() - batch_start_time
                        avg_time = (time.time() - user_start) / max(processed_count, 1)
                        remaining = len(messages) - (batch_end)
                        eta_seconds = avg_time * remaining
                        
                        print(f"🕸️ [KG_TASK] ✅ Batch completed in {batch_time:.2f}s ({batch_successes}/{len(batch)} successful)")
                        print(f"🕸️ [KG_TASK] ⏱️  Avg: {avg_time:.2f}s/msg | ETA: {eta_seconds:.0f}s ({remaining} remaining)")
                    
                    # Post-batch deduplication pass to catch cross-message duplicates
                    print(f"\n🕸️ [KG_TASK] 🔄 Running post-batch deduplication...")
                    dedup_start = time.time()
                    dedup_stats = await self._deduplicate_batch(
                        memory_manager, 
                        user_id, 
                        shared_resolver
                    )
                    dedup_time = time.time() - dedup_start
                    print(f"🕸️ [KG_TASK] ✅ Post-batch deduplication completed in {dedup_time:.2f}s")
                    if dedup_stats.get('duplicates_merged', 0) > 0:
                        print(f"🕸️ [KG_TASK]    Merged {dedup_stats['duplicates_merged']} duplicate entities")
                        print(f"🕸️ [KG_TASK]    Updated {dedup_stats['edges_updated']} edges")
                    else:
                        print(f"🕸️ [KG_TASK]    No duplicates found (clean extraction)")
                    
                    # Trigger ChromaDB cleanup after deduplication to remove orphaned embeddings
                    print(f"🕸️ [KG_TASK] 🧹 Running post-deduplication ChromaDB cleanup...")
                    cleanup_start = time.time()
                    await memory_manager._kg_storage.save_graph(
                        PropertyGraph(nodes=[], edges=[]),
                        superseded_node_ids=set()
                    )
                    cleanup_time = time.time() - cleanup_start
                    print(f"🕸️ [KG_TASK] ✅ ChromaDB cleanup completed in {cleanup_time:.2f}s")
                    
                    # Clean up historical embeddings from ChromaDB after deduplication
                    print(f"\n🕸️ [KG_TASK] 🧹 Cleaning up historical ChromaDB embeddings...")
                    cleanup_start = time.time()
                    from .kg_consolidation_chromadb import cleanup_chromadb_historical
                    cleanup_stats = await cleanup_chromadb_historical(memory_manager)
                    cleanup_time = time.time() - cleanup_start
                    print(f"🕸️ [KG_TASK] ✅ ChromaDB cleanup completed in {cleanup_time:.2f}s")
                    if cleanup_stats.get('nodes_deleted', 0) > 0 or cleanup_stats.get('edges_deleted', 0) > 0:
                        print(f"🕸️ [KG_TASK]    Deleted {cleanup_stats['nodes_deleted']} historical node embeddings")
                        print(f"🕸️ [KG_TASK]    Deleted {cleanup_stats['edges_deleted']} historical edge embeddings")
                    else:
                        print(f"🕸️ [KG_TASK]    No historical embeddings to clean")
                    
                    # Mark messages as consolidated (get message timestamps)
                    message_timestamps = [msg.get("timestamp") for msg in messages if msg.get("timestamp")]
                    print(f"🕸️ [KG_TASK] 🏷️  Marking {len(message_timestamps)} messages as consolidated")
                    if not message_timestamps:
                        print(f"🕸️ [KG_TASK] ⚠️  WARNING: No timestamps found in messages!")
                    else:
                        await self._mark_messages_consolidated(memory_manager, user_id, message_timestamps)
                        print(f"🕸️ [KG_TASK] ✅ Messages marked as consolidated")
                    
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
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
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
    
    async def _deduplicate_batch(
        self,
        memory_manager,
        user_id: str,
        shared_resolver
    ) -> Dict[str, int]:
        """
        Run post-batch deduplication to catch cross-message duplicates.
        
        This catches duplicates that were created across parallel message processing,
        where the same entity (e.g., "TechCorp") appears in multiple messages.
        
        Args:
            memory_manager: Memory manager instance
            user_id: User ID
            shared_resolver: Shared entity resolver with HNSW index
        
        Returns:
            Dict with deduplication statistics
        """
        try:
            # Load all current entities for the user
            all_nodes = await memory_manager._kg_storage.get_user_nodes(user_id, current_only=True)
            
            if len(all_nodes) < 2:
                # Nothing to deduplicate
                return {'duplicates_merged': 0, 'edges_updated': 0}
            
            print(f"🕸️ [KG_TASK] 🔍 Analyzing {len(all_nodes)} entities for duplicates...")
            
            # Group entities by label for efficient comparison (language-agnostic)
            # Only compare entities with the same label (e.g., ORG vs ORG, PERSON vs PERSON)
            from collections import defaultdict
            entities_by_label = defaultdict(list)
            for node in all_nodes:
                entities_by_label[node.label].append(node)
            
            print(f"🕸️ [KG_TASK] 📊 Entity distribution: {dict((label, len(nodes)) for label, nodes in entities_by_label.items())}")
            
            # Process each label group separately to avoid false positives
            from aico.ai.knowledge_graph.models import PropertyGraph
            total_superseded_ids = []
            node_mapping = {}  # Track superseded_id -> canonical_id mappings
            
            for label, nodes in entities_by_label.items():
                if len(nodes) < 2:
                    # No duplicates possible with only 1 entity
                    continue
                
                print(f"🕸️ [KG_TASK] 🔍 Checking {len(nodes)} {label} entities for duplicates...")
                
                # Create a temporary graph with only this label's nodes
                temp_graph = PropertyGraph()
                temp_graph.nodes = nodes
                
                # Run entity resolution on this subset
                resolution_result = await shared_resolver.resolve(
                    new_graph=temp_graph,
                    user_id=user_id,
                    existing_nodes=[]  # All nodes are already in the graph
                )
                
                if resolution_result.superseded_node_ids:
                    print(f"🕸️ [KG_TASK] ✅ Found {len(resolution_result.superseded_node_ids)} duplicate {label} entities")
                    total_superseded_ids.extend(resolution_result.superseded_node_ids)
                    
                    # Get the node mapping from the resolution result
                    if resolution_result.node_mapping:
                        node_mapping.update(resolution_result.node_mapping)
            
            if not total_superseded_ids:
                return {'duplicates_merged': 0, 'edges_updated': 0}
            
            print(f"🕸️ [KG_TASK] 🔍 Total: {len(total_superseded_ids)} duplicate entities to merge")
            print(f"🕸️ [KG_TASK] 🔍 Node mapping: {len(node_mapping)} superseded -> canonical mappings")
            
            # Mark superseded nodes as historical and update edges via UoW
            edges_updated = 0
            
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from datetime import datetime, UTC
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Mark duplicates as historical (only if not already historical)
                for node_id in total_superseded_ids:
                    # Check if node exists and is current
                    node = await uow.kg_nodes.get(filters={'id': node_id})
                    if not node:
                        continue
                    
                    # Skip if already historical
                    if not node.is_current:
                        continue
                    
                    # Check if a historical version already exists
                    historical_nodes = await uow.kg_nodes.list(
                        filters={
                            'user_id': node.user_id,
                            'label': node.label,
                            'properties': node.properties,
                            'is_current': False
                        },
                        limit=1
                    )
                    
                    if historical_nodes:
                        # Historical version already exists - delete this node instead
                        logger.warning(
                            f"[POST_DEDUP] Historical node already exists for {node.label}. "
                            f"Deleting duplicate node {node_id} instead of marking historical."
                        )
                        # First delete edges referencing this node
                        edges_to_delete = await uow.kg_edges.list(
                            filters={'source_id': node_id},
                            limit=10000
                        )
                        edges_to_delete.extend(await uow.kg_edges.list(
                            filters={'target_id': node_id},
                            limit=10000
                        ))
                        for edge in edges_to_delete:
                            await uow.kg_edges.delete(edge.id)
                        
                        # Then delete the node
                        await uow.kg_nodes.delete(node_id)
                    else:
                        # Safe to mark as historical
                        node.is_current = False
                        node.updated_at = datetime.now(UTC)
                        await uow.kg_nodes.update(node)
            
                # Update edges to point to canonical nodes
                print(f"🕸️ [KG_TASK] 🔄 Updating edges to point to canonical nodes...")
                for superseded_id, canonical_id in node_mapping.items():
                    # Update edges where superseded node is the source
                    source_edges = await uow.kg_edges.list(
                        filters={'source_id': superseded_id, 'user_id': user_id},
                        limit=10000
                    )
                    
                    for edge in source_edges:
                        try:
                            edge.source_id = canonical_id
                            edge.updated_at = datetime.now(UTC)
                            await uow.kg_edges.update(edge)
                            edges_updated += 1
                        except Exception as e:
                            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                                logger.warning(
                                    f"[POST_DEDUP] UNIQUE constraint prevented edge update (source_id). "
                                    f"Deleting duplicate edge: superseded={superseded_id}, canonical={canonical_id}"
                                )
                                await uow.kg_edges.delete(edge.id)
                            else:
                                raise
                    
                    # Update edges where superseded node is the target
                    target_edges = await uow.kg_edges.list(
                        filters={'target_id': superseded_id, 'user_id': user_id},
                        limit=10000
                    )
                    
                    for edge in target_edges:
                        try:
                            edge.target_id = canonical_id
                            edge.updated_at = datetime.now(UTC)
                            await uow.kg_edges.update(edge)
                            edges_updated += 1
                        except Exception as e:
                            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                                logger.warning(
                                    f"[POST_DEDUP] UNIQUE constraint prevented edge update (target_id). "
                                    f"Deleting duplicate edge: superseded={superseded_id}, canonical={canonical_id}"
                                )
                                await uow.kg_edges.delete(edge.id)
                            else:
                                raise
            
                print(f"🕸️ [KG_TASK] ✅ Updated {edges_updated} edge references")
                
                # CRITICAL FIX: Update orphaned edges from previous batches
                print(f"🕸️ [KG_TASK] 🔄 Checking for orphaned edges from previous batches...")
                
                # Find all current edges for this user
                all_edges = await uow.kg_edges.list(
                    filters={'user_id': user_id, 'is_current': True},
                    limit=100000
                )
                
                orphaned_fixed = 0
                orphaned_deleted = 0
                
                for edge in all_edges:
                    # Check if source or target nodes are historical
                    source_node = await uow.kg_nodes.get(filters={'id': edge.source_id})
                    target_node = await uow.kg_nodes.get(filters={'id': edge.target_id})
                    
                    source_historical = source_node and not source_node.is_current
                    target_historical = target_node and not target_node.is_current
                    
                    if not source_historical and not target_historical:
                        continue
                    
                    fixed = False
                    
                    # If source is historical, find its canonical replacement
                    if source_historical and source_node:
                        canonical_sources = await uow.kg_nodes.list(
                            filters={
                                'user_id': user_id,
                                'label': source_node.label,
                                'properties': source_node.properties,
                                'is_current': True
                            },
                            limit=1
                        )
                        
                        if canonical_sources:
                            try:
                                edge.source_id = canonical_sources[0].id
                                edge.updated_at = datetime.now(UTC)
                                await uow.kg_edges.update(edge)
                                orphaned_fixed += 1
                                fixed = True
                            except Exception as e:
                                if "unique" in str(e).lower():
                                    await uow.kg_edges.delete(edge.id)
                                    orphaned_deleted += 1
                                    fixed = True
                    
                    # If target is historical, find its canonical replacement
                    if target_historical and target_node and not fixed:
                        canonical_targets = await uow.kg_nodes.list(
                            filters={
                                'user_id': user_id,
                                'label': target_node.label,
                                'properties': target_node.properties,
                                'is_current': True
                            },
                            limit=1
                        )
                        
                        if canonical_targets:
                            try:
                                edge.target_id = canonical_targets[0].id
                                edge.updated_at = datetime.now(UTC)
                                await uow.kg_edges.update(edge)
                                orphaned_fixed += 1
                                fixed = True
                            except Exception as e:
                                if "unique" in str(e).lower():
                                    await uow.kg_edges.delete(edge.id)
                                    orphaned_deleted += 1
                                    fixed = True
                    
                    # If we couldn't find a canonical node, delete the edge as last resort
                    if not fixed:
                        await uow.kg_edges.delete(edge.id)
                        orphaned_deleted += 1
                
                if orphaned_fixed > 0:
                    print(f"🕸️ [KG_TASK] ✅ Fixed {orphaned_fixed} orphaned edges from previous batches")
                if orphaned_deleted > 0:
                    print(f"🕸️ [KG_TASK] 🧹 Deleted {orphaned_deleted} orphaned edges (no canonical node found)")
                    logger.warning(f"[POST_DEDUP] Deleted {orphaned_deleted} orphaned edges with no canonical replacement")
                
                await uow.commit()
            
            return {
                'duplicates_merged': len(total_superseded_ids),
                'edges_updated': edges_updated
            }
            
        except Exception as e:
            print(f"🕸️ [KG_TASK] ⚠️  Post-batch deduplication failed: {e}")
            import traceback
            traceback.print_exc()
            return {'nodes_deleted': 0, 'edges_deleted': 0}
    
    async def _mark_messages_consolidated(
        self,
        memory_manager,
        user_id: str,
        message_timestamps: List[str]
    ) -> None:
        """
        Mark specific messages as consolidated in working memory.
        
        Args:
            memory_manager: Memory manager instance
            user_id: User ID
            message_timestamps: List of message timestamps that were processed
        """
        try:
            working_store = memory_manager._working_store
            
            if not working_store or not working_store._initialized:
                logger.info("🕸️ [KG_TASK] Working memory store not yet initialized, skipping consolidation marking")
                return
            
            db = working_store.dbs.get("session_memory")
            if not db:
                logger.warning("🕸️ [KG_TASK] session_memory database not available")
                return
            
            # Update messages in LMDB by scanning for matching timestamps
            # First pass: collect messages to update (read-only)
            messages_to_update = []
            total_scanned = 0
            matching_timestamps = 0
            
            # Convert timestamps to set for O(1) lookup
            timestamp_set = set(message_timestamps)
            logger.info(f"🕸️ [KG_TASK] 🔍 Scanning LMDB for {len(timestamp_set)} specific message timestamps")
            
            with working_store.env.begin(db=db, write=False) as txn:
                cursor = txn.cursor()
                
                for key, value in cursor:
                    total_scanned += 1
                    try:
                        # Parse message
                        msg = json.loads(value.decode('utf-8'))
                        
                        # Check if this is one of the processed messages
                        msg_timestamp = msg.get('timestamp')
                        if msg_timestamp not in timestamp_set:
                            continue
                        
                        matching_timestamps += 1
                        
                        # Verify it's a user message for this user
                        if msg.get('role') == 'user' and msg.get('user_id') == user_id:
                            # Check if not consolidated (handle both None and False)
                            kg_consolidated = msg.get('kg_consolidated')
                            logger.debug(f"🕸️ [KG_TASK] Message {msg_timestamp}: kg_consolidated={kg_consolidated}")
                            
                            if not kg_consolidated:
                                msg['kg_consolidated'] = True
                                msg['kg_consolidated_at'] = datetime.now(timezone.utc).isoformat()
                                messages_to_update.append((key, msg))
                    
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.warning(f"🕸️ [KG_TASK] Failed to parse message: {e}")
                        continue
            
            logger.info(f"🕸️ [KG_TASK] Marking {len(messages_to_update)} messages as consolidated (scanned {total_scanned} total, matched {matching_timestamps} timestamps)")
            
            # Second pass: write updates
            updated_count = 0
            with working_store.env.begin(db=db, write=True) as txn:
                for key, msg in messages_to_update:
                    try:
                        txn.put(key, json.dumps(msg).encode('utf-8'))
                        updated_count += 1
                    except Exception as e:
                        logger.warning(f"🕸️ [KG_TASK] Failed to update message: {e}")
                        continue
            
            logger.info(f"🕸️ [KG_TASK] Marked {updated_count} messages as consolidated for user {user_id}")
            
        except Exception as e:
            logger.error(f"🕸️ [KG_TASK] Failed to mark messages as consolidated: {e}")
            import traceback
            traceback.print_exc()
