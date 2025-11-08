"""
AMS Memory Consolidation Task

Scheduled task for Adaptive Memory System memory consolidation.
Runs daily during idle periods to transfer important memories from
working memory to semantic memory.

Schedule: Daily at 2 AM (configurable via cron)
User Sharding: 1/7 of users per day to distribute load
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from aico.core.logging import get_logger

from .base import BaseTask, TaskContext, TaskResult

logger = get_logger("backend", "scheduler.tasks.ams_consolidation")


class MemoryConsolidationTask(BaseTask):
    """
    Scheduled task for AMS memory consolidation.
    
    Coordinates with ConsolidationScheduler to:
    - Detect system idle periods
    - Shard users across days (1/7 per day)
    - Execute memory consolidation jobs
    - Track consolidation state
    
    Configuration:
    - Schedule: core.memory.consolidation.schedule.cron
    - User sharding: core.memory.consolidation.schedule.user_shard_days
    - Idle detection: core.memory.consolidation.idle_detection
    """
    
    task_id = "ams.memory_consolidation"
    default_config = {
        "enabled": True,
        "schedule": "0 2 * * *",  # Daily at 2 AM
        "user_shard_days": 7,
        "cpu_threshold": 20.0,
        "check_interval_seconds": 300
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute memory consolidation task.
        
        Returns:
            TaskResult with consolidation statistics
        """
        start_time = datetime.utcnow()
        
        try:
            print("🧠 [AMS_TASK] ========================================")
            print("🧠 [AMS_TASK] Starting memory consolidation task")
            print("🧠 [AMS_TASK] ========================================")
            logger.info("🧠 [AMS_TASK] ========================================")
            logger.info("🧠 [AMS_TASK] Starting memory consolidation task")
            logger.info("🧠 [AMS_TASK] ========================================")
            
            # Load configuration
            consolidation_config = context.config_manager.get("core.memory.consolidation", {})
            enabled = context.get_config("enabled", consolidation_config.get("enabled", False))
            user_shard_days = context.get_config("user_shard_days", 7)
            
            # Check if consolidation is enabled
            if not enabled:
                print("🧠 [AMS_TASK] ⚠️  Consolidation disabled in configuration")
                logger.info("🧠 [AMS_TASK] Consolidation disabled in configuration")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="Consolidation disabled in configuration",
                    data={"enabled": False}
                )
            
            # Get memory manager from backend services
            try:
                print("🧠 [AMS_TASK] Getting memory manager from backend services...")
                from backend.services import get_memory_manager
                memory_manager = get_memory_manager(context.config_manager, context.db_connection)
                
                # Ensure memory manager is initialized
                if not memory_manager._initialized:
                    print("🧠 [AMS_TASK] Initializing memory manager...")
                    logger.info("🧠 [AMS_TASK] Initializing memory manager...")
                    await memory_manager.initialize()
                
                print("🧠 [AMS_TASK] ✅ Memory manager ready")
                
            except Exception as e:
                print(f"🧠 [AMS_TASK] ❌ Failed to get memory manager: {e}")
                logger.error(f"🧠 [AMS_TASK] Failed to get memory manager: {e}")
                return TaskResult(
                    success=False,
                    message="Memory manager not available",
                    error=str(e)
                )
            
            # Check if AMS components are enabled
            if not memory_manager._ams_enabled:
                print("🧠 [AMS_TASK] ⚠️  AMS components not enabled in memory manager")
                logger.warning("🧠 [AMS_TASK] AMS components not enabled in memory manager")
                return TaskResult(
                    success=False,
                    skipped=True,
                    message="AMS components not enabled",
                    data={"ams_enabled": False}
                )
            
            print("🧠 [AMS_TASK] ✅ AMS components are enabled")
            
            # Get consolidation scheduler
            consolidation_scheduler = memory_manager._consolidation_scheduler
            if not consolidation_scheduler:
                logger.error("🧠 [AMS_TASK] Consolidation scheduler not available")
                return TaskResult(
                    success=False,
                    message="Consolidation scheduler not initialized",
                    error="ConsolidationScheduler not available in memory manager"
                )
            
            # Step 1: Check if system is idle
            print("🧠 [AMS_TASK] Step 1: Checking system idle status...")
            logger.info("🧠 [AMS_TASK] Step 1: Checking system idle status...")
            idle_detector = memory_manager._idle_detector
            
            if idle_detector:
                is_idle = await idle_detector.is_system_idle()
                
                if not is_idle:
                    print("🧠 [AMS_TASK] ⚠️  System not idle, skipping consolidation")
                    logger.info("🧠 [AMS_TASK] System not idle, skipping consolidation")
                    return TaskResult(
                        success=False,
                        skipped=True,
                        message="System not idle",
                        data={"idle": False}
                    )
                
                print("🧠 [AMS_TASK] ✅ System is idle, proceeding with consolidation")
                logger.info("🧠 [AMS_TASK] ✅ System is idle, proceeding with consolidation")
            else:
                print("🧠 [AMS_TASK] ⚠️  Idle detector not available, proceeding anyway")
                logger.warning("🧠 [AMS_TASK] Idle detector not available, proceeding anyway")
            
            # Step 2: Get users for today's shard
            print(f"🧠 [AMS_TASK] Step 2: Getting users for today's shard (1/{user_shard_days})...")
            logger.info(f"🧠 [AMS_TASK] Step 2: Getting users for today's shard (1/{user_shard_days})...")
            
            # Get today's shard index (0-6 for 7-day sharding)
            today_shard = datetime.utcnow().day % user_shard_days
            
            # Get database connection from context
            db_connection = context.db_connection
            if not db_connection:
                logger.error("🧠 [AMS_TASK] Database connection not available")
                return TaskResult(
                    success=False,
                    message="Database connection not available",
                    error="No database connection in context"
                )
            
            # Query users for today's shard
            users_query = """
                SELECT uuid FROM users 
                WHERE is_active = 1
                AND (CAST(substr(uuid, 1, 8) AS INTEGER) % ?) = ?
            """
            
            users = db_connection.execute(
                users_query,
                (user_shard_days, today_shard)
            ).fetchall()
            
            user_ids = [row[0] for row in users]
            print(f"🧠 [AMS_TASK] Found {len(user_ids)} users for shard {today_shard}/{user_shard_days}")
            logger.info(f"🧠 [AMS_TASK] Found {len(user_ids)} users for shard {today_shard}/{user_shard_days}")
            
            if not user_ids:
                print("🧠 [AMS_TASK] No users to consolidate")
                logger.info("🧠 [AMS_TASK] No users to consolidate")
                return TaskResult(
                    success=True,
                    message="No users in today's shard",
                    data={
                        "shard": today_shard,
                        "total_shards": user_shard_days,
                        "users_processed": 0
                    }
                )
            
            # Step 3: Execute consolidation for each user
            print(f"🧠 [AMS_TASK] Step 3: Executing consolidation for {len(user_ids)} users...")
            logger.info(f"🧠 [AMS_TASK] Step 3: Executing consolidation for {len(user_ids)} users...")
            
            consolidation_results = {
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }
            
            for user_id in user_ids:
                try:
                    logger.info(f"🧠 [AMS_TASK] Processing user: {user_id}")
                    
                    # Execute consolidation via scheduler
                    result = await consolidation_scheduler.consolidate_user_memories(
                        user_id=user_id,
                        working_store=memory_manager._working_store,
                        semantic_store=memory_manager._semantic_store,
                        db_connection=db_connection,
                        max_messages=100
                    )
                    
                    if result.get("success"):
                        consolidation_results["successful"] += 1
                        logger.info(
                            f"🧠 [AMS_TASK] ✅ User {user_id} consolidated: "
                            f"{result.get('memories_created')}/{result.get('messages_retrieved')} messages"
                        )
                    else:
                        consolidation_results["failed"] += 1
                        consolidation_results["errors"].append({
                            "user_id": user_id,
                            "error": "; ".join(result.get("errors", ["Unknown error"]))
                        })
                        logger.error(f"🧠 [AMS_TASK] ❌ User {user_id} consolidation failed")
                    
                except Exception as e:
                    consolidation_results["failed"] += 1
                    consolidation_results["errors"].append({
                        "user_id": user_id,
                        "error": str(e)
                    })
                    logger.error(f"🧠 [AMS_TASK] ❌ User {user_id} consolidation failed: {e}")
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print("🧠 [AMS_TASK] ========================================")
            print(f"🧠 [AMS_TASK] Consolidation complete in {execution_time:.2f}s")
            print(f"🧠 [AMS_TASK] ✅ Successful: {consolidation_results['successful']}")
            print(f"🧠 [AMS_TASK] ❌ Failed: {consolidation_results['failed']}")
            print(f"🧠 [AMS_TASK] ⚠️  Skipped: {consolidation_results['skipped']}")
            print("🧠 [AMS_TASK] ========================================")
            
            logger.info("🧠 [AMS_TASK] ========================================")
            logger.info(f"🧠 [AMS_TASK] Consolidation complete in {execution_time:.2f}s")
            logger.info(f"🧠 [AMS_TASK] Successful: {consolidation_results['successful']}")
            logger.info(f"🧠 [AMS_TASK] Failed: {consolidation_results['failed']}")
            logger.info(f"🧠 [AMS_TASK] Skipped: {consolidation_results['skipped']}")
            logger.info("🧠 [AMS_TASK] ========================================")
            
            # Determine overall status
            success = consolidation_results["failed"] == 0
            
            return TaskResult(
                success=success,
                message=f"Consolidated memories for {consolidation_results['successful']}/{len(user_ids)} users",
                duration_seconds=execution_time,
                data={
                    "shard": today_shard,
                    "total_shards": user_shard_days,
                    "users_total": len(user_ids),
                    "users_successful": consolidation_results["successful"],
                    "users_failed": consolidation_results["failed"],
                    "users_skipped": consolidation_results["skipped"],
                    "errors": consolidation_results["errors"][:10]  # Limit error details
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            print(f"🧠 [AMS_TASK] ❌❌❌ Task execution failed: {e}")
            logger.error(f"🧠 [AMS_TASK] ❌ Task execution failed: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(f"🧠 [AMS_TASK] Traceback:\n{error_trace}")
            logger.error(f"🧠 [AMS_TASK] Traceback: {error_trace}")
            
            return TaskResult(
                success=False,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                duration_seconds=execution_time
            )
