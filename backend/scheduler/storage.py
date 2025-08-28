"""
Task Storage and Persistence

Provides database operations for scheduled tasks using AICO's encrypted libSQL.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict

from aico.core.logging import get_logger
from .tasks.base import TaskStatus, TaskResult


class TaskStore:
    """Database operations for scheduled tasks"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = get_logger("scheduler", "task_store")
    
    async def create_tables(self):
        """Create scheduler tables if they don't exist"""
        try:
            # Scheduled tasks table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    task_class TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    config TEXT,  -- JSON configuration
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Task execution history
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    result TEXT,  -- JSON TaskResult
                    error_message TEXT,
                    duration_seconds REAL,
                    FOREIGN KEY (task_id) REFERENCES scheduled_tasks (task_id)
                )
            """)
            
            # Task execution locks (for preventing concurrent runs)
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS task_locks (
                    task_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES scheduled_tasks (task_id)
                )
            """)
            
            # Create indexes for performance
            await self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions (task_id)")
            await self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_started_at ON task_executions (started_at)")
            await self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_locks_expires_at ON task_locks (expires_at)")
            
            await self.db.commit()
            self.logger.info("Scheduler database tables created/verified")
            
        except Exception as e:
            self.logger.error(f"Failed to create scheduler tables: {e}")
            raise
    
    async def upsert_task(self, task_id: str, task_class: str, schedule: str, 
                         config: Optional[Dict[str, Any]] = None, enabled: bool = True):
        """Insert or update a scheduled task"""
        try:
            config_json = json.dumps(config) if config else None
            now = datetime.now().isoformat()
            
            await self.db.execute("""
                INSERT INTO scheduled_tasks (task_id, task_class, schedule, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    task_class = excluded.task_class,
                    schedule = excluded.schedule,
                    config = excluded.config,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
            """, (task_id, task_class, schedule, config_json, enabled, now, now))
            
            await self.db.commit()
            self.logger.debug(f"Upserted task: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to upsert task {task_id}: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled task by ID"""
        try:
            cursor = await self.db.execute(
                "SELECT task_id, task_class, schedule, config, enabled, created_at, updated_at "
                "FROM scheduled_tasks WHERE task_id = ?", (task_id,)
            )
            row = await cursor.fetchone()
            
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
    
    async def list_tasks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all scheduled tasks"""
        try:
            query = """
                SELECT task_id, task_class, schedule, config, enabled, created_at, updated_at
                FROM scheduled_tasks
            """
            params = ()
            
            if enabled_only:
                query += " WHERE enabled = TRUE"
            
            query += " ORDER BY task_id"
            
            cursor = await self.db.execute(query, params)
            rows = await cursor.fetchall()
            
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
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task"""
        try:
            cursor = await self.db.execute("DELETE FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            await self.db.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                self.logger.info(f"Deleted task: {task_id}")
            else:
                self.logger.warning(f"Task not found for deletion: {task_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def set_task_enabled(self, task_id: str, enabled: bool) -> bool:
        """Enable or disable a task"""
        try:
            now = datetime.now().isoformat()
            cursor = await self.db.execute(
                "UPDATE scheduled_tasks SET enabled = ?, updated_at = ? WHERE task_id = ?",
                (enabled, now, task_id)
            )
            await self.db.commit()
            
            updated = cursor.rowcount > 0
            if updated:
                status = "enabled" if enabled else "disabled"
                self.logger.info(f"Task {task_id} {status}")
            
            return updated
            
        except Exception as e:
            self.logger.error(f"Failed to set task {task_id} enabled={enabled}: {e}")
            return False
    
    async def record_execution_start(self, task_id: str, execution_id: str) -> bool:
        """Record the start of a task execution"""
        try:
            now = datetime.now().isoformat()
            await self.db.execute("""
                INSERT INTO task_executions (task_id, execution_id, status, started_at)
                VALUES (?, ?, ?, ?)
            """, (task_id, execution_id, TaskStatus.RUNNING.value, now))
            
            await self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record execution start for {task_id}: {e}")
            return False
    
    async def record_execution_result(self, task_id: str, execution_id: str, 
                                    result: TaskResult, status: TaskStatus):
        """Record the completion of a task execution"""
        try:
            now = datetime.now().isoformat()
            result_json = json.dumps(result.to_dict())
            
            await self.db.execute("""
                UPDATE task_executions 
                SET status = ?, completed_at = ?, result = ?, error_message = ?, duration_seconds = ?
                WHERE task_id = ? AND execution_id = ?
            """, (
                status.value, now, result_json, result.error, result.duration_seconds,
                task_id, execution_id
            ))
            
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to record execution result for {task_id}: {e}")
    
    async def get_execution_history(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a task"""
        try:
            cursor = await self.db.execute("""
                SELECT execution_id, status, started_at, completed_at, result, error_message, duration_seconds
                FROM task_executions 
                WHERE task_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (task_id, limit))
            
            rows = await cursor.fetchall()
            history = []
            
            for row in rows:
                history.append({
                    'execution_id': row[0],
                    'status': row[1],
                    'started_at': row[2],
                    'completed_at': row[3],
                    'result': json.loads(row[4]) if row[4] else None,
                    'error_message': row[5],
                    'duration_seconds': row[6]
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get execution history for {task_id}: {e}")
            return []
    
    async def acquire_lock(self, task_id: str, execution_id: str, timeout_seconds: int = 3600) -> bool:
        """Acquire execution lock for a task"""
        try:
            now = datetime.now()
            expires_at = (now + timedelta(seconds=timeout_seconds)).isoformat()
            
            # Clean up expired locks first
            await self.db.execute("DELETE FROM task_locks WHERE expires_at < ?", (now.isoformat(),))
            
            # Try to acquire lock
            await self.db.execute("""
                INSERT INTO task_locks (task_id, execution_id, expires_at)
                VALUES (?, ?, ?)
            """, (task_id, execution_id, expires_at))
            
            await self.db.commit()
            return True
            
        except sqlite3.IntegrityError:
            # Lock already exists
            return False
        except Exception as e:
            self.logger.error(f"Failed to acquire lock for {task_id}: {e}")
            return False
    
    async def release_lock(self, task_id: str, execution_id: str) -> bool:
        """Release execution lock for a task"""
        try:
            cursor = await self.db.execute(
                "DELETE FROM task_locks WHERE task_id = ? AND execution_id = ?",
                (task_id, execution_id)
            )
            await self.db.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            self.logger.error(f"Failed to release lock for {task_id}: {e}")
            return False
    
    async def cleanup_old_executions(self, retention_days: int = 30):
        """Clean up old execution records"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            
            cursor = await self.db.execute(
                "DELETE FROM task_executions WHERE started_at < ?", (cutoff_date,)
            )
            await self.db.commit()
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old task execution records")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions: {e}")
            return 0
