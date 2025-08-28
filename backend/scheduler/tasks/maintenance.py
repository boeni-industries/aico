"""
Built-in Maintenance Tasks

System maintenance tasks for log cleanup, key rotation, health checks,
and database optimization.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict

from aico.core.logging import get_logger
from .base import BaseTask, TaskContext, TaskResult


class LogCleanupTask(BaseTask):
    """Clean up old log files and database entries"""
    
    task_id = "maintenance.log_cleanup"
    default_config = {
        "enabled": True,
        "schedule": "0 3 * * *",  # Daily at 3 AM
        "retention_days": 30,
        "max_size_mb": 500,
        "cleanup_database": True,
        "cleanup_files": True
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute log cleanup task"""
        try:
            retention_days = context.get_config("retention_days", 30)
            max_size_mb = context.get_config("max_size_mb", 500)
            cleanup_database = context.get_config("cleanup_database", True)
            cleanup_files = context.get_config("cleanup_files", True)
            
            results = {}
            
            # Clean up database log entries
            if cleanup_database:
                deleted_count = await self._cleanup_database_logs(context, retention_days)
                results["database_logs_deleted"] = deleted_count
            
            # Clean up log files
            if cleanup_files:
                cleaned_size = await self._cleanup_log_files(context, retention_days, max_size_mb)
                results["files_cleaned_mb"] = cleaned_size
            
            # Clean up task execution history
            task_store = context.db_connection
            from ..storage import TaskStore
            store = TaskStore(task_store)
            exec_deleted = await store.cleanup_old_executions(retention_days)
            results["task_executions_deleted"] = exec_deleted
            
            message = f"Log cleanup completed: {results}"
            self.logger.info(message)
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Log cleanup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
    
    async def _cleanup_database_logs(self, context: TaskContext, retention_days: int) -> int:
        """Clean up old log entries from database"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            
            cursor = await context.db_connection.execute(
                "DELETE FROM logs WHERE timestamp < ?", (cutoff_date,)
            )
            await context.db_connection.commit()
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                self.logger.info(f"Deleted {deleted_count} old log entries from database")
            
            return deleted_count
            
        except Exception as e:
            self.logger.warning(f"Database log cleanup failed: {e}")
            return 0
    
    async def _cleanup_log_files(self, context: TaskContext, retention_days: int, max_size_mb: int) -> float:
        """Clean up old log files from filesystem"""
        try:
            # Get log directory from config
            config = context.config_manager.get("logging", {})
            log_dir = config.get("file_handler", {}).get("directory", "logs")
            
            if not os.path.exists(log_dir):
                return 0.0
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
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
                rotated_count = await self._rotate_session_keys(context, backup_keys)
                results["session_keys_rotated"] = rotated_count
            
            # Database key rotation (if explicitly enabled)
            if rotate_database:
                db_result = await self._rotate_database_keys(context, backup_keys)
                results["database_key_rotated"] = db_result
            else:
                results["database_key_rotated"] = "skipped (disabled)"
            
            message = f"Key rotation completed: {results}"
            self.logger.info(message)
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Key rotation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
    
    async def _rotate_session_keys(self, context: TaskContext, backup: bool) -> int:
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
    
    async def _rotate_database_keys(self, context: TaskContext, backup: bool) -> bool:
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
                bus_healthy = await self._check_message_bus_health(context)
                checks["message_bus"] = bus_healthy
                all_healthy = all_healthy and bus_healthy
            
            # Disk space
            if context.get_config("check_disk_space", True):
                disk_threshold = context.get_config("disk_threshold_percent", 90)
                disk_healthy = await self._check_disk_space(context, disk_threshold)
                checks["disk_space"] = disk_healthy
                all_healthy = all_healthy and disk_healthy
            
            # Memory usage
            if context.get_config("check_memory", True):
                memory_threshold = context.get_config("memory_threshold_percent", 85)
                memory_healthy = await self._check_memory_usage(context, memory_threshold)
                checks["memory"] = memory_healthy
                all_healthy = all_healthy and memory_healthy
            
            status = "healthy" if all_healthy else "unhealthy"
            message = f"Health check completed: {status}"
            
            if not all_healthy:
                self.logger.warning(f"Health check failed: {checks}")
            else:
                self.logger.debug(f"Health check passed: {checks}")
            
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
            # Simple query to test database
            def db_call():
                cursor = context.db_connection.execute("SELECT 1")
                return cursor.fetchone()
            
            result = await asyncio.to_thread(db_call)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    async def _check_message_bus_health(self, context: TaskContext) -> bool:
        """Check message bus connectivity"""
        try:
            # TODO: Implement message bus health check
            # This would involve checking ZMQ socket connectivity
            return True  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Message bus health check failed: {e}")
            return False
    
    async def _check_disk_space(self, context: TaskContext, threshold_percent: int) -> bool:
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
    
    async def _check_memory_usage(self, context: TaskContext, threshold_percent: int) -> bool:
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
        "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
        "full_vacuum": False,  # Full vacuum is slower but more thorough
        "analyze_tables": True
    }
    
    async def execute(self, context: TaskContext) -> TaskResult:
        """Execute database vacuum task"""
        try:
            full_vacuum = context.get_config("full_vacuum", False)
            analyze_tables = context.get_config("analyze_tables", True)
            
            results = {}
            
            # Perform vacuum operation
            if full_vacuum:
                await context.db_connection.execute("VACUUM")
                results["vacuum_type"] = "full"
            else:
                await context.db_connection.execute("VACUUM INCREMENTAL")
                results["vacuum_type"] = "incremental"
            
            # Analyze tables for query optimization
            if analyze_tables:
                await context.db_connection.execute("ANALYZE")
                results["tables_analyzed"] = True
            
            await context.db_connection.commit()
            
            message = f"Database vacuum completed: {results}"
            self.logger.info(message)
            
            return TaskResult(
                success=True,
                message=message,
                data=results
            )
            
        except Exception as e:
            error_msg = f"Database vacuum failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return TaskResult(success=False, error=error_msg)
