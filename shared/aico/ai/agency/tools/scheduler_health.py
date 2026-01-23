"""Scheduler Health Monitoring Tools

Atomic tools for checking task scheduler health and execution status.
"""

from typing import Dict, Any
from datetime import datetime, UTC, timedelta

from aico.core.logging import get_logger
from aico.ai.agency.tools.registry import ToolDefinition, get_tool_registry


logger = get_logger("aico.ai.agency.tools.scheduler_health")


async def tool_scheduler_check_status(lookback_minutes: int = 60) -> Dict[str, Any]:
    """Check scheduler status by querying recent task executions.
    
    Args:
        lookback_minutes: Minutes to look back for recent executions
    
    Returns:
        Dict with ok, data, and error fields following tool contract
    """
    try:
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        # Use provided lookback_minutes parameter
        lookback_time = datetime.now(UTC) - timedelta(minutes=lookback_minutes)
        
        session_factory = await get_session_factory()
        
        async with UnitOfWork(session_factory) as uow:
            # Query recent task executions
            executions = await uow.scheduler_task_executions.list(
                filters={},
                limit=100
            )
            
            # Filter by time and analyze
            recent_executions = [
                e for e in executions 
                if e.started_at and e.started_at >= lookback_time
            ]
            
            total_recent = len(recent_executions)
            running = sum(1 for e in recent_executions if e.status == "running")
            completed = sum(1 for e in recent_executions if e.status == "completed")
            failed = sum(1 for e in recent_executions if e.status == "failed")
            
            # Get registered tasks count
            tasks = await uow.scheduler_tasks.list(filters={}, limit=1000)
            total_tasks = len(tasks)
            enabled_tasks = sum(1 for t in tasks if t.enabled)
            
            # Determine health status
            if total_recent == 0:
                status = "warning"
                message = "No recent task executions"
            elif failed > completed:
                status = "warning"
                message = f"High failure rate: {failed}/{total_recent} failed"
            elif running > 10:
                status = "warning"
                message = f"Many tasks running: {running} concurrent"
            else:
                status = "ok"
                message = "Scheduler is healthy"
            
            return {
                "ok": True,
                "data": {
                    "status": status,
                    "error_message": message if status != "ok" else None,
                    "details": {
                        "total_tasks": total_tasks,
                        "enabled_tasks": enabled_tasks,
                        "recent_executions": total_recent,
                        "running": running,
                        "completed": completed,
                        "failed": failed,
                        "lookback_minutes": lookback_minutes,
                    }
                },
                "error": None
            }
    
    except Exception as exc:
        logger.error("Scheduler health check failed: %s", exc)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "error_message": str(exc),
                "details": {}
            },
            "error": {"code": "check_failed", "message": str(exc)}
        }


async def tool_scheduler_check_stuck_tasks(threshold_minutes: int = 60) -> Dict[str, Any]:
    """Check for tasks that have been running too long.
    
    Args:
        threshold_minutes: Minutes threshold for stuck task detection
    
    Returns:
        Dict with ok, data, and error fields following tool contract
    """
    try:
        from aico.data.postgres.connection import get_session_factory
        from aico.data.uow import UnitOfWork
        
        # Use provided threshold_minutes parameter
        threshold_time = datetime.now(UTC) - timedelta(minutes=threshold_minutes)
        
        session_factory = await get_session_factory()
        
        async with UnitOfWork(session_factory) as uow:
            # Query running tasks
            executions = await uow.scheduler_task_executions.list(
                filters={"status": "running"},
                limit=100
            )
            
            # Find stuck tasks
            stuck_tasks = [
                {
                    "task_id": e.task_id,
                    "execution_id": e.execution_id,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "duration_minutes": int((datetime.now(UTC) - e.started_at).total_seconds() / 60) if e.started_at else 0
                }
                for e in executions
                if e.started_at and e.started_at < threshold_time
            ]
            
            if stuck_tasks:
                status = "warning"
                message = f"Found {len(stuck_tasks)} stuck tasks"
            else:
                status = "ok"
                message = "No stuck tasks detected"
            
            return {
                "ok": True,
                "data": {
                    "status": status,
                    "error_message": message if status != "ok" else None,
                    "details": {
                        "stuck_count": len(stuck_tasks),
                        "stuck_tasks": stuck_tasks[:5],  # Limit to 5 for brevity
                        "threshold_minutes": threshold_minutes,
                    }
                },
                "error": None
            }
    
    except Exception as exc:
        logger.error("Stuck task check failed: %s", exc)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "error_message": str(exc),
                "details": {}
            },
            "error": {"code": "check_failed", "message": str(exc)}
        }


def _register_scheduler_tools():
    """Register scheduler health monitoring tools."""
    registry = get_tool_registry()
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.scheduler.check_status",
            name="Scheduler Status Check",
            description="Check task scheduler health and recent execution status.",
            domain="scheduler",
            backend="database",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_scheduler_check_status,
        )
    )
    
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.scheduler.check_stuck_tasks",
            name="Stuck Tasks Check",
            description="Check for tasks that have been running longer than threshold.",
            domain="scheduler",
            backend="database",
            runtime_context="backend_service",
            capability_tags=["check_health", "query_database"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="small",
            default_timeout_seconds=5,
            handler=tool_scheduler_check_stuck_tasks,
        )
    )


# Register tools at import time
_register_scheduler_tools()
