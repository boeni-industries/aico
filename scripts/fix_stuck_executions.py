#!/usr/bin/env python3
"""
Fix stuck scheduler task executions.
Marks executions stuck in 'running' state as 'failed'.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add shared path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.data.postgres.connection import get_session_factory
from aico.data.uow import UnitOfWork


async def fix_stuck_executions():
    """Mark stuck running executions as failed."""
    
    session_factory = await get_session_factory()
    
    async with UnitOfWork(session_factory) as uow:
        # Get all running executions
        running_executions = await uow.scheduler_task_executions.list(
            filters={'status': 'running'},
            limit=1000
        )
        
        if not running_executions:
            print("✅ No stuck executions found")
            return
        
        print(f"Found {len(running_executions)} stuck executions:")
        
        for execution in running_executions:
            print(f"  - {execution.task_id} (execution_id={execution.execution_id})")
            print(f"    Started: {execution.started_at}")
            
            # Mark as failed
            execution.status = 'failed'
            execution.completed_at = datetime.now(timezone.utc)
            execution.error_message = "Execution stuck in running state - manually reset"
            
            await uow.scheduler_task_executions.update(execution)
        
        await uow.commit()
        print(f"\n✅ Marked {len(running_executions)} executions as failed")


if __name__ == '__main__':
    print("🔧 Fixing stuck scheduler executions...")
    print("=" * 60)
    asyncio.run(fix_stuck_executions())
    print("=" * 60)
