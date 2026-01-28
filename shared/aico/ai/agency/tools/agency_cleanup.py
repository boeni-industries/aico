from __future__ import annotations

"""Agency maintenance tools for cleaning up execution history.

This module provides an atomic tool to clean up old Agency plan and step
executions in PostgreSQL according to a retention policy. It is intended to
be used by maintenance skills (e.g. maint.agency.cleanup_executions) and by
System Health / CLI flows.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Optional, List

from aico.core.config import ConfigurationManager, ConfigurationError
from aico.core.logging import get_logger
from aico.data.uow import UnitOfWork

from .registry import ToolDefinition, ToolParameter, ToolParameterType, get_tool_registry


logger = get_logger("shared.ai.agency.tools.maintenance.agency_cleanup")


async def tool_agency_postgres_cleanup_executions(
    session_factory: Any,
    max_age_days: Optional[int] = None,
    max_executions_per_plan: Optional[int] = None,
    min_keep_per_plan: int = 3,
    plan_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Atomic tool: clean up Agency execution history in PostgreSQL.

    This deletes rows from agency_plan_executions and agency_step_executions
    according to a retention policy. The policy can be passed explicitly via
    parameters, or defaults can be loaded from configuration.

    Returns a result dict with the standard tool contract:

        {
            "ok": bool,
            "data": {
                "plan_stats": { plan_id: {"total_executions", "kept", "deleted"} },
                "deleted_plan_executions": int,
                "deleted_step_executions": int,
            },
            "error": None | {"code", "message"},
        }
    """

    config = ConfigurationManager()
    config.initialize(lightweight=True)

    # IMPORTANT: agency.yaml is loaded under the 'agency' domain.
    # If the section is missing or empty, we fail loudly so misconfiguration
    # is not silently ignored.
    retention_cfg = config.get("agency.execution_retention", None)
    if not isinstance(retention_cfg, dict) or not retention_cfg:
        msg = (
            "Missing or empty configuration section 'agency.execution_retention'. "
            "Execution cleanup tool cannot determine retention policy."
        )
        logger.error("[TOOL_AGENCY_CLEANUP] %s", msg)
        # Raise a ConfigurationError so callers and logs see a clear failure.
        raise ConfigurationError(msg)

    if max_age_days is None:
        max_age_days = retention_cfg.get("max_age_days")
    if max_executions_per_plan is None:
        max_executions_per_plan = retention_cfg.get("max_executions_per_plan")
    if not min_keep_per_plan:
        min_keep_per_plan = retention_cfg.get("min_keep_per_plan", 3)

    cutoff: Optional[datetime] = None
    if max_age_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    deleted_plan_execs = 0
    deleted_step_execs = 0
    plan_stats: Dict[str, Dict[str, int]] = {}

    try:
        async with UnitOfWork(session_factory) as uow:
            repo = uow.agency_plan_executions

            # Fetch executions (optionally filtered by plan_id). We may need
            # to paginate in the future; for now this relies on typical
            # retention configs keeping the set bounded.
            filters: Dict[str, Any] = {}
            if plan_id:
                filters["plan_id"] = plan_id

            executions = await repo.list(filters=filters, limit=1000)

            # Group executions per plan, newest-first
            per_plan: Dict[str, List[Any]] = {}
            for exec_row in executions:
                pid = exec_row.plan_id
                per_plan.setdefault(pid, []).append(exec_row)

            for pid, exec_rows in per_plan.items():
                # Sort by created_at desc (fallback to updated_at)
                exec_rows_sorted = sorted(
                    exec_rows,
                    key=lambda e: getattr(e, "created_at", None) or getattr(e, "updated_at", None),
                    reverse=True,
                )

                total = len(exec_rows_sorted)
                keep_indices = set()

                # Always keep the most recent min_keep_per_plan
                for idx in range(min(min_keep_per_plan, total)):
                    keep_indices.add(idx)

                # Enforce max_executions_per_plan if set
                if max_executions_per_plan is not None:
                    for idx in range(max_executions_per_plan):
                        if idx < total:
                            keep_indices.add(idx)

                to_delete: List[Any] = []
                for idx, exec_row in enumerate(exec_rows_sorted):
                    if idx in keep_indices:
                        continue

                    if cutoff is not None:
                        created = getattr(exec_row, "created_at", None)
                        # created_at is stored as str in AgencyPlanExecution
                        if isinstance(created, str):
                            try:
                                created_dt = datetime.fromisoformat(created)
                            except Exception:
                                created_dt = None
                        else:
                            created_dt = created

                        if created_dt is not None and created_dt >= cutoff:
                            # Recent execution; skip even if over max_executions_per_plan
                            continue

                    to_delete.append(exec_row)

                # Perform deletions for this plan
                for exec_row in to_delete:
                    exec_id = exec_row.execution_id

                    # Delete step executions first to maintain referential integrity
                    step_repo = uow.agency_step_executions
                    step_execs = await step_repo.list(filters={"execution_id": exec_id}, limit=1000)
                    step_count = len(step_execs)
                    if not dry_run:
                        for s in step_execs:
                            await step_repo.delete(s.step_execution_id)

                    deleted_step_execs += step_count

                    # Delete the plan execution itself
                    if not dry_run:
                        await repo.delete(exec_id)
                    deleted_plan_execs += 1

                plan_stats[pid] = {
                    "total_executions": total,
                    "kept": total - len(to_delete),
                    "deleted": len(to_delete),
                }

            if not dry_run:
                await uow.commit()

        return {
            "ok": True,
            "data": {
                "plan_stats": plan_stats,
                "deleted_plan_executions": deleted_plan_execs,
                "deleted_step_executions": deleted_step_execs,
                "config": {
                    "max_age_days": max_age_days,
                    "max_executions_per_plan": max_executions_per_plan,
                    "min_keep_per_plan": min_keep_per_plan,
                    "plan_id": plan_id,
                    "dry_run": dry_run,
                },
            },
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error("[TOOL_AGENCY_CLEANUP] Execution cleanup failed: %s", exc)
        return {
            "ok": False,
            "data": {
                "plan_stats": plan_stats,
                "deleted_plan_executions": deleted_plan_execs,
                "deleted_step_executions": deleted_step_execs,
            },
            "error": {
                "code": "agency_cleanup_failed",
                "message": str(exc),
            },
        }


def _register_agency_cleanup_tools() -> None:
    """Register agency cleanup tools in the global ToolRegistry."""

    registry = get_tool_registry()

    registry.register_tool(
        ToolDefinition(
            tool_id="tool.agency.postgres.cleanup_executions",
            name="Agency Execution Cleanup (PostgreSQL)",
            description=(
                "Clean up Agency plan and step execution history in PostgreSQL "
                "according to the configured retention policy."
            ),
            domain="agency",
            backend="python",
            runtime_context="backend_service",
            capability_tags=["cleanup_history", "maintenance"],
            side_effect_tags=["writes_database", "deletes_history", "agency_internal"],
            safety_level="privileged",
            resource_profile="small",
            default_timeout_seconds=30,
            handler=tool_agency_postgres_cleanup_executions,
            parameters=[
                ToolParameter(
                    name="max_age_days",
                    type=ToolParameterType.INTEGER,
                    description="Delete executions older than this many days (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="max_executions_per_plan",
                    type=ToolParameterType.INTEGER,
                    description="Maximum executions to keep per plan (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="min_keep_per_plan",
                    type=ToolParameterType.INTEGER,
                    description="Minimum executions to always keep per plan",
                    required=False,
                    default=3,
                ),
                ToolParameter(
                    name="plan_id",
                    type=ToolParameterType.STRING,
                    description="If set, restrict cleanup to this plan_id",
                    required=False,
                ),
                ToolParameter(
                    name="dry_run",
                    type=ToolParameterType.BOOLEAN,
                    description="If true, report what would be deleted without deleting",
                    required=False,
                    default=False,
                ),
            ],
        )
    )


_register_agency_cleanup_tools()
