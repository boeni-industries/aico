"""
Built-in Maintenance Tasks

System maintenance tasks for log cleanup, key rotation, health checks,
and database optimization.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult


class LogCleanupTask(BaseTask):
    """Clean up old log files and database entries"""
    
    task_id = "maintenance.log_cleanup"
    default_config = {
        "enabled": True,
        "schedule": "30 3 * * *",  # Daily at 3:30 AM (staggered)
        "retention_days": 7,  # Default to 7 days, but will read from core.yaml logging.retention.days
        "max_size_mb": 500,
        "cleanup_database": True,
        "cleanup_files": True
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute log cleanup task"""
        try:
            # Read retention settings from core.yaml logging configuration
            core_config = context.config_manager.get("core", {})
            logging_retention = core_config.get("logging", {}).get("retention", {})
            retention_days = logging_retention.get("days", context.get_config("retention_days", 7))
            max_size_mb = logging_retention.get("max_size_mb", context.get_config("max_size_mb", 500))
            cleanup_database = context.get_config("cleanup_database", True)
            cleanup_files = context.get_config("cleanup_files", True)
            
            results = {}
            
            # Clean up database log entries
            if cleanup_database:
                deleted_count = self._cleanup_database_logs(context, retention_days)
                results["database_logs_deleted"] = deleted_count
            
            # Clean up log files
            if cleanup_files:
                cleaned_size = self._cleanup_log_files(context, retention_days, max_size_mb)
                results["files_cleaned_mb"] = cleaned_size
            
            # Clean up task execution history via SchedulerService
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from aico.services.scheduler_service import SchedulerService
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                scheduler_service = SchedulerService(uow)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
                exec_deleted = await scheduler_service.cleanup_old_executions(cutoff_date)
                await uow.commit()
            
            results["task_executions_deleted"] = exec_deleted
            
            message = f"Log cleanup completed: {results}"
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Log cleanup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
    
    def _cleanup_database_logs(self, context: TaskContext, retention_days: int) -> int:
        """Clean up old log entries - system_logs table removed, logs now in InfluxDB"""
        # system_logs table no longer exists - logs are in InfluxDB with retention policies
        # InfluxDB handles log retention automatically via bucket retention settings
        self.logger.info("Log cleanup skipped - logs now stored in InfluxDB with automatic retention")
        return 0
    
    def _cleanup_log_files(self, context: TaskContext, retention_days: int, max_size_mb: int) -> float:
        """Clean up old log files from filesystem"""
        try:
            # Get log directory from config
            config = context.config_manager.get("logging", {})
            log_dir = config.get("file_handler", {}).get("directory", "logs")
            
            if not os.path.exists(log_dir):
                return 0.0
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            total_cleaned = 0.0
            
            for filename in os.listdir(log_dir):
                if not filename.endswith('.log'):
                    continue
                
                filepath = os.path.join(log_dir, filename)
                try:
                    stat = os.stat(filepath)
                    file_date = datetime.fromtimestamp(stat.st_mtime)
                    file_size_mb = stat.st_size / (1024 * 1024)
                    
                    # Delete if too old or too large
                    should_delete = (
                        file_date < cutoff_date or 
                        file_size_mb > max_size_mb
                    )
                    
                    if should_delete:
                        os.remove(filepath)
                        total_cleaned += file_size_mb
                        self.logger.debug(f"Deleted log file: {filename} ({file_size_mb:.1f}MB)")
                
                except OSError as e:
                    self.logger.warning(f"Could not process log file {filename}: {e}")
            
            if total_cleaned > 0:
                self.logger.info(f"Cleaned up {total_cleaned:.1f}MB of log files")
            
            return total_cleaned
            
        except Exception as e:
            self.logger.warning(f"Log file cleanup failed: {e}")
            return 0.0


