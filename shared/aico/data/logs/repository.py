"""
Log Repository for database operations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from aico.core.logging import get_logger
from aico.data import LibSQLConnection


class LogRepository:
    """Repository for log data operations"""
    
    def __init__(self, db_connection: LibSQLConnection):
        self.db = db_connection
        self.logger = get_logger("log_repository", "core")
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure log tables exist"""
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    subsystem TEXT,
                    module TEXT,
                    message TEXT NOT NULL,
                    extra_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_subsystem ON logs(subsystem)
            """)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to create log tables: {e}")
    
    def query_logs(self, 
                   limit: int = 50, 
                   offset: int = 0,
                   level: Optional[str] = None,
                   subsystem: Optional[str] = None,
                   module: Optional[str] = None,
                   since: Optional[datetime] = None,
                   until: Optional[datetime] = None,
                   search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query logs with filters"""
        
        query = "SELECT * FROM logs WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = ?"
            params.append(level)
            
        if subsystem:
            query += " AND subsystem = ?"
            params.append(subsystem)
            
        if module:
            query += " AND module = ?"
            params.append(module)
            
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
            
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
            
        if search:
            query += " AND message LIKE ?"
            params.append(f"%{search}%")
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            cursor = self.db.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                logs.append({
                    'id': str(row[0]),  # Convert to string
                    'timestamp': row[1],
                    'level': row[2],
                    'subsystem': row[3] or 'unknown',  # Handle None
                    'module': row[4] or 'unknown',     # Handle None
                    'function': 'unknown',             # Add required field
                    'message': row[5],
                    'topic': None,                     # Add optional field
                    'extra_data': {} if row[6] is None else {'raw': row[6]},  # Convert to dict
                    'created_at': row[7]
                })
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Failed to query logs: {e}")
            return []
    
    def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """Get specific log entry by ID"""
        try:
            cursor = self.db.execute("SELECT * FROM logs WHERE id = ?", [log_id])
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': str(row[0]),  # Convert to string
                    'timestamp': row[1],
                    'level': row[2],
                    'subsystem': row[3] or 'unknown',  # Handle None
                    'module': row[4] or 'unknown',     # Handle None
                    'function': 'unknown',             # Add required field
                    'message': row[5],
                    'topic': None,                     # Add optional field
                    'extra_data': {} if row[6] is None else {'raw': row[6]},  # Convert to dict
                    'created_at': row[7]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get log {log_id}: {e}")
            return None
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        try:
            # Total logs
            cursor = self.db.execute("SELECT COUNT(*) FROM logs")
            total_logs = cursor.fetchone()[0]
            
            # Logs by level
            cursor = self.db.execute("""
                SELECT level, COUNT(*) 
                FROM logs 
                GROUP BY level
            """)
            levels = dict(cursor.fetchall())
            
            # Recent logs (last 24 hours)
            cursor = self.db.execute("""
                SELECT COUNT(*) 
                FROM logs 
                WHERE timestamp >= datetime('now', '-1 day', 'utc')
            """)
            recent_logs = cursor.fetchone()[0]
            
            return {
                'total_logs': total_logs,
                'levels': levels,
                'recent_logs': recent_logs
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get log stats: {e}")
            return {
                'total_logs': 0,
                'levels': {},
                'recent_logs': 0
            }
    
    def add_log(self, level: str, message: str, subsystem: str = None, 
                module: str = None, extra_data: str = None) -> bool:
        """Add a log entry"""
        try:
            self.db.execute("""
                INSERT INTO logs (timestamp, level, subsystem, module, message, extra_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
                level,
                subsystem,
                module,
                message,
                extra_data
            ])
            self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add log: {e}")
            return False
    
    def count_logs(self, 
                   level: Optional[str] = None,
                   subsystem: Optional[str] = None,
                   module: Optional[str] = None,
                   since: Optional[datetime] = None,
                   until: Optional[datetime] = None,
                   search: Optional[str] = None) -> int:
        """Count logs with filters"""
        
        query = "SELECT COUNT(*) FROM logs WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = ?"
            params.append(level)
            
        if subsystem:
            query += " AND subsystem = ?"
            params.append(subsystem)
            
        if module:
            query += " AND module = ?"
            params.append(module)
            
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
            
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
            
        if search:
            query += " AND message LIKE ?"
            params.append(f"%{search}%")
        
        try:
            cursor = self.db.execute(query, params)
            return cursor.fetchone()[0]
            
        except Exception as e:
            self.logger.error(f"Failed to count logs: {e}")
            return 0
