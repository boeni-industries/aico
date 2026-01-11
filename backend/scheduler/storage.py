"""
Task Storage and Persistence

Provides database operations for scheduled tasks using AICO's encrypted libSQL.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict

from aico.core.logging import get_logger
from .tasks.base import TaskStatus, TaskResult


class TaskStore:
    """Database operations for scheduled tasks"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = get_logger("backend.scheduler.task_store")
    
    def verify_tables_exist(self):
        """Verify that the required scheduler tables exist in the database."""
        required_tables = {"scheduler_tasks", "scheduler_task_executions", "scheduler_task_locks"}
        try:
            cursor = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            missing_tables = required_tables - existing_tables

            if missing_tables:
                error_message = (
                    f"Database schema is out of date. Missing required scheduler tables: {', '.join(missing_tables)}. "
                    f"Please ensure the database is initialized correctly using the schemas defined in "
                    f"'shared/aico/data/schemas/core.py'. You may need to run database migrations."
                )
                self.logger.critical(error_message)
                print(f"\n*** DATABASE SCHEMA ERROR ***\n{error_message}\n")
                raise SystemExit(1)  # Fail loudly

            self.logger.debug("Scheduler database tables verified successfully.")

        except Exception as e:
            self.logger.error(f"Failed to verify scheduler tables: {e}")
            raise
    
    def upsert_task(self, task_id: str, task_class: str, schedule: str, 
                         config: Optional[Dict[str, Any]] = None, enabled: bool = True):
        """Insert or update a scheduled task"""
        try:
            config_json = json.dumps(config) if config else None
            now = datetime.now(timezone.utc).isoformat()
            
            self.db.execute("""
                INSERT INTO scheduler_tasks (task_id, task_class, schedule, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    task_class = excluded.task_class,
                    schedule = excluded.schedule,
                    config = excluded.config,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
            """, (task_id, task_class, schedule, config_json, enabled, now, now))
            
            self.db.commit()
            self.logger.debug(f"Upserted task: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to upsert task {task_id}: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled task by ID"""
        try:
            cursor = self.db.execute(
                "SELECT task_id, task_class, schedule, config, enabled, created_at, updated_at "
                "FROM scheduler_tasks WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'task_id': row[0],
                'task_class': row[1], 
                'schedule': row[2],
                'config': json.loads(row[3]) if row[3] else {},
                'enabled': bool(row[4]),
                'created_at': row[5],
                'updated_at': row[6]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    def list_tasks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all scheduled tasks"""
        try:
            query = """
                SELECT task_id, task_class, schedule, config, enabled, created_at, updated_at
                FROM scheduler_tasks
            """
            params = ()
            
            if enabled_only:
                query += " WHERE enabled = TRUE"
            
            query += " ORDER BY task_id"
            
            cursor = self.db.execute(query, params)
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'task_id': row[0],
                    'task_class': row[1],
                    'schedule': row[2], 
                    'config': json.loads(row[3]) if row[3] else {},
                    'enabled': bool(row[4]),
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"Failed to list tasks: {e}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task"""
        try:
            cursor = self.db.execute("DELETE FROM scheduler_tasks WHERE task_id = ?", (task_id,))
            self.db.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                self.logger.info(f"Deleted task: {task_id}")
            else:
                self.logger.warning(f"Task not found for deletion: {task_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    def set_task_enabled(self, task_id: str, enabled: bool) -> bool:
        """Enable or disable a task"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            cursor = self.db.execute(
                "UPDATE scheduler_tasks SET enabled = ?, updated_at = ? WHERE task_id = ?",
                (enabled, now, task_id)
            )
            self.db.commit()
            
            updated = cursor.rowcount > 0
            if updated:
                status = "enabled" if enabled else "disabled"
                self.logger.info(f"Task {task_id} {status}")
            
            return updated
            
        except Exception as e:
            self.logger.error(f"Failed to set task {task_id} enabled={enabled}: {e}")
            return False
    
    def record_execution_start(self, task_id: str, execution_id: str) -> bool:
        """Record the start of a task execution"""
        try:
            now = datetime.now(timezone.utc).isoformat()  # Use UTC with timezone info
            self.db.execute("""
                INSERT INTO scheduler_task_executions (task_id, execution_id, status, started_at)
                VALUES (?, ?, ?, ?)
            """, (task_id, execution_id, TaskStatus.RUNNING.value, now))
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record execution start for {task_id}: {e}")
            return False
    
    def record_execution_result(self, task_id: str, execution_id: str, 
                                    result: TaskResult, status: TaskStatus):
        """Record the completion of a task execution"""
        try:
            now = datetime.now(timezone.utc).isoformat()  # Use UTC with timezone info
            result_json = json.dumps(result.to_dict())
            
            self.db.execute("""
                UPDATE scheduler_task_executions 
                SET status = ?, completed_at = ?, result = ?, error_message = ?, duration_seconds = ?
                WHERE task_id = ? AND execution_id = ?
            """, (
                status.value, now, result_json, result.error, result.duration_seconds,
                task_id, execution_id
            ))
            
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to record execution result for {task_id}: {e}")
    
    def _parse_execution_row(self, row: tuple, include_task_id: bool = False) -> Dict[str, Any]:
        """Parse execution row from database (DRY helper)"""
        if include_task_id:
            return {
                'task_id': row[0],
                'execution_id': row[1],
                'status': row[2],
                'started_at': row[3],
                'completed_at': row[4],
                'result': json.loads(row[5]) if row[5] else None,
                'error_message': row[6],
                'duration_seconds': row[7]
            }
        else:
            return {
                'execution_id': row[0],
                'status': row[1],
                'started_at': row[2],
                'completed_at': row[3],
                'result': json.loads(row[4]) if row[4] else None,
                'error_message': row[5],
                'duration_seconds': row[6]
            }
    
    def get_execution_history(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a task"""
        try:
            cursor = self.db.execute("""
                SELECT execution_id, status, started_at, completed_at, result, error_message, duration_seconds
                FROM scheduler_task_executions 
                WHERE task_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (task_id, limit))
            
            return [self._parse_execution_row(row) for row in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"Failed to get execution history for {task_id}: {e}")
            return []
    
    def get_all_executions_in_range(self, start_time: str, end_time: str, limit: int = 10000) -> List[Dict[str, Any]]:
        """Get all task executions within a time range across all tasks"""
        try:
            cursor = self.db.execute("""
                SELECT task_id, execution_id, status, started_at, completed_at, result, error_message, duration_seconds
                FROM scheduler_task_executions 
                WHERE started_at >= ? AND started_at < ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (start_time, end_time, limit))
            
            return [self._parse_execution_row(row, include_task_id=True) for row in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"Failed to get executions in range: {e}")
            return []
    
    async def acquire_lock(self, task_id: str, execution_id: str, timeout_seconds: int = 3600) -> bool:
        """Acquire execution lock for a task"""
        import asyncio
        import os
        
        def _sync_acquire():
            try:
                now = datetime.now(timezone.utc)
                expires_at = (now + timedelta(seconds=timeout_seconds)).isoformat()
                
                # Clean up expired locks first (best-effort)
                deleted = self.db.execute("DELETE FROM scheduler_task_locks WHERE expires_at < ?", (now.isoformat(),))

                # Atomic acquisition:
                # - If no lock exists: insert succeeds.
                # - If lock exists and is expired: update succeeds.
                # - If lock exists and is still valid: update does NOT happen (WHERE clause), rowcount==0.
                cursor = self.db.execute(
                    """
                    INSERT INTO scheduler_task_locks (task_id, execution_id, expires_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        execution_id = excluded.execution_id,
                        expires_at = excluded.expires_at
                    WHERE scheduler_task_locks.expires_at < ?
                    """,
                    (task_id, execution_id, expires_at, now.isoformat()),
                )

                self.db.commit()

                # If a non-expired lock existed, the WHERE clause prevents update.
                if hasattr(cursor, 'rowcount') and cursor.rowcount == 0:
                    if os.getenv('AICO_DETACH_MODE') == 'false':
                        existing = self.db.execute(
                            "SELECT execution_id, expires_at FROM scheduler_task_locks WHERE task_id = ?",
                            (task_id,),
                        ).fetchone()
                    return False

                return True
                
            except sqlite3.IntegrityError:
                # Lock already exists
                return False
            except Exception as e:
                self.logger.error(f"Failed to acquire lock for {task_id}: {e}")
                return False
        
        return await asyncio.to_thread(_sync_acquire)
    
    async def release_lock(self, task_id: str, execution_id: str) -> bool:
        """Release execution lock for a task"""
        import asyncio
        
        def _sync_release():
            try:
                cursor = self.db.execute(
                    "DELETE FROM scheduler_task_locks WHERE task_id = ? AND execution_id = ?",
                    (task_id, execution_id)
                )
                self.db.commit()
                
                return cursor.rowcount > 0
                
            except Exception as e:
                self.logger.error(f"Failed to release lock for {task_id}: {e}")
                return False
        
        return await asyncio.to_thread(_sync_release)
    
    def cleanup_old_executions(self, retention_days: int = 30):
        """Clean up old execution records"""
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
            
            cursor = self.db.execute(
                "DELETE FROM scheduler_task_executions WHERE started_at < ?", (cutoff_date,)
            )
            self.db.commit()
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old task execution records")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions: {e}")
            return 0
