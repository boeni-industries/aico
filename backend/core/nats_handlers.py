"""
NATS request handlers for core services.

Handles gateway→core requests via NATS request/reply pattern.
"""

import json
import os
import uuid
import time
import asyncio
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional
from aico.core.logging import get_logger
from google.protobuf.struct_pb2 import Struct
from opentelemetry import trace
from backend.core.agency_nats_handlers import AgencyNATSHandlers
from backend.core.system_nats_handlers import SystemNATSHandlers

logger = get_logger("backend.core.nats_handlers")
tracer = trace.get_tracer(__name__)


def trace_nats_handler(subject: str):
    """Decorator to add OpenTelemetry tracing to NATS handlers"""
    def decorator(func):
        async def wrapper(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
            with tracer.start_as_current_span(
                f"nats.handle.{subject}",
                kind=trace.SpanKind.SERVER,
                attributes={
                    "messaging.system": "nats",
                    "messaging.destination": subject,
                    "messaging.operation": "handle",
                }
            ) as span:
                try:
                    result = await func(self, request_data)
                    if result.get("error"):
                        span.set_status(trace.Status(trace.StatusCode.ERROR, result.get("message", "Unknown error")))
                        span.set_attribute("error.type", result.get("error"))
                    else:
                        span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


class CoreNATSHandlers:
    """NATS request handlers for core services"""
    
    def __init__(self, service_container):
        self.container = service_container
        self.logger = logger
        self.agency_handlers = AgencyNATSHandlers(service_container)
        
        # Initialize system health handlers (will be lazy-loaded when needed)
        self.system_handlers = None
        self._system_handlers_start_time = None

        # Guard against duplicate subscription setup. In some startup/reconnect flows,
        # setup_handlers() can be invoked multiple times; without a guard, each call
        # adds another subscription and causes handlers (e.g. backup.create) to run
        # multiple times per single request.
        self._setup_lock = asyncio.Lock()
        self._setup_in_progress = False
        self._setup_completed = False
    
    async def _get_system_handlers(self):
        """Lazy-load system handlers when first needed."""
        if self.system_handlers is None:
            import time
            if self._system_handlers_start_time is None:
                self._system_handlers_start_time = time.time()
            
            from aico.data.postgres.connection import get_session_factory
            session_factory = await get_session_factory()
            self.system_handlers = SystemNATSHandlers(
                self.container, 
                session_factory, 
                self._system_handlers_start_time
            )
        return self.system_handlers
    
    @trace_nats_handler("scheduler.status")
    async def handle_scheduler_status_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler status request from gateway"""
        try:
            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {
                    "error": "SCHEDULER_NOT_AVAILABLE",
                    "message": "Task scheduler not available"
                }
            
            status = scheduler.get_status()
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduler status: {e}")
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }

    async def handle_scheduler_task_get_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific task configuration."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task = await scheduler_service.get_task(task_id)

            if not task:
                return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}

            config_value = getattr(task, "config", None)
            if isinstance(config_value, str):
                try:
                    config_value = json.loads(config_value)
                except Exception:
                    pass

            created_at = getattr(task, "created_at", None)
            updated_at = getattr(task, "updated_at", None)

            return {
                "task_id": task.task_id,
                "task_class": task.task_class,
                "schedule": task.schedule,
                "config": config_value,
                "enabled": bool(task.enabled),
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            }
        except Exception as e:
            self.logger.error(f"Failed to get scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_create_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scheduled task."""
        try:
            task_id = request_data.get("task_id")
            task_class = request_data.get("task_class")
            schedule = request_data.get("schedule")
            enabled = bool(request_data.get("enabled", True))
            config = request_data.get("config")

            if not task_id or not task_class or not schedule:
                return {"error": "VALIDATION_ERROR", "message": "task_id, task_class, and schedule are required"}

            from datetime import datetime, UTC
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                existing = await scheduler_service.get_task(task_id)
                if existing:
                    return {"error": "TASK_ALREADY_EXISTS", "message": f"Task already exists: {task_id}"}

                task_data = {
                    "task_id": task_id,
                    "task_class": task_class,
                    "schedule": schedule,
                    "config": json.dumps(config) if isinstance(config, (dict, list)) else config,
                    "enabled": enabled,
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
                created = await scheduler_service.create_task(task_data)

            # Best-effort: update runtime next_run cache
            try:
                scheduler = self.container.get_service("task_scheduler")
                if scheduler and enabled and schedule:
                    next_run = scheduler.cron_parser.next_run_time(schedule)
                    if next_run:
                        scheduler.next_run_times[task_id] = next_run
            except Exception:
                pass

            config_value = getattr(created, "config", None)
            if isinstance(config_value, str):
                try:
                    config_value = json.loads(config_value)
                except Exception:
                    pass

            return {
                "task_id": created.task_id,
                "task_class": created.task_class,
                "schedule": created.schedule,
                "config": config_value,
                "enabled": bool(created.enabled),
                "created_at": getattr(created, "created_at", None).isoformat() if getattr(created, "created_at", None) else None,
                "updated_at": getattr(created, "updated_at", None).isoformat() if getattr(created, "updated_at", None) else None,
            }
        except Exception as e:
            self.logger.error(f"Failed to create scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_update_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a scheduled task."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            new_schedule = request_data.get("schedule")
            new_config = request_data.get("config")
            enabled = request_data.get("enabled")

            from datetime import datetime, UTC
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                existing = await scheduler_service.get_task(task_id)
                if not existing:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}

                task_data = {
                    "task_id": task_id,
                    "task_class": existing.task_class,
                    "schedule": new_schedule or existing.schedule,
                    "config": json.dumps(new_config) if isinstance(new_config, (dict, list)) else (new_config if new_config is not None else existing.config),
                    "enabled": bool(existing.enabled) if enabled is None else bool(enabled),
                    "created_at": existing.created_at,
                    "updated_at": datetime.now(UTC),
                }
                updated = await scheduler_service.update_task(task_data)

            # Best-effort: update runtime next_run cache
            try:
                scheduler = self.container.get_service("task_scheduler")
                if scheduler:
                    if bool(getattr(updated, "enabled", True)) and getattr(updated, "schedule", None):
                        next_run = scheduler.cron_parser.next_run_time(updated.schedule)
                        if next_run:
                            scheduler.next_run_times[task_id] = next_run
                    else:
                        scheduler.next_run_times.pop(task_id, None)
            except Exception:
                pass

            config_value = getattr(updated, "config", None)
            if isinstance(config_value, str):
                try:
                    config_value = json.loads(config_value)
                except Exception:
                    pass

            created_at = getattr(updated, "created_at", None)
            updated_at = getattr(updated, "updated_at", None)

            return {
                "task_id": updated.task_id,
                "task_class": updated.task_class,
                "schedule": updated.schedule,
                "config": config_value,
                "enabled": bool(updated.enabled),
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            }
        except Exception as e:
            self.logger.error(f"Failed to update scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_delete_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a scheduled task."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                deleted = await scheduler_service.delete_task(task_id)
                if not deleted:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}

            try:
                scheduler = self.container.get_service("task_scheduler")
                if scheduler:
                    scheduler.next_run_times.pop(task_id, None)
            except Exception:
                pass

            return {"success": True, "message": f"Task {task_id} deleted successfully"}
        except Exception as e:
            self.logger.error(f"Failed to delete scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_enable_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enable a scheduled task."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                ok = await scheduler_service.enable_task(task_id)
                if not ok:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}
                task = await scheduler_service.get_task(task_id)

            # Best-effort runtime update
            try:
                scheduler = self.container.get_service("task_scheduler")
                if scheduler and task and getattr(task, "schedule", None):
                    next_run = scheduler.cron_parser.next_run_time(task.schedule)
                    if next_run:
                        scheduler.next_run_times[task_id] = next_run
            except Exception:
                pass

            return {"success": True, "message": f"Task {task_id} enabled successfully"}
        except Exception as e:
            self.logger.error(f"Failed to enable scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_disable_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Disable a scheduled task."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                ok = await scheduler_service.disable_task(task_id)
                if not ok:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}

            try:
                scheduler = self.container.get_service("task_scheduler")
                if scheduler:
                    scheduler.next_run_times.pop(task_id, None)
            except Exception:
                pass

            return {"success": True, "message": f"Task {task_id} disabled successfully"}
        except Exception as e:
            self.logger.error(f"Failed to disable scheduler task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_status_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get task status (enabled, last execution, next_run_time, is_running)."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task = await scheduler_service.get_task(task_id)
                if not task:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}

                history = await scheduler_service.get_task_executions(task_id, limit=1)

            last_execution = None
            if history:
                exec_data = history[0]
                last_execution = {
                    "execution_id": exec_data.execution_id,
                    "status": exec_data.status,
                    "started_at": exec_data.started_at.isoformat() if getattr(exec_data, "started_at", None) else None,
                    "completed_at": exec_data.completed_at.isoformat() if getattr(exec_data, "completed_at", None) else None,
                    "result": exec_data.result,
                    "error_message": exec_data.error_message,
                    "duration_seconds": exec_data.duration_seconds,
                }

            scheduler = self.container.get_service("task_scheduler")
            next_run_time = None
            is_running = False
            if scheduler is not None:
                if bool(getattr(task, "enabled", False)) and task_id in getattr(scheduler, "next_run_times", {}):
                    next_run_time = scheduler.next_run_times[task_id].isoformat()
                is_running = task_id in getattr(scheduler.task_executor, "running_tasks", {})

            return {
                "task_id": task_id,
                "enabled": bool(task.enabled),
                "last_execution": last_execution,
                "next_run_time": next_run_time,
                "is_running": bool(is_running),
            }
        except Exception as e:
            self.logger.error(f"Failed to get task status: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get execution history for a task."""
        try:
            task_id = request_data.get("task_id")
            limit = int(request_data.get("limit", 50))
            limit = max(1, min(limit, 1000))
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                task = await scheduler_service.get_task(task_id)
                if not task:
                    return {"error": "TASK_NOT_FOUND", "message": f"Task not found: {task_id}"}
                history = await scheduler_service.get_task_executions(task_id, limit=limit)

            executions = []
            for exec_data in history:
                executions.append(
                    {
                        "execution_id": exec_data.execution_id,
                        "status": exec_data.status,
                        "started_at": exec_data.started_at.isoformat() if getattr(exec_data, "started_at", None) else None,
                        "completed_at": exec_data.completed_at.isoformat() if getattr(exec_data, "completed_at", None) else None,
                        "result": exec_data.result,
                        "error_message": exec_data.error_message,
                        "duration_seconds": exec_data.duration_seconds,
                    }
                )

            return {"task_id": task_id, "executions": executions, "total_count": len(executions)}
        except Exception as e:
            self.logger.error(f"Failed to get task history: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_executions_range_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get executions in a given time range (ISO timestamps)."""
        try:
            start_time = request_data.get("start_time")
            end_time = request_data.get("end_time")
            if not start_time or not end_time:
                return {"error": "VALIDATION_ERROR", "message": "start_time and end_time are required"}

            limit = int(request_data.get("limit", 500))
            limit = max(1, min(limit, 2000))

            from datetime import datetime

            start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                all_executions = await scheduler_service.get_recent_executions(limit=10000)

            executions = [
                e
                for e in all_executions
                if getattr(e, "started_at", None) and start_dt <= e.started_at <= end_dt
            ]

            executions = executions[:limit]

            executions_response = []
            for exec_data in executions:
                executions_response.append(
                    {
                        "task_id": exec_data.task_id,
                        "execution_id": exec_data.execution_id,
                        "status": exec_data.status,
                        "started_at": exec_data.started_at.isoformat() if getattr(exec_data, "started_at", None) else None,
                        "completed_at": exec_data.completed_at.isoformat() if getattr(exec_data, "completed_at", None) else None,
                        "error_message": exec_data.error_message,
                        "duration_seconds": exec_data.duration_seconds,
                    }
                )

            return {
                "executions": executions_response,
                "total_count": len(executions_response),
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
        except Exception as e:
            self.logger.error(f"Failed to get executions in range: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_executions_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """List executions in a time range with cursor pagination."""
        try:
            start_time = request_data.get("start_time")
            end_time = request_data.get("end_time")
            if not start_time or not end_time:
                return {"error": "VALIDATION_ERROR", "message": "start_time and end_time are required"}

            limit = int(request_data.get("limit", 200))
            limit = max(1, min(limit, 500))

            cursor_started_at_raw = request_data.get("cursor_started_at")
            cursor_execution_id = request_data.get("cursor_execution_id")

            task_id = request_data.get("task_id")
            status = request_data.get("status")
            include_acknowledged = bool(request_data.get("include_acknowledged", True))

            from datetime import datetime

            start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))

            cursor_started_at = None
            if cursor_started_at_raw:
                cursor_started_at = datetime.fromisoformat(str(cursor_started_at_raw).replace("Z", "+00:00"))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                executions = await scheduler_service.list_executions_in_range_cursor(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    limit=limit,
                    cursor_started_at=cursor_started_at,
                    cursor_execution_id=cursor_execution_id,
                    task_id=task_id,
                    status=status,
                    include_acknowledged=include_acknowledged,
                )

            items = []
            for exec_data in executions:
                items.append(
                    {
                        "task_id": exec_data.task_id,
                        "execution_id": exec_data.execution_id,
                        "status": exec_data.status,
                        "started_at": exec_data.started_at.isoformat() if getattr(exec_data, "started_at", None) else None,
                        "completed_at": exec_data.completed_at.isoformat() if getattr(exec_data, "completed_at", None) else None,
                        "error_message": exec_data.error_message,
                        "duration_seconds": exec_data.duration_seconds,
                        "acknowledged": bool(getattr(exec_data, "acknowledged", False)),
                    }
                )

            next_cursor_started_at = None
            next_cursor_execution_id = None
            if items:
                last = items[-1]
                next_cursor_started_at = last.get("started_at")
                next_cursor_execution_id = last.get("execution_id")

            return {
                "items": items,
                "next_cursor_started_at": next_cursor_started_at,
                "next_cursor_execution_id": next_cursor_execution_id,
                "has_more": bool(len(items) == limit),
                "limit": limit,
                "start_time": start_time,
                "end_time": end_time,
            }
        except Exception as e:
            self.logger.error(f"Failed to list executions: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_execution_get_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a single execution by execution_id."""
        try:
            execution_id = request_data.get("execution_id")
            if not execution_id:
                return {"error": "VALIDATION_ERROR", "message": "execution_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                execution = await scheduler_service.get_execution_by_execution_id(str(execution_id))

            if not execution:
                return {"error": "EXECUTION_NOT_FOUND", "message": f"Execution not found: {execution_id}"}

            return {
                "task_id": execution.task_id,
                "execution_id": execution.execution_id,
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if getattr(execution, "started_at", None) else None,
                "completed_at": execution.completed_at.isoformat() if getattr(execution, "completed_at", None) else None,
                "result": execution.result,
                "error_message": execution.error_message,
                "duration_seconds": execution.duration_seconds,
                "acknowledged": bool(getattr(execution, "acknowledged", False)),
            }
        except Exception as e:
            self.logger.error(f"Failed to get execution: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_executions_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get execution stats buckets in a time range."""
        try:
            start_time = request_data.get("start_time")
            end_time = request_data.get("end_time")
            if not start_time or not end_time:
                return {"error": "VALIDATION_ERROR", "message": "start_time and end_time are required"}

            bucket = str(request_data.get("bucket") or "hour")
            if bucket not in {"hour", "day"}:
                return {"error": "VALIDATION_ERROR", "message": "bucket must be 'hour' or 'day'"}

            task_id = request_data.get("task_id")

            from datetime import datetime

            start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                rows = await scheduler_service.get_execution_stats_in_range(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    bucket=bucket,
                    task_id=task_id,
                )

            items = []
            for row in rows:
                bucket_start = row.get("bucket_start")
                items.append(
                    {
                        "bucket_start": bucket_start.isoformat() if hasattr(bucket_start, "isoformat") else bucket_start,
                        "status": row.get("status"),
                        "count": int(row.get("count") or 0),
                    }
                )

            return {
                "items": items,
                "bucket": bucket,
                "start_time": start_time,
                "end_time": end_time,
                "task_id": task_id,
            }
        except Exception as e:
            self.logger.error(f"Failed to get execution stats: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_runs_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """List planned runs (run ledger) in a time range."""
        try:
            start_time = request_data.get("start_time")
            end_time = request_data.get("end_time")
            if not start_time or not end_time:
                return {"error": "VALIDATION_ERROR", "message": "start_time and end_time are required"}

            limit = int(request_data.get("limit", 200))
            limit = max(1, min(limit, 500))
            offset = int(request_data.get("offset", 0))
            offset = max(0, offset)

            task_id = request_data.get("task_id")
            state = request_data.get("state")
            tenant_id = request_data.get("tenant_id")

            from datetime import datetime

            start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            filters: Dict[str, Any] = {
                "scheduled_for_from": start_dt,
                "scheduled_for_to": end_dt,
            }
            if task_id:
                filters["task_id"] = task_id
            if state:
                filters["state"] = state
            if tenant_id is not None:
                filters["tenant_id"] = tenant_id

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                runs = await scheduler_service.list_runs(filters=filters, limit=limit, offset=offset)

                count_fn = getattr(uow.scheduler_run_ledger, "count", None)
                if count_fn is None:
                    total_count = len(runs)
                else:
                    total_count = await count_fn(filters)

            items: List[Dict[str, Any]] = []
            for run in runs:
                items.append(
                    {
                        "id": int(run.id),
                        "task_id": run.task_id,
                        "run_key": run.run_key,
                        "tenant_id": getattr(run, "tenant_id", None),
                        "scheduled_for": run.scheduled_for.isoformat(),
                        "planned_at": run.planned_at.isoformat() if getattr(run, "planned_at", None) else None,
                        "state": run.state,
                        "enqueued_at": run.enqueued_at.isoformat() if getattr(run, "enqueued_at", None) else None,
                        "started_at": run.started_at.isoformat() if getattr(run, "started_at", None) else None,
                        "completed_at": run.completed_at.isoformat() if getattr(run, "completed_at", None) else None,
                        "execution_id": getattr(run, "execution_id", None),
                        "reason_code": getattr(run, "reason_code", None),
                    }
                )

            return {
                "items": items,
                "total_count": int(total_count),
                "limit": limit,
                "offset": offset,
                "start_time": start_time,
                "end_time": end_time,
            }
        except Exception as e:
            self.logger.error(f"Failed to list runs: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_run_get_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a single run ledger row by numeric run_id."""
        try:
            run_id = request_data.get("run_id")
            if not run_id:
                return {"error": "VALIDATION_ERROR", "message": "run_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                run = await scheduler_service.get_run(str(run_id))

            if not run:
                return {"error": "RUN_NOT_FOUND", "message": f"Run not found: {run_id}"}

            return {
                "id": int(run.id),
                "task_id": run.task_id,
                "run_key": run.run_key,
                "tenant_id": getattr(run, "tenant_id", None),
                "scheduled_for": run.scheduled_for.isoformat(),
                "planned_at": run.planned_at.isoformat() if getattr(run, "planned_at", None) else None,
                "state": run.state,
                "enqueued_at": run.enqueued_at.isoformat() if getattr(run, "enqueued_at", None) else None,
                "started_at": run.started_at.isoformat() if getattr(run, "started_at", None) else None,
                "completed_at": run.completed_at.isoformat() if getattr(run, "completed_at", None) else None,
                "execution_id": getattr(run, "execution_id", None),
                "reason_code": getattr(run, "reason_code", None),
                "reason_detail": getattr(run, "reason_detail", None),
            }
        except Exception as e:
            self.logger.error(f"Failed to get run: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_runs_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get run ledger stats buckets in a time range."""
        try:
            start_time = request_data.get("start_time")
            end_time = request_data.get("end_time")
            if not start_time or not end_time:
                return {"error": "VALIDATION_ERROR", "message": "start_time and end_time are required"}

            bucket = str(request_data.get("bucket") or "hour")
            if bucket not in {"hour", "day"}:
                return {"error": "VALIDATION_ERROR", "message": "bucket must be 'hour' or 'day'"}

            task_id = request_data.get("task_id")
            tenant_id = request_data.get("tenant_id")

            from datetime import datetime

            start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                rows = await scheduler_service.get_run_stats_in_range(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    bucket=bucket,
                    task_id=task_id,
                    tenant_id=tenant_id,
                )

            items: List[Dict[str, Any]] = []
            for row in rows:
                bucket_start = row.get("bucket_start")
                items.append(
                    {
                        "bucket_start": bucket_start.isoformat() if hasattr(bucket_start, "isoformat") else bucket_start,
                        "state": row.get("state"),
                        "count": int(row.get("count") or 0),
                    }
                )

            return {
                "items": items,
                "bucket": bucket,
                "start_time": start_time,
                "end_time": end_time,
                "task_id": task_id,
                "tenant_id": tenant_id,
            }
        except Exception as e:
            self.logger.error(f"Failed to get run stats: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_unacknowledged_failures_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get unacknowledged failed executions."""
        try:
            task_id = request_data.get("task_id")
            limit = int(request_data.get("limit", 100))
            limit = max(1, min(limit, 10000))

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                executions = await scheduler_service.get_unacknowledged_failures(task_id=task_id, limit=limit)

            executions_response = []
            for exec_data in executions:
                executions_response.append(
                    {
                        "execution_id": exec_data.execution_id,
                        "task_id": exec_data.task_id,
                        "status": exec_data.status,
                        "started_at": exec_data.started_at.isoformat() if getattr(exec_data, "started_at", None) else None,
                        "completed_at": exec_data.completed_at.isoformat() if getattr(exec_data, "completed_at", None) else None,
                        "error_message": exec_data.error_message,
                        "duration_seconds": exec_data.duration_seconds,
                    }
                )

            return {"executions": executions_response, "total_count": len(executions_response), "task_id": task_id}
        except Exception as e:
            self.logger.error(f"Failed to get unacknowledged failures: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_acknowledge_execution_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Acknowledge a single execution."""
        try:
            execution_id = request_data.get("execution_id")
            if not execution_id:
                return {"error": "EXECUTION_ID_REQUIRED", "message": "execution_id is required"}

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                success = await scheduler_service.acknowledge_execution(execution_id)

            if not success:
                return {"error": "EXECUTION_NOT_FOUND", "message": f"Execution {execution_id} not found"}

            return {"success": True, "message": f"Execution {execution_id} acknowledged successfully"}
        except Exception as e:
            self.logger.error(f"Failed to acknowledge execution: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_acknowledge_all_failed_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Acknowledge all failed executions."""
        try:
            task_id = request_data.get("task_id")

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                count = await scheduler_service.acknowledge_all_failed(task_id=task_id)

            if task_id:
                return {"success": True, "message": f"Acknowledged {count} failed executions for task {task_id}"}
            return {"success": True, "message": f"Acknowledged {count} failed executions across all tasks"}
        except Exception as e:
            self.logger.error(f"Failed to acknowledge all failed executions: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}

    async def handle_scheduler_task_trigger_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a task execution."""
        try:
            task_id = request_data.get("task_id")
            if not task_id:
                return {"error": "TASK_ID_REQUIRED", "message": "task_id is required"}

            scheduler = self.container.get_service("task_scheduler")
            if scheduler is None:
                return {"error": "SCHEDULER_NOT_AVAILABLE", "message": "Task scheduler not available"}

            result = await scheduler.trigger_task(task_id)

            return {
                "success": bool(getattr(result, "success", False)),
                "message": getattr(result, "message", ""),
                "execution_id": None,
                "data": getattr(result, "data", None),
            }
        except Exception as e:
            self.logger.error(f"Failed to trigger task: {e}", exc_info=True)
            return {"error": "SCHEDULER_ERROR", "message": str(e)}
    
    async def handle_scheduler_tasks_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler tasks list request from gateway"""
        try:
            enabled_only = request_data.get("enabled_only", False)

            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                filters: Dict[str, Any] = {"enabled": True} if enabled_only else {}
                task_models = await scheduler_service.list_tasks(filters=filters)

            tasks: list[dict] = []
            for task in task_models:
                config_value = getattr(task, "config", None)
                if isinstance(config_value, str):
                    try:
                        config_value = json.loads(config_value)
                    except Exception:
                        # Keep original string if it is not valid JSON
                        config_value = config_value

                created_at = getattr(task, "created_at", None)
                updated_at = getattr(task, "updated_at", None)

                tasks.append(
                    {
                        "task_id": task.task_id,
                        "task_class": task.task_class,
                        "schedule": task.schedule,
                        "config": config_value,
                        "enabled": bool(task.enabled),
                        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
                    }
                )

            return {"tasks": tasks, "total_count": len(tasks)}
            
        except Exception as e:
            self.logger.error(f"Failed to list scheduler tasks: {e}", exc_info=True)
            return {
                "error": "SCHEDULER_ERROR",
                "message": str(e)
            }
    
    async def handle_emotion_current_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle current emotion state request from gateway"""
        try:
            # Get emotion engine service
            emotion_engine = self.container.get_service("emotion_engine")
            if emotion_engine is None:
                return {
                    "error": "EMOTION_ENGINE_UNAVAILABLE",
                    "message": "Emotion engine unavailable"
                }
            
            # Get current emotional state from engine
            current_state = emotion_engine.current_state
            
            if current_state is None:
                return {
                    "error": "EMOTION_STATE_NOT_AVAILABLE",
                    "message": "No emotional state available"
                }
            
            # Convert to response format matching EmotionStateResponse schema
            return {
                "timestamp": current_state.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "primary": current_state.subjective_feeling.value,
                "confidence": current_state.intensity,
                "valence": current_state.mood_valence,
                "arousal": current_state.mood_arousal,
                "dominance": 0.5  # Default neutral dominance (not yet implemented in CPM)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get current emotion: {e}", exc_info=True)
            return {
                "error": "EMOTION_ENGINE_ERROR",
                "message": str(e)
            }
    
    async def handle_emotion_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emotion history request from gateway"""
        try:
            # Extract query params
            limit = request_data.get("limit", 10)
            hours = request_data.get("hours", 24)
            
            # Get emotion engine service
            emotion_engine = self.container.get_service("emotion_engine")
            if emotion_engine is None:
                return {
                    "error": "EMOTION_ENGINE_UNAVAILABLE",
                    "message": "Emotion engine unavailable"
                }
            
            # Get emotion state history from engine
            history = await emotion_engine.get_state_history(limit=limit, hours=hours)
            self.logger.info(f"🎭 Emotion engine returned {len(history)} states (limit={limit}, hours={hours})")
            
            # Add metadata about data age and diversity
            metadata = {}
            if history:
                from datetime import datetime, UTC
                
                # Check data age
                try:
                    # Robust timestamp parsing to handle malformed variants
                    ts_str = history[-1]["timestamp"]
                    # Handle double +00:00 suffix and other malformed variants
                    if "+00:00+00:00" in ts_str:
                        ts_str = ts_str.replace("+00:00+00:00", "+00:00")
                    if ts_str.endswith("+00:00Z"):
                        ts_str = ts_str[:-1]
                    if ts_str.endswith("Z"):
                        ts_str = ts_str.replace("Z", "+00:00")
                    
                    last_timestamp = datetime.fromisoformat(ts_str)
                    age_hours = (datetime.now(UTC) - last_timestamp).total_seconds() / 3600
                    metadata["oldest_record_age_hours"] = age_hours
                    metadata["newest_record_timestamp"] = history[-1]["timestamp"]
                    metadata["oldest_record_timestamp"] = history[0]["timestamp"]
                except Exception as e:
                    self.logger.warning(f"Could not parse timestamp for metadata: {e}")
                
                # Check diversity
                unique_feelings = len(set(h.get('feeling') for h in history))
                metadata["unique_feelings_count"] = unique_feelings
                
                self.logger.info(f"🎭 Data diversity: {unique_feelings} unique feelings, newest record age: {metadata.get('oldest_record_age_hours', 0):.1f}h")
            
            return {
                "count": len(history), 
                "history": history,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get emotion history: {e}", exc_info=True)
            return {
                "error": "EMOTION_ENGINE_ERROR",
                "message": str(e)
            }
    
    async def handle_memory_semantic_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle semantic memory stats request from gateway"""
        try:
            from aico.ai import ai_registry
            from sqlalchemy import select, func, text
            from aico.data.tables import conversation_segments
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                return {
                    "error": "MEMORY_MANAGER_NOT_INITIALIZED",
                    "message": "Memory manager not initialized"
                }
            
            if not hasattr(memory_manager, '_semantic_store'):
                return {
                    "error": "SEMANTIC_MEMORY_NOT_INITIALIZED",
                    "message": "Semantic memory not initialized"
                }
            
            # Use exact same logic as original router.py - query database directly
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                stmt = select(func.count()).select_from(conversation_segments)
                total_vectors = (await uow_instance._session.execute(stmt)).scalar() or 0

                # Estimate storage size using Postgres relation size (includes table + indexes)
                index_size_mb = 0.0
                try:
                    size_stmt = text("SELECT pg_total_relation_size('aico_core.conversation_segments')")
                    size_bytes = (await uow_instance._session.execute(size_stmt)).scalar() or 0
                    index_size_mb = float(size_bytes) / (1024.0 * 1024.0)
                except Exception:
                    # If size query fails, keep 0 and fall back below
                    index_size_mb = 0.0

                # Guard: avoid 0 MB when vectors exist (Studio derives per-MB metrics)
                if int(total_vectors) > 0 and index_size_mb <= 0.0:
                    # Rough lower-bound estimate: vector payload only (768 float32)
                    index_size_mb = max(0.01, (int(total_vectors) * 768 * 4) / (1024.0 * 1024.0))
                
                collections = [
                    {"name": "conversation_segments", "count": int(total_vectors), "dimension": 768}
                ]
                
                return {
                    "total_vectors": int(total_vectors),
                    "collections": collections,
                    "index_size_mb": float(index_size_mb),
                    "avg_retrieval_latency_ms": 0.0,
                    "retrieval_quality_percent": 0.0
                }
            
        except Exception as e:
            self.logger.error(f"Failed to get semantic memory stats: {e}", exc_info=True)
            return {
                "error": "SEMANTIC_MEMORY_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_memory_working_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle working memory stats request from gateway"""
        try:
            from aico.ai import ai_registry
            
            memory_manager = ai_registry.get("memory")
            if not memory_manager:
                return {
                    "error": "MEMORY_MANAGER_NOT_INITIALIZED",
                    "message": "Memory manager not initialized"
                }
            
            if not hasattr(memory_manager, '_working_store'):
                return {
                    "error": "WORKING_MEMORY_NOT_INITIALIZED",
                    "message": "Working memory not initialized"
                }
            
            working_store = memory_manager._working_store
            stats = await working_store.get_stats()
            
            # Use exact same logic as original router.py
            active_items = stats.get('active_items', 0)
            capacity = stats.get('capacity', max(10000, int(active_items) * 2 if isinstance(active_items, int) else 10000))
            utilization_percent = stats.get('utilization_percent')
            if utilization_percent is None:
                utilization_percent = (active_items / capacity) * 100 if capacity else 0.0
            
            return {
                "active_items": active_items,
                "capacity": capacity,
                "utilization_percent": float(utilization_percent),
                "ttl_utilization_percent": float(stats.get('ttl_utilization_percent', utilization_percent)),
                "eviction_rate_per_min": float(stats.get('eviction_rate_per_min', 0.0)),
                "recent_activity": stats.get('recent_activity', [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get working memory stats: {e}", exc_info=True)
            return {
                "error": "WORKING_MEMORY_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_kg_stats_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG stats request from gateway - matches original router.py logic"""
        try:
            user_id = request_data.get("user_id")
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get all nodes and edges for this user
                all_nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=100000)
                all_edges = await uow_instance.kg_edges.list(filters={"user_id": user_id}, limit=100000)
                
                # Basic counts
                node_count = len(all_nodes)
                current_nodes = [n for n in all_nodes if n.is_current]
                current_node_count = len(current_nodes)
                historical_node_count = node_count - current_node_count
                
                edge_count = len(all_edges)
                current_edges = [e for e in all_edges if e.is_current]
                current_edge_count = len(current_edges)
                historical_edge_count = edge_count - current_edge_count
                
                # Node/edge type distributions
                import json
                node_types = {}
                for node in all_nodes:
                    label = node.label or "unknown"
                    node_types[label] = node_types.get(label, 0) + 1
                
                edge_types = {}
                for edge in all_edges:
                    rel_type = edge.relation_type or "unknown"
                    edge_types[rel_type] = edge_types.get(rel_type, 0) + 1
                
                # Total properties
                total_node_properties = 0
                for node in all_nodes:
                    if node.properties:
                        if isinstance(node.properties, str):
                            try:
                                props = json.loads(node.properties)
                                total_node_properties += len(props)
                            except:
                                pass
                        elif isinstance(node.properties, dict):
                            total_node_properties += len(node.properties)
                
                # Storage size estimation
                node_data_size = sum(
                    len(str(node.id or "")) + len(str(node.label or "")) + 
                    len(str(node.properties or "")) + len(str(node.source_text or ""))
                    for node in all_nodes
                )
                edge_data_size = sum(
                    len(str(edge.id or "")) + len(str(edge.relation_type or "")) + 
                    len(str(edge.properties or "")) + len(str(edge.source_text or ""))
                    for edge in all_edges
                )
                storage_size_mb = (node_data_size + edge_data_size) / (1024 * 1024) * 1.3
                
                # Health metrics
                avg_degree = current_edge_count / max(current_node_count, 1)
                isolated_nodes = sum(1 for node in current_nodes if not any(
                    e.source_id == node.id or e.target_id == node.id for e in current_edges
                ))
                
                return {
                    "total_nodes": node_count,
                    "current_nodes": current_node_count,
                    "historical_nodes": historical_node_count,
                    "total_edges": edge_count,
                    "current_edges": current_edge_count,
                    "historical_edges": historical_edge_count,
                    "total_node_properties": total_node_properties,
                    "node_types": node_types,
                    "edge_types": edge_types,
                    "storage_size_mb": round(storage_size_mb, 2),
                    "user_id": user_id,
                    "health": {
                        "orphaned_edges": 0,
                        "duplicate_nodes": 0,
                        "stale_nodes_count": 0,
                        "stale_nodes_percent": 0.0,
                        "property_completeness": total_node_properties / max(current_node_count, 1),
                        "nodes_added_24h": 0,
                        "edges_added_24h": 0
                    },
                    "duplicate_pairs": None,
                    "structure": {
                        "graph_density": current_edge_count / max((current_node_count * (current_node_count - 1)) / 2, 1) if current_node_count > 1 else 0.0,
                        "average_degree": avg_degree,
                        "max_degree": 0,
                        "min_degree": 0,
                        "isolated_nodes": isolated_nodes,
                        "connected_components": 1,
                        "largest_component_size": current_node_count
                    },
                    "temporal": {
                        "growth_rate_7d": 0.0,
                        "growth_rate_30d": 0.0,
                        "most_active_day": None,
                        "activity_by_day": {}
                    },
                    "centrality": {
                        "top_by_degree": [],
                        "top_by_pagerank": [],
                        "top_by_betweenness": []
                    },
                    "clustering": {
                        "global_clustering_coefficient": 0.0,
                        "average_clustering_coefficient": 0.0,
                        "communities_detected": 0,
                        "modularity_score": 0.0
                    }
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG stats: {e}", exc_info=True)
            return {
                "error": "KG_STATS_FAILED",
                "message": str(e)
            }
    
    async def handle_kg_nodes_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG nodes request from gateway"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 1000)
            offset = request_data.get("offset", 0)
            limit = min(limit, 1000)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query KG nodes from database
            uow = uow_factory()
            async with uow as uow_instance:
                nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=limit, offset=offset)
                
                # Convert to dict format - match original router.py format
                import json
                nodes_list = []
                for node in nodes:
                    nodes_list.append(
                        {
                            "id": node.id,
                            "user_id": node.user_id,
                            "label": node.label,
                            "properties": json.loads(node.properties) if isinstance(node.properties, str) else (node.properties or {}),
                            "confidence": node.confidence,
                            "source_text": node.source_text,
                            "created_at": node.created_at.isoformat() if getattr(node, "created_at", None) else None,
                            "updated_at": node.updated_at.isoformat() if getattr(node, "updated_at", None) else None,
                            "valid_from": node.valid_from.isoformat() if getattr(node, "valid_from", None) else None,
                            "valid_until": node.valid_until.isoformat() if getattr(node, "valid_until", None) else None,
                            "is_current": bool(node.is_current),
                            "canonical_id": getattr(node, "canonical_id", None),
                            "aliases": json.loads(node.aliases_json) if isinstance(getattr(node, "aliases_json", None), str) else (getattr(node, "aliases_json", None) or []),
                        }
                    )
                
                return {
                    "nodes": nodes_list,
                    "total": len(nodes_list),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG nodes: {e}", exc_info=True)
            return {
                "nodes": [],
                "total": 0,
                "limit": request_data.get("limit", 1000),
                "offset": request_data.get("offset", 0)
            }
    
    async def handle_kg_edges_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG edges request from gateway"""
        try:
            user_id = request_data.get("user_id")
            limit = request_data.get("limit", 1000)
            offset = request_data.get("offset", 0)
            limit = min(limit, 1000)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query KG edges from database
            uow = uow_factory()
            async with uow as uow_instance:
                edges = await uow_instance.kg_edges.list(
                    filters={"user_id": user_id, "is_current": True},
                    limit=limit,
                    offset=offset,
                )
                
                # Convert to dict format - match original router.py format
                import json
                edges_list = []
                for edge in edges:
                    edges_list.append({
                        "id": edge.id,
                        "user_id": edge.user_id,
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "relation_type": edge.relation_type,
                        "properties": json.loads(edge.properties) if isinstance(edge.properties, str) else (edge.properties or {}),
                        "confidence": edge.confidence,
                        "source_text": edge.source_text,
                        "created_at": edge.created_at.isoformat() if getattr(edge, "created_at", None) else None,
                        "updated_at": edge.updated_at.isoformat() if getattr(edge, "updated_at", None) else None,
                        "valid_from": edge.valid_from.isoformat() if getattr(edge, "valid_from", None) else None,
                        "valid_until": edge.valid_until.isoformat() if getattr(edge, "valid_until", None) else None,
                        "is_current": bool(edge.is_current),
                    })
                
                return {
                    "edges": edges_list,
                    "total": len(edges_list),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get KG edges: {e}", exc_info=True)
            return {
                "edges": [],
                "total": 0,
                "limit": request_data.get("limit", 1000),
                "offset": request_data.get("offset", 0)
            }

    async def handle_kg_schema_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG schema request from gateway"""
        try:
            user_id = request_data.get("user_id")

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id, "is_current": True}, limit=10000)
                edges = await uow_instance.kg_edges.list(filters={"user_id": user_id, "is_current": True}, limit=10000)

                node_labels = sorted(list(set(node.label for node in nodes if getattr(node, "label", None))))
                relationship_types = sorted(list(set(edge.relation_type for edge in edges if getattr(edge, "relation_type", None))))

                node_properties = [
                    "id", "label", "confidence", "source_text",
                    "created_at", "updated_at", "valid_from", "valid_until",
                    "is_current", "canonical_id", "language", "reason",
                ]

                relationship_properties = [
                    "id", "relation_type", "confidence", "source_text",
                    "created_at", "updated_at", "valid_from", "valid_until",
                    "is_current", "reason",
                ]

                return {
                    "nodeLabels": node_labels,
                    "relationshipTypes": relationship_types,
                    "nodeProperties": node_properties,
                    "relationshipProperties": relationship_properties,
                }

        except Exception as e:
            self.logger.error(f"Failed to get KG schema: {e}", exc_info=True)
            return {
                "error": "KG_SCHEMA_FAILED",
                "message": str(e),
            }

    async def handle_kg_changes_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG changes request from gateway"""
        try:
            user_id = request_data.get("user_id")
            from_timestamp = request_data.get("from_timestamp")
            to_timestamp = request_data.get("to_timestamp")
            limit = request_data.get("limit", 1000)

            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            async with uow as uow_instance:
                import json
                from datetime import datetime

                def _parse_iso(ts: Any):
                    if ts is None:
                        return None
                    if isinstance(ts, datetime):
                        return ts
                    if isinstance(ts, str):
                        try:
                            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception:
                            return None
                    return None

                from_dt = _parse_iso(from_timestamp)
                to_dt = _parse_iso(to_timestamp)

                def _in_range(value: Any) -> bool:
                    if value is None:
                        return False
                    if isinstance(value, datetime) and from_dt and to_dt:
                        return from_dt <= value <= to_dt
                    # Fallback: compare as strings (best-effort)
                    try:
                        return str(from_timestamp) <= str(value) <= str(to_timestamp)
                    except Exception:
                        return False

                changes: list[dict] = []

                all_nodes = await uow_instance.kg_nodes.list(filters={"user_id": user_id}, limit=100000)
                nodes_changed = [
                    n for n in all_nodes
                    if (_in_range(getattr(n, "created_at", None)) or _in_range(getattr(n, "updated_at", None)))
                ]
                nodes_changed.sort(key=lambda n: n.updated_at or n.created_at or "", reverse=True)
                nodes_changed = nodes_changed[:limit]

                for node in nodes_changed:
                    properties = getattr(node, "properties", None)
                    if properties is None:
                        properties = {}
                    elif isinstance(properties, dict):
                        properties = dict(properties)
                    else:
                        try:
                            properties = json.loads(str(properties))
                            if not isinstance(properties, dict):
                                properties = {}
                        except Exception:
                            properties = {}

                    created_at = getattr(node, "created_at", None)
                    updated_at = getattr(node, "updated_at", None)
                    valid_until = getattr(node, "valid_until", None)

                    if created_at and _in_range(created_at):
                        change_type = "node_created"
                    elif valid_until and _in_range(valid_until):
                        change_type = "node_deleted"
                    else:
                        change_type = "node_updated"

                    timestamp_val = updated_at or created_at
                    timestamp_str = timestamp_val.isoformat() if hasattr(timestamp_val, "isoformat") else str(timestamp_val)

                    changes.append(
                        {
                            "change_type": change_type,
                            "entity_type": "node",
                            "entity_id": node.id,
                            "entity_label": getattr(node, "label", None),
                            "timestamp": timestamp_str,
                            "properties_changed": list(properties.keys()) if change_type == "node_updated" else None,
                            "old_values": None,
                            "new_values": properties if change_type != "node_deleted" else None,
                            "source_text": getattr(node, "source_text", None),
                            "reason": None,
                        }
                    )

                all_edges = await uow_instance.kg_edges.list(filters={"user_id": user_id}, limit=100000)
                edges_changed = [
                    e for e in all_edges
                    if (_in_range(getattr(e, "created_at", None)) or _in_range(getattr(e, "updated_at", None)))
                ]
                edges_changed.sort(key=lambda e: e.updated_at or e.created_at or "", reverse=True)
                edges_changed = edges_changed[:limit]

                for edge in edges_changed:
                    properties = getattr(edge, "properties", None)
                    if properties is None:
                        properties = {}
                    elif isinstance(properties, dict):
                        properties = dict(properties)
                    else:
                        try:
                            properties = json.loads(str(properties))
                            if not isinstance(properties, dict):
                                properties = {}
                        except Exception:
                            properties = {}

                    created_at = getattr(edge, "created_at", None)
                    updated_at = getattr(edge, "updated_at", None)
                    valid_until = getattr(edge, "valid_until", None)

                    if created_at and _in_range(created_at):
                        change_type = "edge_created"
                    elif valid_until and _in_range(valid_until):
                        change_type = "edge_deleted"
                    else:
                        change_type = "edge_updated"

                    timestamp_val = updated_at or created_at
                    timestamp_str = timestamp_val.isoformat() if hasattr(timestamp_val, "isoformat") else str(timestamp_val)

                    changes.append(
                        {
                            "change_type": change_type,
                            "entity_type": "edge",
                            "entity_id": edge.id,
                            "entity_label": getattr(edge, "relation_type", None),
                            "timestamp": timestamp_str,
                            "properties_changed": list(properties.keys()) if change_type == "edge_updated" else None,
                            "old_values": None,
                            "new_values": properties if change_type != "edge_deleted" else None,
                            "source_text": getattr(edge, "source_text", None),
                            "reason": None,
                        }
                    )

                changes.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
                return {
                    "from_timestamp": from_timestamp,
                    "to_timestamp": to_timestamp,
                    "total_changes": len(changes),
                    "changes": changes[:limit],
                }

        except Exception as e:
            self.logger.error(f"Failed to get KG changes: {e}", exc_info=True)
            return {
                "error": "KG_CHANGES_FAILED",
                "message": str(e),
            }

    async def handle_kg_query_templates_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG query templates request from gateway"""
        try:
            from aico.core.paths import AICOPaths
            import json

            data_dir = AICOPaths.get_data_directory() / AICOPaths.get_data_subdirectory_from_config()
            templates_path = data_dir / "gql_query_templates.json"

            if not templates_path.exists():
                return {
                    "error": "KG_QUERY_TEMPLATES_NOT_INITIALIZED",
                    "message": "Query templates not initialized. Run 'aico config init' to set up templates.",
                }

            with open(templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data

        except Exception as e:
            self.logger.error(f"Failed to get KG query templates: {e}", exc_info=True)
            return {
                "error": "KG_QUERY_TEMPLATES_LOAD_FAILED",
                "message": str(e),
            }

    async def handle_kg_query_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KG GQL/Cypher query execution request from gateway"""
        try:
            user_id = request_data.get("user_id")
            query = request_data.get("query")
            output_format = request_data.get("format", "dict")
            limit = request_data.get("limit")

            # Create KG storage like backend.api.kg.dependencies.get_kg_storage
            from aico.ai.knowledge_graph import PropertyGraphStorage
            uow_factory = self.container.get_service("uow")
            kg_storage = PropertyGraphStorage(uow_factory)

            from aico.ai.knowledge_graph.query import GQLQueryExecutor
            max_results = limit or 1000
            executor = GQLQueryExecutor(
                kg_storage,
                max_results=max_results,
                timeout_seconds=30,
            )

            result = await executor.execute(query, user_id, format=output_format)
            return result

        except Exception as e:
            self.logger.error(f"Failed to execute KG query: {e}", exc_info=True)
            return {
                "error": "KG_QUERY_EXECUTION_FAILED",
                "message": str(e),
                "success": False,
            }
    
    # Agency handlers - delegate to AgencyNATSHandlers
    async def handle_agency_intentions_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_intentions_request(request_data)
    
    async def handle_agency_events_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_events_request(request_data)
    
    async def handle_agency_curiosity_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_curiosity_request(request_data)
    
    async def handle_agency_profile_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_profile_request(request_data)
    
    async def handle_agency_profile_update_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_profile_update_request(request_data)
    
    async def handle_agency_policies_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_policies_request(request_data)
    
    async def handle_agency_consent_grant_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_consent_grant_request(request_data)
    
    async def handle_agency_consents_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_consents_request(request_data)
    
    async def handle_agency_consent_revoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_consent_revoke_request(request_data)
    
    async def handle_agency_goals_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_goals_request(request_data)
    
    async def handle_agency_goal_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_goal_request(request_data)
    
    async def handle_agency_goal_plans_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_goal_plans_request(request_data)
    
    async def handle_agency_goal_replan_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_goal_replan_request(request_data)
    
    async def handle_agency_skills_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_skills_list_request(request_data)
    
    async def handle_agency_skill_info_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_skill_info_request(request_data)
    
    async def handle_agency_skill_invoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_skill_invoke_request(request_data)
    
    async def handle_agency_connectivity_scan_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_connectivity_scan_request(request_data)
    
    async def handle_agency_tools_list_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_tools_list_request(request_data)
    
    async def handle_agency_tool_info_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_tool_info_request(request_data)
    
    async def handle_agency_tool_invoke_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_tool_invoke_request(request_data)
    
    async def handle_agency_reflection_runs_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_reflection_runs_request(request_data)
    
    async def handle_agency_reflection_lessons_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_reflection_lessons_request(request_data)
    
    async def handle_agency_reflection_self_model_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_reflection_self_model_request(request_data)
    
    async def handle_agency_skill_performance_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_skill_performance_request(request_data)
    
    async def handle_agency_reflection_summary_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.agency_handlers.handle_agency_reflection_summary_request(request_data)
    
    async def handle_agency_state_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agency state request from gateway"""
        try:
            from aico.ai import ai_registry
            from datetime import datetime, UTC
            
            user_id = request_data.get("user_id")
            if not user_id:
                return {
                    "error": "MISSING_USER_ID",
                    "message": "user_id is required"
                }
            
            # Get agency engine from registry
            agency_engine = ai_registry.get("agency")
            if not agency_engine:
                return {
                    "error": "AGENCY_ENGINE_NOT_INITIALIZED",
                    "message": "Agency engine not initialized"
                }
            
            # Get UoW factory
            uow_factory = self.container.get_service("uow")
            uow = uow_factory()
            
            async with uow as uow_instance:
                # Get intention set using correct API
                intention_set_obj = await agency_engine.get_intention_set(user_id)
                intentions = intention_set_obj.intentions[:10]
                
                # Get all goals for user
                all_goals = await agency_engine.list_goals_for_user(user_id)
                
                # Fetch Goal objects for active intentions and build GoalSummary objects
                active_intentions = []
                hobby_goals = []
                if intentions:
                    goal_ids = [intent.goal_id for intent in intentions]
                    goals = await agency_engine.agency_service.get_goals_bulk(goal_ids)
                    goals_by_id = {goal.goal_id: goal for goal in goals}
                    
                    for intent in intentions:
                        goal = goals_by_id.get(intent.goal_id)
                        if goal:
                            goal_summary = {
                                "goal_id": goal.goal_id,
                                "title": goal.title,
                                "description": goal.description,
                                "origin": goal.origin.value,
                                "priority": goal.priority.value,
                                "status": goal.status.value,
                                "score": intent.arbiter_score,
                                "priority_band": intent.priority_band.value,
                                "created_at": goal.created_at.isoformat() if hasattr(goal.created_at, 'isoformat') else str(goal.created_at),
                                "metadata": goal.metadata or {},
                            }
                            active_intentions.append(goal_summary)
                            if goal.origin.value == "hobby":
                                hobby_goals.append(goal_summary)
                
                # Count open goals
                open_goals = [g for g in all_goals if g.status.value in ["pending", "active"]]
                
                # Build IntentionSetResponse structure
                intention_set = {
                    "user_id": user_id,
                    "primary_focus": active_intentions[0] if active_intentions else None,
                    "active_intentions": active_intentions,
                    "open_goals_total": len(open_goals),
                    "hobby_goals_active": hobby_goals,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                
                # Build CuriosityStatusResponse structure
                curiosity_status = {
                    "user_id": user_id,
                    "curiosity_level": "medium",
                    "curiosity_opportunities": [],
                    "curiosity_goals_active": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                
                # Build ValueProfileResponse structure
                value_profile = {
                    "profile_id": f"profile_{user_id}",
                    "user_id": user_id,
                    "curiosity_intensity": 0.5,
                    "autonomy_level": "balanced",
                    "sensitive_life_areas": [],
                    "allowed_curiosity_domains": [],
                }
                
                # Get recent events for active goals
                active_goal_ids = [intent.goal_id for intent in intentions]
                recent_events = []
                
                if active_goal_ids:
                    try:
                        rows = await uow_instance.agency_events_log.get_by_entities_bulk(
                            entity_type="goal",
                            entity_ids=active_goal_ids,
                            limit_per_entity=20,
                        )
                        
                        # Deduplicate and aggregate events
                        import json
                        seen_ids = set()
                        goal_events = []
                        
                        # Map database event types to API enum values
                        def map_event_type(db_event_type: str) -> str:
                            """Map database event types to API EventType enum values."""
                            event_type_lower = db_event_type.lower()
                            if "curiosity" in event_type_lower or "signal" in event_type_lower:
                                return "curiosity_signal"
                            elif "user" in event_type_lower or "trigger" in event_type_lower or "request" in event_type_lower:
                                return "user_trigger"
                            elif "external" in event_type_lower or "stimulus" in event_type_lower:
                                return "external_stimulus"
                            else:
                                return "system_observation"
                        
                        for row in rows:
                            event_id = str(row.event_id)
                            if event_id in seen_ids:
                                continue
                            seen_ids.add(event_id)
                            
                            # Parse event_data JSON if it's a string
                            event_data = {}
                            if hasattr(row, 'event_data') and row.event_data:
                                try:
                                    event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                                except:
                                    event_data = {}
                            
                            goal_events.append({
                                "event_id": event_id,
                                "user_id": str(row.user_id),
                                "event_type": map_event_type(str(row.event_type)),
                                "source": str(row.source_component or "system"),
                                "title": event_data.get("title", row.event_type),
                                "description": event_data.get("description", ""),
                                "intensity": event_data.get("intensity", 0.5),
                                "metadata": event_data,
                                "created_at": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                                "processed": True,
                                "related_goal_id": str(row.entity_id) if row.entity_type == "goal" and row.entity_id else None,
                                "strength": 1,
                            })
                        
                        # Group by goal and aggregate
                        groups = {}
                        for ev in goal_events:
                            gid = ev.get("related_goal_id")
                            if not gid:
                                continue
                            groups.setdefault(gid, []).append(ev)
                        
                        for goal_id, group in groups.items():
                            master = max(group, key=lambda e: e["created_at"])
                            master["strength"] = len(group)
                            recent_events.append(master)
                        
                        recent_events.sort(key=lambda e: e["created_at"], reverse=True)
                        recent_events = recent_events[:10]
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch agency events: {e}")
                
                return {
                    "user_id": user_id,
                    "intention_set": intention_set,
                    "curiosity_status": curiosity_status,
                    "value_profile": value_profile,
                    "consent_required_actions": [],
                    "recent_events": recent_events,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get agency state: {e}", exc_info=True)
            return {
                "error": "AGENCY_STATE_FAILED",
                "message": str(e)
            }
    
    async def handle_memory_album_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory album request from gateway"""
        try:
            user_uuid = request_data.get("user_uuid")
            category = request_data.get("category")
            favorites_only = request_data.get("favorites_only", False)
            limit = request_data.get("limit", 50)
            offset = request_data.get("offset", 0)
            
            # Get UoW factory from service container
            uow_factory = self.container.get_service("uow")
            
            # Query memory album from database
            uow = uow_factory()
            async with uow as uow_instance:
                from aico.ai.memory.memory_album import MemoryAlbumStore
                
                memory_store = MemoryAlbumStore()
                facts = await memory_store.get_user_curated_facts(
                    user_id=user_uuid,
                    category=category,
                    favorites_only=favorites_only,
                    limit=limit,
                    offset=offset,
                )
                
                # Enrich with user profile data
                enriched_facts = []
                for fact in facts:
                    user_profile = await uow_instance.users.get_by_id(fact['user_id'])
                    
                    fact_with_user = dict(fact)
                    if user_profile:
                        fact_with_user['user_uuid'] = user_profile.uuid
                        fact_with_user['user_full_name'] = user_profile.full_name
                        fact_with_user['user_nickname'] = user_profile.nickname
                    else:
                        fact_with_user['user_uuid'] = fact['user_id']
                        fact_with_user['user_full_name'] = 'Unknown'
                        fact_with_user['user_nickname'] = None
                    
                    enriched_facts.append(fact_with_user)
                
                # Convert to response format
                memories = []
                for fact in enriched_facts:
                    # Parse JSON fields
                    import json
                    tags = json.loads(fact.get('tags_json', '[]')) if fact.get('tags_json') else []
                    key_moments = json.loads(fact.get('key_moments_json', '[]')) if fact.get('key_moments_json') else []
                    
                    # Normalize datetime fields
                    created_at = fact['created_at']
                    if hasattr(created_at, 'isoformat'):
                        created_at = created_at.isoformat()
                    
                    updated_at = fact['updated_at']
                    if hasattr(updated_at, 'isoformat'):
                        updated_at = updated_at.isoformat()
                    
                    last_revisited = fact.get('last_revisited')
                    if last_revisited and hasattr(last_revisited, 'isoformat'):
                        last_revisited = last_revisited.isoformat()
                    
                    memories.append({
                        "fact_id": fact['fact_id'],
                        "content": fact['content'],
                        "content_type": fact.get('content_type', 'message'),
                        "category": fact['category'],
                        "fact_type": fact['fact_type'],
                        "user_note": fact.get('user_note'),
                        "tags": tags,
                        "is_favorite": bool(fact.get('is_favorite', 0)),
                        "emotional_tone": fact.get('emotional_tone'),
                        "memory_type": fact.get('memory_type'),
                        "source_conversation_id": fact['source_conversation_id'],
                        "source_message_id": fact.get('source_message_id'),
                        "revisit_count": fact.get('revisit_count', 0),
                        "last_revisited": last_revisited,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "user_uuid": fact.get('user_uuid', fact['user_id']),
                        "user_full_name": fact.get('user_full_name', 'Unknown User'),
                        "user_nickname": fact.get('user_nickname'),
                        "conversation_title": fact.get('conversation_title'),
                        "conversation_summary": fact.get('conversation_summary'),
                        "turn_range": fact.get('turn_range'),
                        "key_moments": key_moments,
                    })
                
                return {
                    "memories": memories,
                    "total": len(memories),
                    "limit": limit,
                    "offset": offset
                }
        except Exception as e:
            self.logger.error(f"Failed to get memory album: {e}", exc_info=True)
            return {
                "memories": [],
                "total": 0,
                "limit": request_data.get("limit", 50),
                "offset": request_data.get("offset", 0)
            }
    
    async def handle_operations_databases_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations databases request from gateway"""
        try:
            # PostgreSQL metrics (minimal set required by aico-studio DatabaseStorage UI)
            # Note: core runs inside docker-compose network; `AICO_PG_HOST` points at the postgres service.
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            db_size = 0
            table_count = 0
            connection_count = 0
            wal_size = 0
            status = "healthy"
            error_details = None

            try:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=db_name,
                    user=user,
                    password=password,
                    connect_timeout=5,
                )

                with conn.cursor() as cur:
                    # Table count (prefer aico_core schema; fall back to public)
                    try:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE'"
                        )
                        table_count = int(cur.fetchone()[0])
                    except Exception:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                        )
                        table_count = int(cur.fetchone()[0])

                    # Active connections
                    cur.execute(
                        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()"
                    )
                    connection_count = int(cur.fetchone()[0])

                    # Database size
                    cur.execute("SELECT pg_database_size(current_database())")
                    db_size = int(cur.fetchone()[0])

                    # Approximate WAL size (LSN diff from origin)
                    cur.execute("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')")
                    wal_size = int(float(cur.fetchone()[0]))

                conn.close()
            except psycopg2.OperationalError as e:
                status = "critical"
                error_details = str(e)
            except Exception as e:
                status = "degraded"
                error_details = str(e)

            databases = [
                {
                    "name": "PostgreSQL",
                    "type": "postgresql",
                    "size_bytes": db_size,
                    "status": status,
                    "location": f"{host}:{port}/{db_name}",
                    "error_details": error_details,
                    "table_count": table_count,
                    "connection_count": connection_count,
                    "wal_size_bytes": wal_size,
                    "database_name": db_name,
                    "host": host,
                    "port": port,
                }
            ]

            return {"databases": databases}
        except Exception as e:
            # Do NOT fail the UI. Always return a PostgreSQL entry with critical status.
            self.logger.error(f"Failed to get database operations: {e}", exc_info=True)
            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            return {
                "databases": [
                    {
                        "name": "PostgreSQL",
                        "type": "postgresql",
                        "size_bytes": 0,
                        "status": "critical",
                        "location": f"{host}:{port}/{db_name}",
                        "error_details": str(e),
                        "table_count": 0,
                        "connection_count": 0,
                        "wal_size_bytes": 0,
                        "database_name": db_name,
                        "host": host,
                        "port": port,
                    }
                ]
            }

    async def handle_operations_postgresql_schema_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PostgreSQL schema metadata request from gateway"""
        try:
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=db_name,
                user=user,
                password=password,
                connect_timeout=5,
            )

            tables: list[str] = []
            columns: dict[str, list[str]] = {}

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
                for (table_name,) in cur.fetchall():
                    tables.append(table_name)
                    try:
                        cur.execute(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'aico_core' AND table_name = %s "
                            "ORDER BY ordinal_position",
                            (table_name,),
                        )
                        columns[table_name] = [row[0] for row in cur.fetchall()]
                    except Exception:
                        columns[table_name] = []

            conn.close()
            return {"tables": tables, "columns": columns}
        except Exception as e:
            self.logger.error(f"Failed to get schema metadata: {e}", exc_info=True)
            return {"tables": [], "columns": {}}

    async def handle_operations_postgresql_details_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import psycopg2

            host = os.environ.get("AICO_PG_HOST", "postgres")
            port = int(os.environ.get("AICO_PG_PORT", "5432"))
            db_name = os.environ.get("AICO_POSTGRES_DATABASE", "aico")
            user = os.environ.get("AICO_POSTGRES_USER", "postgres")

            password = None
            try:
                with open("/run/secrets/pg_password", "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                password = os.environ.get("AICO_PG_PASSWORD")

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=db_name,
                user=user,
                password=password,
                connect_timeout=5,
            )

            tables: list[dict[str, Any]] = []

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'aico_core' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
                table_names = [row[0] for row in cur.fetchall()]

                for table_name in table_names:
                    row_count = 0
                    size_bytes = None
                    column_count = 0

                    try:
                        cur.execute(f'SELECT COUNT(*) FROM "aico_core"."{table_name}"')
                        row_count = int(cur.fetchone()[0])
                    except Exception:
                        row_count = 0

                    try:
                        cur.execute(
                            "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'aico_core' AND table_name = %s",
                            (table_name,),
                        )
                        column_count = int(cur.fetchone()[0])
                    except Exception:
                        column_count = 0

                    try:
                        cur.execute("SELECT pg_total_relation_size(%s)", (f"aico_core.{table_name}",))
                        size_bytes = int(cur.fetchone()[0])
                    except Exception:
                        size_bytes = None

                    tables.append(
                        {
                            "name": table_name,
                            "row_count": row_count,
                            "size_bytes": size_bytes,
                            "columns": column_count,
                        }
                    )

            conn.close()
            return {"database_type": "postgresql", "tables": tables}
        except Exception as e:
            self.logger.error(f"Failed to get PostgreSQL details: {e}", exc_info=True)
            return {"database_type": "postgresql", "tables": []}
    
    async def handle_operations_topology_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations topology request from gateway"""
        try:
            import time
            import asyncio
            import subprocess
            from datetime import datetime
            from backend.api.operations.router import start_time, format_uptime, get_backend_version, get_modelservice_version
            from backend.services.version_detector import get_version_detector
            
            # Get versions
            backend_version = get_backend_version()
            modelservice_version = get_modelservice_version()
            
            # Get database versions
            version_detector = get_version_detector()
            db_versions = await version_detector.get_all_versions()
            
            # Get backend container uptime (Gateway and Core run in same container)
            backend_uptime_str = "N/A"
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-core"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    started_at = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    backend_uptime_str = format_uptime(uptime_seconds)
            except Exception:
                # Fallback to process uptime if docker inspect fails
                backend_uptime_seconds = time.time() - start_time
                backend_uptime_str = format_uptime(backend_uptime_seconds)
            
            # Get modelservice uptime
            modelservice_uptime_str = "N/A"
            try:
                from backend.services import get_modelservice_client
                from aico.core.config import ConfigurationManager
                config = ConfigurationManager()
                modelservice_client = get_modelservice_client(config)
                health_data = await modelservice_client.get_health()
                if health_data and health_data.get('success') and health_data.get('uptime_seconds'):
                    modelservice_uptime_str = format_uptime(health_data['uptime_seconds'])
            except Exception:
                pass
            
            # Get postgres uptime
            postgres_uptime_str = "N/A"
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-postgres"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    started_at = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    postgres_uptime_str = format_uptime(uptime_seconds)
            except Exception:
                pass
            
            # Get MinIO health, version, and uptime
            minio_status = "offline"
            minio_version = "unknown"
            minio_uptime_str = "N/A"
            try:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get("http://localhost:9000/minio/health/live")
                    if response.status_code == 200:
                        minio_status = "healthy"
            except Exception:
                pass
            
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "exec", "aico-minio", "minio", "--version"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    version_line = result.stdout.strip()
                    if "RELEASE" in version_line:
                        # Parse timestamp format like "RELEASE.2025-09-07T16-13-09Z" to "2025-09-07"
                        timestamp = version_line.split("RELEASE.")[1].split()[0] if len(version_line.split("RELEASE.")) > 1 else ""
                        if timestamp and "T" in timestamp:
                            minio_version = timestamp.split("T")[0]  # Extract just the date part
                        else:
                            minio_version = timestamp if timestamp else "unknown"
            except Exception:
                pass
            
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "inspect", "--format={{.State.StartedAt}}", "aico-minio"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    started_at = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                    minio_uptime_str = format_uptime(uptime_seconds)
            except Exception:
                pass
            
            # Build services list with all services
            services = [
                {"id": "gateway", "name": "API Gateway", "type": "gateway", "status": "healthy", "version": backend_version, "host": "localhost", "port": 8771, "uptime": backend_uptime_str},
                {"id": "core", "name": "Backend Core", "type": "backend", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
                {"id": "studio", "name": "Studio", "type": "studio", "status": "healthy", "version": "N/A", "host": "localhost", "port": 3000, "uptime": "N/A"},
                {"id": "modelservice", "name": "Model Service", "type": "modelservice", "status": "healthy", "version": modelservice_version, "host": "localhost", "port": 11434, "uptime": modelservice_uptime_str},
                {"id": "scheduler", "name": "Task Scheduler", "type": "scheduler", "status": "healthy", "version": backend_version, "host": "localhost", "uptime": backend_uptime_str},
                {"id": "nats", "name": "NATS", "type": "bus", "status": "healthy", "version": "2.10", "host": "localhost", "port": 4222, "uptime": "N/A"},
                {"id": "loki", "name": "Loki", "type": "logs", "status": "healthy", "version": "2.9.0", "host": "localhost", "port": 3100, "uptime": "N/A"},
                {"id": "grafana", "name": "Grafana", "type": "dashboard", "status": "healthy", "version": "12.1", "host": "localhost", "port": 3001, "uptime": "N/A"},
                {"id": "postgresql", "name": "PostgreSQL", "type": "database", "status": "healthy", "version": db_versions.get("PostgreSQL", "18.1"), "host": "localhost", "port": 5432, "uptime": postgres_uptime_str},
                {"id": "minio", "name": "MinIO", "type": "database", "status": minio_status, "version": minio_version, "host": "localhost", "port": 9000, "uptime": minio_uptime_str},
            ]
            
            # Build connections list with all connections
            connections = [
                {"from_service": "studio", "to_service": "gateway", "protocol": "HTTP/WebSocket", "status": "active"},
                {"from_service": "gateway", "to_service": "nats", "protocol": "NATS", "status": "active"},
                {"from_service": "nats", "to_service": "core", "protocol": "NATS", "status": "active"},
                {"from_service": "core", "to_service": "nats", "protocol": "NATS", "status": "active"},
                {"from_service": "core", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
                {"from_service": "core", "to_service": "minio", "protocol": "S3", "status": "active"},
                {"from_service": "core", "to_service": "modelservice", "protocol": "ZMQ", "status": "active"},
                {"from_service": "core", "to_service": "loki", "protocol": "HTTP", "status": "active"},
                {"from_service": "grafana", "to_service": "loki", "protocol": "HTTP", "status": "active"},
                {"from_service": "grafana", "to_service": "postgresql", "protocol": "PostgreSQL", "status": "active"},
            ]
            
            return {
                "services": services,
                "connections": connections,
                "deployment_type": "docker-compose"
            }
        except Exception as e:
            self.logger.error(f"Failed to get operations topology: {e}", exc_info=True)
            return {
                "error": "OPERATIONS_TOPOLOGY_FAILED",
                "message": str(e)
            }
    
    async def handle_operations_create_backup_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup creation request from gateway"""
        try:
            from backend.api.operations.backup_sets import create_backup_set
            from backend.api.operations.schemas import BackupSetCreateRequest
            
            # Parse request
            backup_request = BackupSetCreateRequest(
                output_path=request_data.get("output_path"),
                include_influx=request_data.get("include_influx", False),
                created_by_user_uuid=request_data.get("created_by_user_uuid"),
            )
            
            # Create backup
            response = await create_backup_set(backup_request)
            
            # Convert to dict
            return {
                "success": response.success,
                "backup_set": response.backup_set.model_dump() if response.backup_set else None,
                "message": response.message
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}", exc_info=True)
            return {
                "success": False,
                "backup_set": None,
                "message": str(e)
            }

    async def handle_operations_restore_backup_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup restore request from gateway"""
        try:
            from backend.api.operations.backup_sets import restore_backup_set
            from backend.api.operations.schemas import BackupSetRestoreRequest

            restore_request = BackupSetRestoreRequest(
                backup_id=request_data.get("backup_id"),
                confirm_destroy_existing=bool(request_data.get("confirm_destroy_existing", False)),
                restore_to_primary=bool(request_data.get("restore_to_primary", False)),
                restore_influx=bool(request_data.get("restore_influx", False)),
            )

            response = await restore_backup_set(restore_request)
            return {
                "success": bool(response.success),
                "message": str(response.message),
            }
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
            }
    
    async def handle_operations_backup_sets_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle operations backup sets request from gateway"""
        try:
            from backend.api.operations.backup_sets import list_backup_sets_async_with_options

            include_deleted = bool(request_data.get("include_deleted", False))
            resp = await list_backup_sets_async_with_options(include_deleted=include_deleted)
            return {
                "backup_sets": [b.model_dump() for b in resp.backup_sets],
                "total_count": int(resp.total_count),
            }
        except Exception as e:
            self.logger.error(f"Failed to get backup sets: {e}", exc_info=True)
            return {
                "error": "OPERATIONS_BACKUP_SETS_FAILED",
                "message": str(e)
            }

    async def handle_operations_delete_backup_set_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup set soft-delete request from gateway"""
        try:
            backup_id = str(request_data.get("backup_id") or "").strip()
            if not backup_id:
                return {"error": "VALIDATION_ERROR", "message": "backup_id is required"}

            deleted_by_user_uuid = request_data.get("deleted_by_user_uuid")
            if deleted_by_user_uuid is not None:
                deleted_by_user_uuid = str(deleted_by_user_uuid)

            from backend.api.operations.backup_sets import delete_backup_set_async

            resp = await delete_backup_set_async(backup_id, deleted_by_user_uuid=deleted_by_user_uuid)
            return resp.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to delete backup set: {e}", exc_info=True)
            return {"error": "OPERATIONS_DELETE_BACKUP_FAILED", "message": str(e)}

    async def handle_operations_purge_backup_set_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup set purge request from gateway"""
        try:
            backup_id = str(request_data.get("backup_id") or "").strip()
            if not backup_id:
                return {"error": "VALIDATION_ERROR", "message": "backup_id is required"}

            from backend.api.operations.backup_sets import purge_backup_set_async

            resp = await purge_backup_set_async(backup_id)
            return resp.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to purge backup set: {e}", exc_info=True)
            return {"error": "OPERATIONS_PURGE_BACKUP_FAILED", "message": str(e)}
    
    async def handle_scheduler_expected_runs_today_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scheduler expected runs today request from gateway"""
        try:
            # NOTE: This endpoint used to calculate expected runs from DB-backed task schedules.
            # In the current NATS-only core architecture, the request handler must be robust and
            # never time out the gateway. If DB-backed schedules are temporarily unavailable or
            # not wired here, return a minimal valid payload.
            from datetime import datetime, timedelta, UTC

            now = datetime.now(UTC)
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            return {
                "total_expected_runs": 0,
                "task_run_counts": {},
                "calculated_at": now.isoformat(),
                "period_start": day_start.isoformat(),
                "period_end": day_end.isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate expected runs: {e}", exc_info=True)
            return {
                "error": "SCHEDULER_EXPECTED_RUNS_FAILED",
                "message": str(e)
            }
    
    async def handle_system_metrics_all_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system metrics all request from gateway"""
        try:
            from backend.api.metrics.endpoints.gateway import get_gateway_metrics
            from backend.api.metrics.endpoints.modelservice import get_modelservice_metrics
            from backend.api.metrics.endpoints.memory import get_memory_metrics
            from backend.api.metrics.endpoints.scheduler import get_scheduler_metrics
            from backend.api.metrics.endpoints.messagebus import get_messagebus_metrics
            from backend.api.metrics.endpoints.system import get_system_health_metrics
            from datetime import datetime, UTC
            import asyncio
            
            # Get UoW from service container
            uow = self.container.get_service("uow")
            
            # Mock user dict for memory metrics (admin access already validated at gateway)
            user = {"uuid": "system", "role": "admin"}
            
            # Collect all metrics in parallel
            gateway, modelservice, memory, scheduler, message_bus, system_health = await asyncio.gather(
                get_gateway_metrics(),
                get_modelservice_metrics(),
                get_memory_metrics(user, uow),
                get_scheduler_metrics(),
                get_messagebus_metrics(),
                get_system_health_metrics(),
            )
            
            return {
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "gateway": gateway.model_dump(),
                "modelservice": modelservice.model_dump(),
                "memory": memory.model_dump(),
                "scheduler": scheduler.model_dump(),
                "message_bus": message_bus.model_dump(),
                "system_health": system_health.model_dump(),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}", exc_info=True)

    async def handle_system_overview_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system overview request from gateway"""
        try:
            from backend.api.system.router import get_system_overview

            uow = self.container.get_service("uow")
            user = {"user_id": "system", "uuid": "system", "role": "admin"}

            resp = await get_system_overview(user=user, uow=uow)
            return resp.model_dump()
        except Exception as e:
            self.logger.error(f"Failed to get system overview: {e}", exc_info=True)
            return {"error": "SYSTEM_OVERVIEW_FAILED", "message": str(e)}
    async def handle_system_health_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_system_health_request(request_data)
    
    async def handle_system_health_services_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health services request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_system_health_services_request(request_data)
    
    async def handle_system_health_issues_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health issues request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_system_health_issues_request(request_data)
    
    async def handle_remediate_available_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle available remediation actions request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_remediate_available_request(request_data)
    
    async def handle_remediate_history_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle remediation history request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_remediate_history_request(request_data)

    async def handle_remediate_trigger_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle remediation trigger request from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_remediate_trigger_request(request_data)
    
    async def handle_health_check_connectivity_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connectivity health check trigger from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_health_check_connectivity(request_data)
    
    async def handle_health_check_resources_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources health check trigger from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_health_check_resources(request_data)
    
    async def handle_health_check_models_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle models health check trigger from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_health_check_models(request_data)
    
    async def handle_health_check_ai_behaviour_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI behaviour health check trigger from gateway"""
        handlers = await self._get_system_handlers()
        return await handlers.handle_health_check_ai_behaviour(request_data)
    
    def _extract_request_data(self, request_envelope) -> Dict[str, Any]:
        """Extract JSON data from request envelope"""
        try:
            # Check if request has JSON data in attributes
            if hasattr(request_envelope, 'metadata') and hasattr(request_envelope.metadata, 'attributes'):
                json_data = request_envelope.metadata.attributes.get('json_data', '{}')
                return json.loads(json_data)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to extract request data: {e}")
            return {}
    
    async def setup_handlers(self, message_bus_client):
        """Register all NATS request handlers using native NATS request/reply"""

        async with self._setup_lock:
            if self._setup_completed:
                self.logger.warning("setup_handlers called again; subscriptions already registered. Skipping.")
                return
            # Mark as completed immediately (under lock) so even if setup_handlers is invoked
            # again during startup/reconnect churn, we do not register duplicate subscriptions.
            self._setup_completed = True
        
        def make_handler(handler_func, response_type):
            """Create a NATS message handler that processes requests and sends replies"""
            async def handler(msg):
                try:
                    # Parse JSON request directly from bytes
                    request_data = json.loads(msg.data.decode('utf-8')) if msg.data else {}
                    
                    # Process request
                    response_data = await handler_func(request_data)
                    
                    # Send JSON response as plain bytes (simplest approach)
                    response_bytes = json.dumps(response_data).encode('utf-8')

                    # NATS default max payload is typically 1MiB. Keep a safety buffer.
                    if len(response_bytes) > 900_000:
                        response_data = {
                            "error": "RESPONSE_TOO_LARGE",
                            "message": "Response payload exceeded NATS max payload; reduce requested range/limit.",
                            "subject": getattr(msg, "subject", None),
                            "response_type": response_type,
                            "size_bytes": len(response_bytes),
                        }
                        response_bytes = json.dumps(response_data).encode("utf-8")
                    
                    # Send reply using NATS built-in reply mechanism
                    try:
                        await message_bus_client._nats.publish(
                            msg.reply,
                            response_bytes,
                        )
                    except Exception as e:
                        # Publishing can fail for oversized payloads (MaxPayloadError) or transient transport issues.
                        self.logger.error(f"Error in {response_type} handler: {e}", exc_info=True)
                        if getattr(msg, "reply", None):
                            error_payload = {
                                "error": "NATS_PUBLISH_FAILED",
                                "message": str(e),
                                "subject": getattr(msg, "subject", None),
                                "response_type": response_type,
                            }
                            try:
                                await message_bus_client._nats.publish(
                                    msg.reply,
                                    json.dumps(error_payload).encode("utf-8"),
                                )
                            except Exception:
                                pass
                    
                except Exception as e:
                    self.logger.error(f"Error in {response_type} handler: {e}", exc_info=True)
                    try:
                        if getattr(msg, "reply", None):
                            error_payload = {
                                "error": "NATS_HANDLER_ERROR",
                                "message": str(e),
                                "subject": getattr(msg, "subject", None),
                            }
                            await message_bus_client._nats.publish(
                                msg.reply,
                                json.dumps(error_payload).encode("utf-8"),
                            )
                    except Exception:
                        # If we can't reply, at least avoid crashing the subscription callback.
                        pass
            
            return handler

        # Register handlers using direct NATS subscriptions (not MessageBusClient.subscribe)
        # because we need access to the raw NATS message for the reply subject
        self.logger.info("Subscribing to scheduler.status...")
        sid1 = await message_bus_client._nats.subscribe(
            "scheduler.status",
            cb=make_handler(self.handle_scheduler_status_request, "scheduler.status.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.status (sid={sid1})")
        
        self.logger.info("Subscribing to scheduler.tasks...")
        sid2 = await message_bus_client._nats.subscribe(
            "scheduler.tasks",
            cb=make_handler(self.handle_scheduler_tasks_request, "scheduler.tasks.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.tasks (sid={sid2})")

        # Scheduler management endpoints (gateway proxies via NATS)
        self.logger.info("Subscribing to scheduler.task.get...")
        sid2a = await message_bus_client._nats.subscribe(
            "scheduler.task.get",
            cb=make_handler(self.handle_scheduler_task_get_request, "scheduler.task.get.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.get (sid={sid2a})")

        self.logger.info("Subscribing to scheduler.task.create...")
        sid2b = await message_bus_client._nats.subscribe(
            "scheduler.task.create",
            cb=make_handler(self.handle_scheduler_task_create_request, "scheduler.task.create.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.create (sid={sid2b})")

        self.logger.info("Subscribing to scheduler.task.update...")
        sid2c = await message_bus_client._nats.subscribe(
            "scheduler.task.update",
            cb=make_handler(self.handle_scheduler_task_update_request, "scheduler.task.update.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.update (sid={sid2c})")

        self.logger.info("Subscribing to scheduler.task.delete...")
        sid2d = await message_bus_client._nats.subscribe(
            "scheduler.task.delete",
            cb=make_handler(self.handle_scheduler_task_delete_request, "scheduler.task.delete.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.delete (sid={sid2d})")

        self.logger.info("Subscribing to scheduler.task.enable...")
        sid2e = await message_bus_client._nats.subscribe(
            "scheduler.task.enable",
            cb=make_handler(self.handle_scheduler_task_enable_request, "scheduler.task.enable.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.enable (sid={sid2e})")

        self.logger.info("Subscribing to scheduler.task.disable...")
        sid2f = await message_bus_client._nats.subscribe(
            "scheduler.task.disable",
            cb=make_handler(self.handle_scheduler_task_disable_request, "scheduler.task.disable.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.disable (sid={sid2f})")

        self.logger.info("Subscribing to scheduler.task.status...")
        sid2g = await message_bus_client._nats.subscribe(
            "scheduler.task.status",
            cb=make_handler(self.handle_scheduler_task_status_request, "scheduler.task.status.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.status (sid={sid2g})")

        self.logger.info("Subscribing to scheduler.task.history...")
        sid2h = await message_bus_client._nats.subscribe(
            "scheduler.task.history",
            cb=make_handler(self.handle_scheduler_task_history_request, "scheduler.task.history.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.history (sid={sid2h})")

        self.logger.info("Subscribing to scheduler.executions.range...")
        sid2i = await message_bus_client._nats.subscribe(
            "scheduler.executions.range",
            cb=make_handler(self.handle_scheduler_executions_range_request, "scheduler.executions.range.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.executions.range (sid={sid2i})")

        self.logger.info("Subscribing to scheduler.executions.list...")
        sid2i_list = await message_bus_client._nats.subscribe(
            "scheduler.executions.list",
            cb=make_handler(self.handle_scheduler_executions_list_request, "scheduler.executions.list.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.executions.list (sid={sid2i_list})")

        self.logger.info("Subscribing to scheduler.executions.get...")
        sid2i_get = await message_bus_client._nats.subscribe(
            "scheduler.executions.get",
            cb=make_handler(self.handle_scheduler_execution_get_request, "scheduler.executions.get.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.executions.get (sid={sid2i_get})")

        self.logger.info("Subscribing to scheduler.executions.stats...")
        sid2i_stats = await message_bus_client._nats.subscribe(
            "scheduler.executions.stats",
            cb=make_handler(self.handle_scheduler_executions_stats_request, "scheduler.executions.stats.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.executions.stats (sid={sid2i_stats})")

        self.logger.info("Subscribing to scheduler.runs.list...")
        sid_runs_list = await message_bus_client._nats.subscribe(
            "scheduler.runs.list",
            cb=make_handler(self.handle_scheduler_runs_list_request, "scheduler.runs.list.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.runs.list (sid={sid_runs_list})")

        self.logger.info("Subscribing to scheduler.runs.get...")
        sid_runs_get = await message_bus_client._nats.subscribe(
            "scheduler.runs.get",
            cb=make_handler(self.handle_scheduler_run_get_request, "scheduler.runs.get.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.runs.get (sid={sid_runs_get})")

        self.logger.info("Subscribing to scheduler.runs.stats...")
        sid_runs_stats = await message_bus_client._nats.subscribe(
            "scheduler.runs.stats",
            cb=make_handler(self.handle_scheduler_runs_stats_request, "scheduler.runs.stats.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.runs.stats (sid={sid_runs_stats})")

        self.logger.info("Subscribing to scheduler.executions.unacknowledged_failures...")
        sid2j = await message_bus_client._nats.subscribe(
            "scheduler.executions.unacknowledged_failures",
            cb=make_handler(
                self.handle_scheduler_unacknowledged_failures_request,
                "scheduler.executions.unacknowledged_failures.reply",
            ),
        )
        self.logger.info(
            f"✅ Subscribed to scheduler.executions.unacknowledged_failures (sid={sid2j})"
        )

        self.logger.info("Subscribing to scheduler.executions.acknowledge...")
        sid2k = await message_bus_client._nats.subscribe(
            "scheduler.executions.acknowledge",
            cb=make_handler(
                self.handle_scheduler_acknowledge_execution_request,
                "scheduler.executions.acknowledge.reply",
            ),
        )
        self.logger.info(f"✅ Subscribed to scheduler.executions.acknowledge (sid={sid2k})")

        self.logger.info("Subscribing to scheduler.executions.acknowledge_all...")
        sid2l = await message_bus_client._nats.subscribe(
            "scheduler.executions.acknowledge_all",
            cb=make_handler(
                self.handle_scheduler_acknowledge_all_failed_request,
                "scheduler.executions.acknowledge_all.reply",
            ),
        )
        self.logger.info(
            f"✅ Subscribed to scheduler.executions.acknowledge_all (sid={sid2l})"
        )

        self.logger.info("Subscribing to scheduler.task.trigger...")
        sid2m = await message_bus_client._nats.subscribe(
            "scheduler.task.trigger",
            cb=make_handler(self.handle_scheduler_task_trigger_request, "scheduler.task.trigger.reply"),
        )
        self.logger.info(f"✅ Subscribed to scheduler.task.trigger (sid={sid2m})")
        
        self.logger.info("Subscribing to emotion.current...")
        sid3 = await message_bus_client._nats.subscribe(
            "emotion.current",
            cb=make_handler(self.handle_emotion_current_request, "emotion.current.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.current (sid={sid3})")
        
        self.logger.info("Subscribing to emotion.history...")
        sid4 = await message_bus_client._nats.subscribe(
            "emotion.history",
            cb=make_handler(self.handle_emotion_history_request, "emotion.history.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.history (sid={sid4})")
        
        self.logger.info("Subscribing to memory.semantic.stats...")
        sid5 = await message_bus_client._nats.subscribe(
            "memory.semantic.stats",
            cb=make_handler(self.handle_memory_semantic_stats_request, "memory.semantic.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.semantic.stats (sid={sid5})")
        
        self.logger.info("Subscribing to memory.working.stats...")
        sid6 = await message_bus_client._nats.subscribe(
            "memory.working.stats",
            cb=make_handler(self.handle_memory_working_stats_request, "memory.working.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.working.stats (sid={sid6})")
        
        self.logger.info("Subscribing to kg.stats...")
        sid7 = await message_bus_client._nats.subscribe(
            "kg.stats",
            cb=make_handler(self.handle_kg_stats_request, "kg.stats.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.stats (sid={sid7})")
        
        self.logger.info("Subscribing to kg.nodes...")
        sid7a = await message_bus_client._nats.subscribe(
            "kg.nodes",
            cb=make_handler(self.handle_kg_nodes_request, "kg.nodes.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.nodes (sid={sid7a})")
        
        self.logger.info("Subscribing to kg.edges...")
        sid7b = await message_bus_client._nats.subscribe(
            "kg.edges",
            cb=make_handler(self.handle_kg_edges_request, "kg.edges.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.edges (sid={sid7b})")

        self.logger.info("Subscribing to kg.schema...")
        sid7c = await message_bus_client._nats.subscribe(
            "kg.schema",
            cb=make_handler(self.handle_kg_schema_request, "kg.schema.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.schema (sid={sid7c})")

        self.logger.info("Subscribing to kg.changes...")
        sid7d = await message_bus_client._nats.subscribe(
            "kg.changes",
            cb=make_handler(self.handle_kg_changes_request, "kg.changes.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.changes (sid={sid7d})")

        self.logger.info("Subscribing to kg.query-templates...")
        sid7e = await message_bus_client._nats.subscribe(
            "kg.query-templates",
            cb=make_handler(self.handle_kg_query_templates_request, "kg.query-templates.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.query-templates (sid={sid7e})")

        self.logger.info("Subscribing to kg.query...")
        sid7f = await message_bus_client._nats.subscribe(
            "kg.query",
            cb=make_handler(self.handle_kg_query_request, "kg.query.reply")
        )
        self.logger.info(f"✅ Subscribed to kg.query (sid={sid7f})")
        
        self.logger.info("Subscribing to memory.album...")
        sid7g = await message_bus_client._nats.subscribe(
            "memory.album",
            cb=make_handler(self.handle_memory_album_request, "memory.album.reply")
        )
        self.logger.info(f"✅ Subscribed to memory.album (sid={sid7g})")
        
        # Emotion endpoints
        self.logger.info("Subscribing to emotion.state.current...")
        sid_emotion_current = await message_bus_client._nats.subscribe(
            "emotion.state.current",
            cb=make_handler(self.handle_emotion_current_request, "emotion.state.current.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.state.current (sid={sid_emotion_current})")
        
        self.logger.info("Subscribing to emotion.state.history...")
        sid_emotion_history = await message_bus_client._nats.subscribe(
            "emotion.state.history",
            cb=make_handler(self.handle_emotion_history_request, "emotion.state.history.reply")
        )
        self.logger.info(f"✅ Subscribed to emotion.state.history (sid={sid_emotion_history})")
        
        self.logger.info("Subscribing to agency.state...")
        sid7h = await message_bus_client._nats.subscribe(
            "agency.state",
            cb=make_handler(self.handle_agency_state_request, "agency.state.reply")
        )
        self.logger.info(f"✅ Subscribed to agency.state (sid={sid7h})")
        
        self.logger.info("Subscribing to agency.goals...")
        sid7i = await message_bus_client._nats.subscribe(
            "agency.goals",
            cb=make_handler(self.handle_agency_goals_request, "agency.goals.reply")
        )
        self.logger.info(f"✅ Subscribed to agency.goals (sid={sid7i})")
        
        # All remaining agency subscriptions
        self.logger.info("Subscribing to agency.intentions...")
        await message_bus_client._nats.subscribe("agency.intentions", cb=make_handler(self.handle_agency_intentions_request, "agency.intentions.reply"))
        
        self.logger.info("Subscribing to agency.events...")
        await message_bus_client._nats.subscribe("agency.events", cb=make_handler(self.handle_agency_events_request, "agency.events.reply"))
        
        self.logger.info("Subscribing to agency.curiosity...")
        await message_bus_client._nats.subscribe("agency.curiosity", cb=make_handler(self.handle_agency_curiosity_request, "agency.curiosity.reply"))
        
        self.logger.info("Subscribing to agency.profile...")
        await message_bus_client._nats.subscribe("agency.profile", cb=make_handler(self.handle_agency_profile_request, "agency.profile.reply"))
        
        self.logger.info("Subscribing to agency.profile.update...")
        await message_bus_client._nats.subscribe("agency.profile.update", cb=make_handler(self.handle_agency_profile_update_request, "agency.profile.update.reply"))
        
        self.logger.info("Subscribing to agency.policies...")
        await message_bus_client._nats.subscribe("agency.policies", cb=make_handler(self.handle_agency_policies_request, "agency.policies.reply"))
        
        self.logger.info("Subscribing to agency.consent.grant...")
        await message_bus_client._nats.subscribe("agency.consent.grant", cb=make_handler(self.handle_agency_consent_grant_request, "agency.consent.grant.reply"))
        
        self.logger.info("Subscribing to agency.consents...")
        await message_bus_client._nats.subscribe("agency.consents", cb=make_handler(self.handle_agency_consents_request, "agency.consents.reply"))
        
        self.logger.info("Subscribing to agency.consent.revoke...")
        await message_bus_client._nats.subscribe("agency.consent.revoke", cb=make_handler(self.handle_agency_consent_revoke_request, "agency.consent.revoke.reply"))
        
        self.logger.info("Subscribing to agency.goal...")
        await message_bus_client._nats.subscribe("agency.goal", cb=make_handler(self.handle_agency_goal_request, "agency.goal.reply"))
        
        self.logger.info("Subscribing to agency.goal.plans...")
        await message_bus_client._nats.subscribe("agency.goal.plans", cb=make_handler(self.handle_agency_goal_plans_request, "agency.goal.plans.reply"))
        
        self.logger.info("Subscribing to agency.goal.replan...")
        await message_bus_client._nats.subscribe("agency.goal.replan", cb=make_handler(self.handle_agency_goal_replan_request, "agency.goal.replan.reply"))
        
        self.logger.info("Subscribing to agency.skills.list...")
        await message_bus_client._nats.subscribe("agency.skills.list", cb=make_handler(self.handle_agency_skills_list_request, "agency.skills.list.reply"))
        
        self.logger.info("Subscribing to agency.skill.info...")
        await message_bus_client._nats.subscribe("agency.skill.info", cb=make_handler(self.handle_agency_skill_info_request, "agency.skill.info.reply"))
        
        self.logger.info("Subscribing to agency.skill.invoke...")
        await message_bus_client._nats.subscribe("agency.skill.invoke", cb=make_handler(self.handle_agency_skill_invoke_request, "agency.skill.invoke.reply"))
        
        self.logger.info("Subscribing to agency.connectivity.scan...")
        await message_bus_client._nats.subscribe("agency.connectivity.scan", cb=make_handler(self.handle_agency_connectivity_scan_request, "agency.connectivity.scan.reply"))
        
        self.logger.info("Subscribing to agency.tools.list...")
        await message_bus_client._nats.subscribe("agency.tools.list", cb=make_handler(self.handle_agency_tools_list_request, "agency.tools.list.reply"))
        
        self.logger.info("Subscribing to agency.tool.info...")
        await message_bus_client._nats.subscribe("agency.tool.info", cb=make_handler(self.handle_agency_tool_info_request, "agency.tool.info.reply"))
        
        self.logger.info("Subscribing to agency.tool.invoke...")
        await message_bus_client._nats.subscribe("agency.tool.invoke", cb=make_handler(self.handle_agency_tool_invoke_request, "agency.tool.invoke.reply"))
        
        self.logger.info("Subscribing to agency.reflection.runs...")
        await message_bus_client._nats.subscribe("agency.reflection.runs", cb=make_handler(self.handle_agency_reflection_runs_request, "agency.reflection.runs.reply"))
        
        self.logger.info("Subscribing to agency.reflection.lessons...")
        await message_bus_client._nats.subscribe("agency.reflection.lessons", cb=make_handler(self.handle_agency_reflection_lessons_request, "agency.reflection.lessons.reply"))
        
        self.logger.info("Subscribing to agency.reflection.self_model...")
        await message_bus_client._nats.subscribe("agency.reflection.self_model", cb=make_handler(self.handle_agency_reflection_self_model_request, "agency.reflection.self_model.reply"))
        
        self.logger.info("Subscribing to agency.skill.performance...")
        await message_bus_client._nats.subscribe("agency.skill.performance", cb=make_handler(self.handle_agency_skill_performance_request, "agency.skill.performance.reply"))
        
        self.logger.info("Subscribing to agency.reflection.summary...")
        await message_bus_client._nats.subscribe("agency.reflection.summary", cb=make_handler(self.handle_agency_reflection_summary_request, "agency.reflection.summary.reply"))
        
        self.logger.info("✅ Subscribed to all 26 agency endpoints")
        
        self.logger.info("Subscribing to operations.databases...")
        sid8 = await message_bus_client._nats.subscribe(
            "operations.databases",
            cb=make_handler(self.handle_operations_databases_request, "operations.databases.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.databases (sid={sid8})")

        self.logger.info("Subscribing to operations.databases.postgresql.schema...")
        sid8b = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.schema",
            cb=make_handler(
                self.handle_operations_postgresql_schema_request,
                "operations.databases.postgresql.schema.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.schema (sid={sid8b})")

        self.logger.info("Subscribing to operations.databases.postgresql.details...")
        sid8c = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.details",
            cb=make_handler(
                self.handle_operations_postgresql_details_request,
                "operations.databases.postgresql.details.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.details (sid={sid8c})")
        
        self.logger.info("Subscribing to operations.topology...")
        sid9 = await message_bus_client._nats.subscribe(
            "operations.topology",
            cb=make_handler(self.handle_operations_topology_request, "operations.topology.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.topology (sid={sid9})")
        
        self.logger.info("Subscribing to operations.backup.create...")
        sid10a = await message_bus_client._nats.subscribe(
            "operations.backup.create",
            cb=make_handler(self.handle_operations_create_backup_request, "operations.backup.create.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup.create (sid={sid10a})")

        self.logger.info("Subscribing to operations.backup.restore...")
        sid10b = await message_bus_client._nats.subscribe(
            "operations.backup.restore",
            cb=make_handler(self.handle_operations_restore_backup_request, "operations.backup.restore.reply"),
        )
        self.logger.info(f"✅ Subscribed to operations.backup.restore (sid={sid10b})")
        
        self.logger.info("Subscribing to operations.backup_sets...")
        sid10 = await message_bus_client._nats.subscribe(
            "operations.backup_sets",
            cb=make_handler(self.handle_operations_backup_sets_request, "operations.backup_sets.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup_sets (sid={sid10})")

        self.logger.info("Subscribing to operations.backup.delete...")
        sid10c = await message_bus_client._nats.subscribe(
            "operations.backup.delete",
            cb=make_handler(self.handle_operations_delete_backup_set_request, "operations.backup.delete.reply"),
        )
        self.logger.info(f"✅ Subscribed to operations.backup.delete (sid={sid10c})")

        self.logger.info("Subscribing to operations.backup.purge...")
        sid10d = await message_bus_client._nats.subscribe(
            "operations.backup.purge",
            cb=make_handler(self.handle_operations_purge_backup_set_request, "operations.backup.purge.reply"),
        )
        self.logger.info(f"✅ Subscribed to operations.backup.purge (sid={sid10d})")
        
        self.logger.info("Subscribing to scheduler.expected_runs_today...")
        sid11 = await message_bus_client._nats.subscribe(
            "scheduler.expected_runs_today",
            cb=make_handler(self.handle_scheduler_expected_runs_today_request, "scheduler.expected_runs_today.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.expected_runs_today (sid={sid11})")
        
        self.logger.info("Subscribing to system.metrics.all...")
        sid12 = await message_bus_client._nats.subscribe(
            "system.metrics.all",
            cb=make_handler(self.handle_system_metrics_all_request, "system.metrics.all.reply")
        )
        self.logger.info(f"✅ Subscribed to system.metrics.all (sid={sid12})")
        
        self.logger.info("Subscribing to system.overview...")
        sid13 = await message_bus_client._nats.subscribe(
            "system.overview",
            cb=make_handler(self.handle_system_overview_request, "system.overview.reply")
        )
        self.logger.info(f"✅ Subscribed to system.overview (sid={sid13})")
        
        self.logger.info("Subscribing to system.health...")
        sid14 = await message_bus_client._nats.subscribe(
            "system.health",
            cb=make_handler(self.handle_system_health_request, "system.health.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health (sid={sid14})")
        
        self.logger.info("Subscribing to system.health.services...")
        sid15 = await message_bus_client._nats.subscribe(
            "system.health.services",
            cb=make_handler(self.handle_system_health_services_request, "system.health.services.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.services (sid={sid15})")
        
        self.logger.info("Subscribing to system.health.issues...")
        sid16 = await message_bus_client._nats.subscribe(
            "system.health.issues",
            cb=make_handler(self.handle_system_health_issues_request, "system.health.issues.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.issues (sid={sid16})")
        
        self.logger.info("Subscribing to system.remediate.available...")
        sid17 = await message_bus_client._nats.subscribe(
            "system.remediate.available",
            cb=make_handler(self.handle_remediate_available_request, "system.remediate.available.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.available (sid={sid17})")
        
        self.logger.info("Subscribing to system.remediate.history...")
        sid18 = await message_bus_client._nats.subscribe(
            "system.remediate.history",
            cb=make_handler(self.handle_remediate_history_request, "system.remediate.history.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.history (sid={sid18})")

        self.logger.info("Subscribing to system.remediate.trigger...")
        sid18b = await message_bus_client._nats.subscribe(
            "system.remediate.trigger",
            cb=make_handler(self.handle_remediate_trigger_request, "system.remediate.trigger.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.trigger (sid={sid18b})")
        
        self.logger.info("Subscribing to system.health.check.connectivity...")
        sid19 = await message_bus_client._nats.subscribe(
            "system.health.check.connectivity",
            cb=make_handler(self.handle_health_check_connectivity_request, "system.health.check.connectivity.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.connectivity (sid={sid19})")
        
        self.logger.info("Subscribing to system.health.check.resources...")
        sid20 = await message_bus_client._nats.subscribe(
            "system.health.check.resources",
            cb=make_handler(self.handle_health_check_resources_request, "system.health.check.resources.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.resources (sid={sid20})")
        
        self.logger.info("Subscribing to system.health.check.models...")
        sid21 = await message_bus_client._nats.subscribe(
            "system.health.check.models",
            cb=make_handler(self.handle_health_check_models_request, "system.health.check.models.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.models (sid={sid21})")
        
        self.logger.info("Subscribing to system.health.check.ai_behaviour...")
        sid22 = await message_bus_client._nats.subscribe(
            "system.health.check.ai_behaviour",
            cb=make_handler(self.handle_health_check_ai_behaviour_request, "system.health.check.ai_behaviour.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.ai_behaviour (sid={sid22})")
        
        self.logger.info("Core NATS request handlers registered (scheduler, emotion, memory, kg, operations, system, health checks)")
        return
        self.logger.info("Subscribing to agency.connectivity.scan...")
        await message_bus_client._nats.subscribe("agency.connectivity.scan", cb=make_handler(self.handle_agency_connectivity_scan_request, "agency.connectivity.scan.reply"))
        
        self.logger.info("Subscribing to agency.tools.list...")
        await message_bus_client._nats.subscribe("agency.tools.list", cb=make_handler(self.handle_agency_tools_list_request, "agency.tools.list.reply"))
        
        self.logger.info("Subscribing to agency.tool.info...")
        await message_bus_client._nats.subscribe("agency.tool.info", cb=make_handler(self.handle_agency_tool_info_request, "agency.tool.info.reply"))
        
        self.logger.info("Subscribing to agency.tool.invoke...")
        await message_bus_client._nats.subscribe("agency.tool.invoke", cb=make_handler(self.handle_agency_tool_invoke_request, "agency.tool.invoke.reply"))
        
        self.logger.info("Subscribing to agency.reflection.runs...")
        await message_bus_client._nats.subscribe("agency.reflection.runs", cb=make_handler(self.handle_agency_reflection_runs_request, "agency.reflection.runs.reply"))
        
        self.logger.info("Subscribing to agency.reflection.lessons...")
        await message_bus_client._nats.subscribe("agency.reflection.lessons", cb=make_handler(self.handle_agency_reflection_lessons_request, "agency.reflection.lessons.reply"))
        
        self.logger.info("Subscribing to agency.reflection.self_model...")
        await message_bus_client._nats.subscribe("agency.reflection.self_model", cb=make_handler(self.handle_agency_reflection_self_model_request, "agency.reflection.self_model.reply"))
        
        self.logger.info("Subscribing to agency.skill.performance...")
        await message_bus_client._nats.subscribe("agency.skill.performance", cb=make_handler(self.handle_agency_skill_performance_request, "agency.skill.performance.reply"))
        
        self.logger.info("Subscribing to agency.reflection.summary...")
        await message_bus_client._nats.subscribe("agency.reflection.summary", cb=make_handler(self.handle_agency_reflection_summary_request, "agency.reflection.summary.reply"))
        
        self.logger.info("✅ Subscribed to all 26 agency endpoints")
        
        self.logger.info("Subscribing to operations.databases...")
        sid8 = await message_bus_client._nats.subscribe(
            "operations.databases",
            cb=make_handler(self.handle_operations_databases_request, "operations.databases.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.databases (sid={sid8})")

        self.logger.info("Subscribing to operations.databases.postgresql.schema...")
        sid8b = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.schema",
            cb=make_handler(
                self.handle_operations_postgresql_schema_request,
                "operations.databases.postgresql.schema.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.schema (sid={sid8b})")

        self.logger.info("Subscribing to operations.databases.postgresql.details...")
        sid8c = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.details",
            cb=make_handler(
                self.handle_operations_postgresql_details_request,
                "operations.databases.postgresql.details.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.details (sid={sid8c})")
        
        self.logger.info("Subscribing to operations.topology...")
        sid9 = await message_bus_client._nats.subscribe(
            "operations.topology",
            cb=make_handler(self.handle_operations_topology_request, "operations.topology.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.topology (sid={sid9})")
        
        self.logger.info("Subscribing to operations.backup.create...")
        sid10a = await message_bus_client._nats.subscribe(
            "operations.backup.create",
            cb=make_handler(self.handle_operations_create_backup_request, "operations.backup.create.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup.create (sid={sid10a})")
        
        self.logger.info("Subscribing to operations.backup_sets...")
        sid10 = await message_bus_client._nats.subscribe(
            "operations.backup_sets",
            cb=make_handler(self.handle_operations_backup_sets_request, "operations.backup_sets.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup_sets (sid={sid10})")
        
        self.logger.info("Subscribing to scheduler.expected_runs_today...")
        sid11 = await message_bus_client._nats.subscribe(
            "scheduler.expected_runs_today",
            cb=make_handler(self.handle_scheduler_expected_runs_today_request, "scheduler.expected_runs_today.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.expected_runs_today (sid={sid11})")
        
        self.logger.info("Subscribing to system.metrics.all...")
        sid12 = await message_bus_client._nats.subscribe(
            "system.metrics.all",
            cb=make_handler(self.handle_system_metrics_all_request, "system.metrics.all.reply")
        )
        self.logger.info(f"✅ Subscribed to system.metrics.all (sid={sid12})")
        
        self.logger.info("Subscribing to system.overview...")
        sid13 = await message_bus_client._nats.subscribe(
            "system.overview",
            cb=make_handler(self.handle_system_overview_request, "system.overview.reply")
        )
        self.logger.info(f"✅ Subscribed to system.overview (sid={sid13})")
        
        self.logger.info("Subscribing to system.health...")
        sid14 = await message_bus_client._nats.subscribe(
            "system.health",
            cb=make_handler(self.handle_system_health_request, "system.health.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health (sid={sid14})")
        
        self.logger.info("Subscribing to system.health.services...")
        sid15 = await message_bus_client._nats.subscribe(
            "system.health.services",
            cb=make_handler(self.handle_system_health_services_request, "system.health.services.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.services (sid={sid15})")
        
        self.logger.info("Subscribing to system.health.issues...")
        sid16 = await message_bus_client._nats.subscribe(
            "system.health.issues",
            cb=make_handler(self.handle_system_health_issues_request, "system.health.issues.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.issues (sid={sid16})")
        
        self.logger.info("Subscribing to system.remediate.available...")
        sid17 = await message_bus_client._nats.subscribe(
            "system.remediate.available",
            cb=make_handler(self.handle_remediate_available_request, "system.remediate.available.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.available (sid={sid17})")
        
        self.logger.info("Subscribing to system.remediate.history...")
        sid18 = await message_bus_client._nats.subscribe(
            "system.remediate.history",
            cb=make_handler(self.handle_remediate_history_request, "system.remediate.history.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.history (sid={sid18})")

        self.logger.info("Subscribing to system.remediate.trigger...")
        sid18b = await message_bus_client._nats.subscribe(
            "system.remediate.trigger",
            cb=make_handler(self.handle_remediate_trigger_request, "system.remediate.trigger.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.trigger (sid={sid18b})")
        
        self.logger.info("Subscribing to system.health.check.connectivity...")
        sid19 = await message_bus_client._nats.subscribe(
            "system.health.check.connectivity",
            cb=make_handler(self.handle_health_check_connectivity_request, "system.health.check.connectivity.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.connectivity (sid={sid19})")
        
        self.logger.info("Subscribing to system.health.check.resources...")
        sid20 = await message_bus_client._nats.subscribe(
            "system.health.check.resources",
            cb=make_handler(self.handle_health_check_resources_request, "system.health.check.resources.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.resources (sid={sid20})")
        
        self.logger.info("Subscribing to system.health.check.models...")
        sid21 = await message_bus_client._nats.subscribe(
            "system.health.check.models",
            cb=make_handler(self.handle_health_check_models_request, "system.health.check.models.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.models (sid={sid21})")
        
        self.logger.info("Subscribing to system.health.check.ai_behaviour...")
        sid22 = await message_bus_client._nats.subscribe(
            "system.health.check.ai_behaviour",
            cb=make_handler(self.handle_health_check_ai_behaviour_request, "system.health.check.ai_behaviour.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.ai_behaviour (sid={sid22})")
        
        self.logger.info("Core NATS request handlers registered (scheduler, emotion, memory, kg, operations, system, health checks)")
        sid22 = await message_bus_client._nats.subscribe(
            "system.health.check.ai_behaviour",
            cb=make_handler(self.handle_health_check_ai_behaviour_request, "system.health.check.ai_behaviour.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.ai_behaviour (sid={sid22})")
        
        self.logger.info("Core NATS request handlers registered (scheduler, emotion, memory, kg, operations, system, health checks)")
        self.logger.info("Subscribing to agency.connectivity.scan...")
        await message_bus_client._nats.subscribe("agency.connectivity.scan", cb=make_handler(self.handle_agency_connectivity_scan_request, "agency.connectivity.scan.reply"))
        
        self.logger.info("Subscribing to agency.tools.list...")
        await message_bus_client._nats.subscribe("agency.tools.list", cb=make_handler(self.handle_agency_tools_list_request, "agency.tools.list.reply"))
        
        self.logger.info("Subscribing to agency.tool.info...")
        await message_bus_client._nats.subscribe("agency.tool.info", cb=make_handler(self.handle_agency_tool_info_request, "agency.tool.info.reply"))
        
        self.logger.info("Subscribing to agency.tool.invoke...")
        await message_bus_client._nats.subscribe("agency.tool.invoke", cb=make_handler(self.handle_agency_tool_invoke_request, "agency.tool.invoke.reply"))
        
        self.logger.info("Subscribing to agency.reflection.runs...")
        await message_bus_client._nats.subscribe("agency.reflection.runs", cb=make_handler(self.handle_agency_reflection_runs_request, "agency.reflection.runs.reply"))
        
        self.logger.info("Subscribing to agency.reflection.lessons...")
        await message_bus_client._nats.subscribe("agency.reflection.lessons", cb=make_handler(self.handle_agency_reflection_lessons_request, "agency.reflection.lessons.reply"))
        
        self.logger.info("Subscribing to agency.reflection.self_model...")
        await message_bus_client._nats.subscribe("agency.reflection.self_model", cb=make_handler(self.handle_agency_reflection_self_model_request, "agency.reflection.self_model.reply"))
        
        self.logger.info("Subscribing to agency.skill.performance...")
        await message_bus_client._nats.subscribe("agency.skill.performance", cb=make_handler(self.handle_agency_skill_performance_request, "agency.skill.performance.reply"))
        
        self.logger.info("Subscribing to agency.reflection.summary...")
        await message_bus_client._nats.subscribe("agency.reflection.summary", cb=make_handler(self.handle_agency_reflection_summary_request, "agency.reflection.summary.reply"))
        
        self.logger.info("✅ Subscribed to all 26 agency endpoints")
        
        self.logger.info("Subscribing to operations.databases...")
        sid8 = await message_bus_client._nats.subscribe(
            "operations.databases",
            cb=make_handler(self.handle_operations_databases_request, "operations.databases.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.databases (sid={sid8})")

        self.logger.info("Subscribing to operations.databases.postgresql.schema...")
        sid8b = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.schema",
            cb=make_handler(
                self.handle_operations_postgresql_schema_request,
                "operations.databases.postgresql.schema.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.schema (sid={sid8b})")

        self.logger.info("Subscribing to operations.databases.postgresql.details...")
        sid8c = await message_bus_client._nats.subscribe(
            "operations.databases.postgresql.details",
            cb=make_handler(
                self.handle_operations_postgresql_details_request,
                "operations.databases.postgresql.details.reply",
            )
        )
        self.logger.info(f"✅ Subscribed to operations.databases.postgresql.details (sid={sid8c})")
        
        self.logger.info("Subscribing to operations.topology...")
        sid9 = await message_bus_client._nats.subscribe(
            "operations.topology",
            cb=make_handler(self.handle_operations_topology_request, "operations.topology.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.topology (sid={sid9})")
        
        self.logger.info("Subscribing to operations.backup.create...")
        sid10a = await message_bus_client._nats.subscribe(
            "operations.backup.create",
            cb=make_handler(self.handle_operations_create_backup_request, "operations.backup.create.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup.create (sid={sid10a})")
        
        self.logger.info("Subscribing to operations.backup_sets...")
        sid10 = await message_bus_client._nats.subscribe(
            "operations.backup_sets",
            cb=make_handler(self.handle_operations_backup_sets_request, "operations.backup_sets.reply")
        )
        self.logger.info(f"✅ Subscribed to operations.backup_sets (sid={sid10})")
        
        self.logger.info("Subscribing to scheduler.expected_runs_today...")
        sid11 = await message_bus_client._nats.subscribe(
            "scheduler.expected_runs_today",
            cb=make_handler(self.handle_scheduler_expected_runs_today_request, "scheduler.expected_runs_today.reply")
        )
        self.logger.info(f"✅ Subscribed to scheduler.expected_runs_today (sid={sid11})")
        
        self.logger.info("Subscribing to system.metrics.all...")
        sid12 = await message_bus_client._nats.subscribe(
            "system.metrics.all",
            cb=make_handler(self.handle_system_metrics_all_request, "system.metrics.all.reply")
        )
        self.logger.info(f"✅ Subscribed to system.metrics.all (sid={sid12})")
        
        self.logger.info("Subscribing to system.overview...")
        sid13 = await message_bus_client._nats.subscribe(
            "system.overview",
            cb=make_handler(self.handle_system_overview_request, "system.overview.reply")
        )
        self.logger.info(f"✅ Subscribed to system.overview (sid={sid13})")
        
        self.logger.info("Subscribing to system.health...")
        sid14 = await message_bus_client._nats.subscribe(
            "system.health",
            cb=make_handler(self.handle_system_health_request, "system.health.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health (sid={sid14})")
        
        self.logger.info("Subscribing to system.health.services...")
        sid15 = await message_bus_client._nats.subscribe(
            "system.health.services",
            cb=make_handler(self.handle_system_health_services_request, "system.health.services.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.services (sid={sid15})")
        
        self.logger.info("Subscribing to system.health.issues...")
        sid16 = await message_bus_client._nats.subscribe(
            "system.health.issues",
            cb=make_handler(self.handle_system_health_issues_request, "system.health.issues.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.issues (sid={sid16})")
        
        self.logger.info("Subscribing to system.remediate.available...")
        sid17 = await message_bus_client._nats.subscribe(
            "system.remediate.available",
            cb=make_handler(self.handle_remediate_available_request, "system.remediate.available.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.available (sid={sid17})")
        
        self.logger.info("Subscribing to system.remediate.history...")
        sid18 = await message_bus_client._nats.subscribe(
            "system.remediate.history",
            cb=make_handler(self.handle_remediate_history_request, "system.remediate.history.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.history (sid={sid18})")

        self.logger.info("Subscribing to system.remediate.trigger...")
        sid18b = await message_bus_client._nats.subscribe(
            "system.remediate.trigger",
            cb=make_handler(self.handle_remediate_trigger_request, "system.remediate.trigger.reply")
        )
        self.logger.info(f"✅ Subscribed to system.remediate.trigger (sid={sid18b})")
        
        self.logger.info("Subscribing to system.health.check.connectivity...")
        sid19 = await message_bus_client._nats.subscribe(
            "system.health.check.connectivity",
            cb=make_handler(self.handle_health_check_connectivity_request, "system.health.check.connectivity.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.connectivity (sid={sid19})")
        
        self.logger.info("Subscribing to system.health.check.resources...")
        sid20 = await message_bus_client._nats.subscribe(
            "system.health.check.resources",
            cb=make_handler(self.handle_health_check_resources_request, "system.health.check.resources.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.resources (sid={sid20})")
        
        self.logger.info("Subscribing to system.health.check.models...")
        sid21 = await message_bus_client._nats.subscribe(
            "system.health.check.models",
            cb=make_handler(self.handle_health_check_models_request, "system.health.check.models.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.models (sid={sid21})")
        
        self.logger.info("Subscribing to system.health.check.ai_behaviour...")
        sid22 = await message_bus_client._nats.subscribe(
            "system.health.check.ai_behaviour",
            cb=make_handler(self.handle_health_check_ai_behaviour_request, "system.health.check.ai_behaviour.reply")
        )
        self.logger.info(f"✅ Subscribed to system.health.check.ai_behaviour (sid={sid22})")
        
        self.logger.info("Core NATS request handlers registered (scheduler, emotion, memory, kg, operations, system, health checks)")
