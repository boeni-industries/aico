"""Agency Metrics and Health Monitoring Tools

Atomic tools for monitoring agency behaviour and detecting issues.
"""

from __future__ import annotations

from datetime import datetime, UTC, timedelta
from typing import Dict, Any

from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork
from .registry import ToolDefinition, get_tool_registry


logger = get_logger("shared.ai.agency.tools.agency_metrics")


async def tool_agency_metrics_snapshot(session_factory: Any) -> Dict[str, Any]:
    """Atomic tool: snapshot current agency metrics (goals, plans, reflections).
    
    Queries PostgreSQL to get counts and health indicators for agency components.
    """
    start = datetime.now(UTC)
    try:
        async with UnitOfWork(session_factory) as uow:
            # Count active goals using get_active_goals_for_user
            # Since we don't have a specific user_id, we'll use count with status filter
            active_goals = await uow.goals.count(filters={"status": "active"})
            
            # Count active intentions
            active_intentions_count = 0
            if hasattr(uow, "intentions"):
                # Use list with status filter instead of list_active
                active_intentions = await uow.intentions.list(filters={"status": "active"}, limit=1000)
                active_intentions_count = len(active_intentions)
            
            # Count recent reflections (last 24 hours)
            recent_reflections = 0
            if hasattr(uow, "lessons"):
                cutoff = datetime.now(UTC) - timedelta(hours=24)
                lessons = await uow.lessons.list(filters={"status": "active"}, limit=1000)
                recent_reflections = len([l for l in lessons if getattr(l, "created_at", None) and l.created_at >= cutoff])
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        return {
            "ok": True,
            "data": {
                "status": "ok",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "active_goals": active_goals,
                    "active_intentions": active_intentions_count,
                    "reflections_24h": recent_reflections,
                    "snapshot_time": datetime.now(UTC).isoformat(),
                },
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[TOOL_AGENCY_METRICS] Metrics snapshot failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {
                "code": "agency_metrics_snapshot_failed",
                "message": str(exc),
            },
        }


async def tool_agency_detect_stalled_plans(session_factory: Any) -> Dict[str, Any]:
    """Atomic tool: detect plans that have been in progress for too long.
    
    Identifies plans that may be stuck or experiencing issues.
    """
    start = datetime.now(UTC)
    try:
        async with UnitOfWork(session_factory) as uow:
            # Define "stalled" as in_progress for more than 1 hour
            stall_threshold = datetime.now(UTC) - timedelta(hours=1)
            
            stalled_plans = []
            if hasattr(uow, "plans"):
                # Get all active plans using list with status filter
                plans = await uow.plans.list(filters={"status": "active"}, limit=1000)
                
                for plan in plans:
                    # Check if plan has been in progress too long
                    if plan.status == "in_progress":
                        if plan.started_at and plan.started_at < stall_threshold:
                            stalled_plans.append({
                                "plan_id": str(plan.id),
                                "goal_id": str(plan.goal_id) if plan.goal_id else None,
                                "started_at": plan.started_at.isoformat(),
                                "duration_hours": (datetime.now(UTC) - plan.started_at).total_seconds() / 3600,
                            })
        
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        stalled_count = len(stalled_plans)
        
        return {
            "ok": True,
            "data": {
                "status": "ok" if stalled_count == 0 else "warning",
                "latency_ms": latency_ms,
                "error_message": None,
                "details": {
                    "stalled_count": stalled_count,
                    "stalled_plans": stalled_plans[:10],  # Limit to first 10
                    "threshold_hours": 1,
                },
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[TOOL_AGENCY_METRICS] Stalled plan detection failed: %s", exc)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return {
            "ok": False,
            "data": {
                "status": "error",
                "latency_ms": latency_ms,
                "error_message": str(exc),
                "details": {},
            },
            "error": {
                "code": "agency_stalled_plan_detection_failed",
                "message": str(exc),
            },
        }


def _register_agency_metrics_tools() -> None:
    """Register agency metrics tools in the global ToolRegistry."""
    registry = get_tool_registry()
    
    # Metrics snapshot
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.agency.metrics.snapshot",
            name="Agency Metrics Snapshot",
            description="Snapshot current agency metrics (goals, plans, reflections).",
            domain="agency",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "measure_metrics"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=5,
            handler=tool_agency_metrics_snapshot,
        )
    )
    
    # Stalled plan detection
    registry.register_tool(
        ToolDefinition(
            tool_id="tool.agency.detect_stalled_plans",
            name="Detect Stalled Plans",
            description="Detect plans that have been in progress for too long.",
            domain="agency",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["check_health", "detect_issues"],
            side_effect_tags=["reads_database"],
            safety_level="low",
            resource_profile="tiny",
            default_timeout_seconds=5,
            handler=tool_agency_detect_stalled_plans,
        )
    )


# Register tools at import time
_register_agency_metrics_tools()