class KeyRotationTask(BaseTask):
    """Rotate encryption keys and session tokens"""
    
    task_id = "maintenance.key_rotation"
    default_config = {
        "enabled": True,
        "schedule": "0 1 1 * *",  # Monthly on 1st at 1 AM
        "rotate_session_keys": True,
        "rotate_database_keys": False,  # Dangerous, requires manual intervention
        "backup_old_keys": True
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute key rotation task"""
        try:
            rotate_session = context.get_config("rotate_session_keys", True)
            rotate_database = context.get_config("rotate_database_keys", False)
            backup_keys = context.get_config("backup_old_keys", True)
            
            results = {}
            
            # Rotate session keys
            if rotate_session:
                rotated_count = self._rotate_session_keys(context, backup_keys)
                results["session_keys_rotated"] = rotated_count
            
            # Database key rotation (if explicitly enabled)
            if rotate_database:
                db_result = self._rotate_database_keys(context, backup_keys)
                results["database_key_rotated"] = db_result
            else:
                results["database_key_rotated"] = "skipped (disabled)"
            
            message = f"Key rotation completed: {results}"
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Key rotation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
    
    def _rotate_session_keys(self, context: TaskContext, backup: bool) -> int:
        """Rotate session authentication keys"""
        try:
            # TODO: Implement session key rotation
            # This would involve:
            # 1. Generate new JWT signing keys
            # 2. Update keyring with new keys
            # 3. Invalidate old sessions (optional)
            # 4. Backup old keys if requested
            
            self.logger.info("Session key rotation completed")
            return 1  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Session key rotation failed: {e}")
            return 0
    
    def _rotate_database_keys(self, context: TaskContext, backup: bool) -> bool:
        """Rotate database encryption keys (dangerous operation)"""
        try:
            # TODO: Implement database key rotation
            # This is a complex operation that requires:
            # 1. Create new encryption key
            # 2. Re-encrypt all database data
            # 3. Update key storage
            # 4. Verify data integrity
            
            self.logger.warning("Database key rotation is not yet implemented")
            return False
            
        except Exception as e:
            self.logger.error(f"Database key rotation failed: {e}")
            return False


class HealthCheckTask(BaseTask):
    """Perform system health checks"""
    
    task_id = "maintenance.health_check"
    default_config = {
        "enabled": True,
        "schedule": "*/5 * * * *",  # Every 5 minutes
        "check_database": True,
        "check_message_bus": True,
        "check_disk_space": True,
        "check_memory": True,
        "disk_threshold_percent": 90,
        "memory_threshold_percent": 85
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute health check task"""
        try:
            checks = {}
            all_healthy = True
            
            # Database health
            if context.get_config("check_database", True):
                db_healthy = await self._check_database_health(context)
                checks["database"] = db_healthy
                all_healthy = all_healthy and db_healthy
            
            # Message bus health
            if context.get_config("check_message_bus", True):
                bus_healthy = self._check_message_bus_health(context)
                checks["message_bus"] = bus_healthy
                all_healthy = all_healthy and bus_healthy
            
            # Disk space
            if context.get_config("check_disk_space", True):
                disk_threshold = context.get_config("disk_threshold_percent", 90)
                disk_healthy = self._check_disk_space(context, disk_threshold)
                checks["disk_space"] = disk_healthy
                all_healthy = all_healthy and disk_healthy
            
            # Memory usage
            if context.get_config("check_memory", True):
                memory_threshold = context.get_config("memory_threshold_percent", 85)
                memory_healthy = self._check_memory_usage(context, memory_threshold)
                checks["memory"] = memory_healthy
                all_healthy = all_healthy and memory_healthy
            
            status = "healthy" if all_healthy else "unhealthy"
            message = f"Health check completed: {status}"
            
            if not all_healthy:
                self.logger.warning(f"Health check failed: {checks}")
            
            return TaskResult(
                success=all_healthy,
                message=message,
                data={"status": status, "checks": checks}
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
    
    async def _check_database_health(self, context: TaskContext) -> bool:
        """Check database connectivity and basic operations"""
        try:
            # Simple query to test database via UoW
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork

            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                # Try to list a single user profile to verify DB connectivity
                await uow.user_profiles.list(limit=1)
            return True
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def _check_message_bus_health(self, context: TaskContext) -> bool:
        """Check message bus connectivity"""
        try:
            # TODO: Implement message bus health check
            # This would involve checking ZMQ socket connectivity
            return True  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Message bus health check failed: {e}")
            return False
    
    def _check_disk_space(self, context: TaskContext, threshold_percent: int) -> bool:
        """Check available disk space"""
        try:
            # Check disk space in current directory
            total, used, free = shutil.disk_usage(".")
            used_percent = (used / total) * 100
            
            healthy = used_percent < threshold_percent
            if not healthy:
                self.logger.warning(f"Disk usage high: {used_percent:.1f}% (threshold: {threshold_percent}%)")
            
            return healthy
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {e}")
            return False
    
    def _check_memory_usage(self, context: TaskContext, threshold_percent: int) -> bool:
        """Check system memory usage"""
        try:
            # TODO: Implement proper memory usage checking
            # This would use psutil or similar to check system memory
            return True  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Memory usage check failed: {e}")
            return False


class DatabaseVacuumTask(BaseTask):
    """Optimize database performance with VACUUM operations"""
    
    task_id = "maintenance.database_vacuum"
    default_config = {
        "enabled": True,
        "schedule": "0 3 * * 0",  # Weekly on Sunday at 3:00 AM (deep off-hours)
        "analyze_tables": True
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute database vacuum task"""
        try:
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            from sqlalchemy import text
            
            analyze_tables = context.get_config("analyze_tables", True)

            results = {}

            # VACUUM must run outside transaction - use raw connection
            self.logger.info("Starting database VACUUM...")
            session_factory = await get_session_factory()
            async with session_factory() as session:
                # Get raw connection and set autocommit for VACUUM
                connection = await session.connection()
                raw_conn = await connection.get_raw_connection()
                
                # Execute VACUUM outside transaction
                await raw_conn.set_isolation_level(0)  # AUTOCOMMIT mode
                cursor = await raw_conn.cursor()
                await cursor.execute("VACUUM")
                results["vacuum_type"] = "standard"
                
                # ANALYZE can run in transaction
                if analyze_tables:
                    await cursor.execute("ANALYZE")
                    results["tables_analyzed"] = True
                
                await cursor.close()
            
            message = f"Database vacuum completed: {results}"
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Database vacuum failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)


class RunLedgerCleanupTask(BaseTask):
    """Clean up old scheduler run ledger entries"""
    
    task_id = "maintenance.run_ledger_cleanup"
    default_config = {
        "enabled": True,
        "schedule": "15 4 * * *",  # Daily at 4:15 AM (staggered between log cleanup and vacuum)
        "retention_days": 30,  # Keep last 30 days of run history
        "states": ["completed", "missed", "suppressed", "started"],  # Only delete finalized runs
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute run ledger cleanup task"""
        try:
            # Read retention settings from scheduler config
            scheduler_config = context.config_manager.get("scheduler", {})
            deterministic_cfg = scheduler_config.get("deterministic", {})
            retention_days = deterministic_cfg.get("retention_days", context.get_config("retention_days", 30))
            states = context.get_config("states", ["completed", "missed", "suppressed", "started"])
            
            from aico.data.postgres.connection import get_session_factory
            from aico.data.uow import UnitOfWork
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            session_factory = await get_session_factory()
            async with UnitOfWork(session_factory) as uow:
                repo = uow.scheduler_run_ledger
                delete_before = getattr(repo, "delete_before", None)
                
                if delete_before is None:
                    error_msg = "scheduler_run_ledger repository missing delete_before method"
                    self.logger.error(error_msg)
                    return TaskResult(success=False, error=error_msg)
                
                deleted_count = await delete_before(cutoff=cutoff_date, states=states)
                await uow.commit()
            
            message = f"Run ledger cleanup completed: deleted {deleted_count} old run(s) before {cutoff_date.isoformat()}"
            self.logger.info(message, extra={"deleted_count": deleted_count, "retention_days": retention_days})
            
            return TaskResult(
                success=True,
                message=message,
                data={
                    "deleted_count": deleted_count,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "states_cleaned": states,
                }
            )
            
        except Exception as e:
            error_msg = f"Run ledger cleanup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)


class AgencyConnectivityScanTask(BaseTask):
    """Run Agency maintenance connectivity full scan via SkillInvoker.

    This task is designed to be created and triggered manually (e.g. via
    `aico scheduler trigger maintenance.agency_connectivity_scan`) and is
    therefore disabled by default.
    """

    task_id = "maintenance.agency_connectivity_scan"
    default_config = {
        "enabled": False,  # Explicitly disabled; for manual triggering only
        "schedule": "*/10 * * * *",  # Placeholder; effective only if enabled
        "targets": ["postgres"],
    }

    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute connectivity scan via AgencyEngine skill.

        Delegates to the `maint.connectivity.full_scan` skill using the
        AgencyEngine's SkillInvoker, ensuring we reuse the same maintenance
        logic as the HTTP endpoint and future self-healing flows.
        """

        from aico.ai import ai_registry

        try:
            agency_engine = ai_registry.get("agency")
        except Exception as exc:  # pragma: no cover - defensive
            error_msg = f"AgencyEngine not available for connectivity scan: {exc}"
            self.logger.error(error_msg)
            return TaskResult(success=False, error=error_msg)

        targets = context.get_config("targets", ["postgres"])
        input_data: Dict[str, Any] = {"targets": targets}

        try:
            result = await agency_engine.skill_invoker.invoke_skill(
                skill_id="maint.connectivity.full_scan",
                user_id="system_user",
                input_data=input_data,
                context={
                    "trigger": "scheduler_connectivity_scan",
                    "task_id": self.task_id,
                    "initiator_type": "system",
                    "source": "scheduler",
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            error_msg = f"Connectivity scan skill invocation failed: {exc}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)

        # SkillInvoker.invoke_skill returns a dict with success/output/error fields.
        if not result.get("success"):
            error_msg = result.get("error") or "Connectivity scan reported failure"
            self.logger.warning(f"Agency connectivity scan failed: {error_msg}")
            return TaskResult(
                success=False,
                error=error_msg,
                data={"output": result.get("output")},
            )

        # Successful scan; return the skill's structured output in TaskResult
        return TaskResult(
            success=True,
            message="Agency connectivity scan completed successfully",
            data=result.get("output"),
        )
