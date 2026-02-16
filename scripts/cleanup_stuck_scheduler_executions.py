#!/usr/bin/env python3
"""
Cleanup script for stuck scheduler executions.

This script marks all executions stuck in 'running' state as 'failed'
with a clear error message explaining they were orphaned before the fix.

Run this after applying the scheduler fixes to clean up pre-existing stuck jobs.
"""

import asyncio
from datetime import datetime, timezone, timedelta


async def cleanup_stuck_executions():
    """Mark all stuck 'running' executions as failed."""
    from aico.data.postgres.connection import get_session_factory
    from aico.data.uow import UnitOfWork
    
    print("🔧 Starting cleanup of stuck scheduler executions...")
    print("=" * 80)
    
    session_factory = await get_session_factory()
    
    async with UnitOfWork(session_factory) as uow:
        # Get all executions stuck in 'running' state
        all_executions = await uow.scheduler_task_executions.list(
            filters={'status': 'running'},
            limit=10000
        )
        
        print(f"Found {len(all_executions)} executions stuck in 'running' state")
        
        if not all_executions:
            print("✅ No stuck executions found!")
            return
        
        # Mark each as failed with explanation
        now = datetime.now(timezone.utc)
        fixed_count = 0
        
        for execution in all_executions:
            try:
                # Calculate how long it's been running
                if execution.started_at:
                    duration = (now - execution.started_at).total_seconds()
                else:
                    duration = 0
                
                # Update to failed status
                execution.status = 'failed'
                execution.completed_at = now
                execution.error_message = (
                    "Execution was stuck in 'running' state due to pre-fix bug. "
                    "Marked as failed during cleanup. "
                    "This was caused by the database migration issue that has now been fixed."
                )
                execution.duration_seconds = duration
                execution.result = {
                    "success": False,
                    "message": "Cleaned up stuck execution",
                    "cleanup_timestamp": now.isoformat()
                }
                
                await uow.scheduler_task_executions.update(execution)
                fixed_count += 1
                
                print(f"  ✓ Fixed execution {execution.execution_id[:8]}... "
                      f"(task: {execution.task_id}, stuck for {duration/3600:.1f}h)")
                
            except Exception as e:
                print(f"  ✗ Failed to fix execution {execution.execution_id[:8]}...: {e}")
        
        # Commit all changes
        await uow.commit()
        
        print("=" * 80)
        print(f"✅ Cleanup complete: Fixed {fixed_count} out of {len(all_executions)} executions")
        print("=" * 80)
        print("\n💡 New jobs will now complete properly with the applied fixes.")


if __name__ == "__main__":
    asyncio.run(cleanup_stuck_executions())
