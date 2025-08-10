"""
AICO Unified Logging System

Provides unified logging infrastructure for all AICO subsystems with:
- Configuration-driven behavior
- Database-only storage (no file logging)
- Bootstrap buffering for early logging
- Multi-layer fallback mechanisms
- ZeroMQ message bus integration
"""

import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import inspect

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False


@dataclass
class LogEntry:
    """Structured log entry matching our unified schema"""
    timestamp: str
    level: str
    subsystem: str
    module: str
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    topic: str = ""
    message: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class AICOLogger:
    """Main logger class with bootstrap buffering and fallback mechanisms"""
    
    def __init__(self, subsystem: str, module: str, config_manager, transport=None):
        self.subsystem = subsystem
        self.module = module
        self.config = config_manager
        self.transport = transport
        self._bootstrap_buffer: List[LogEntry] = []
        self._db_ready = False
        self._max_buffer_size = self.config.get("logging.bootstrap.buffer_size", 100)
        
    def _create_log_entry(self, level: str, message: str, **kwargs) -> LogEntry:
        """Create a structured log entry with automatic context detection"""
        
        # Get caller information automatically
        frame = inspect.currentframe().f_back.f_back  # Skip this method and the calling log method
        function_name = frame.f_code.co_name if frame else None
        file_path = frame.f_code.co_filename if frame else None
        line_number = frame.f_lineno if frame else None
        
        # Clean up file path (just filename, not full path)
        if file_path:
            file_path = Path(file_path).name
            
        return LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            subsystem=self.subsystem,
            module=self.module,
            function_name=function_name,
            file_path=file_path,
            line_number=line_number,
            topic=kwargs.get("topic", f"{self.subsystem}.{self.module}"),
            message=message,
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_id"),
            trace_id=kwargs.get("trace_id"),
            extra=kwargs.get("extra")
        )
    
    def _should_log(self, level: str) -> bool:
        """Check if log level should be recorded based on configuration"""
        # Get configured log level for this subsystem/module
        default_level = self.config.get("logging.levels.default", "INFO")
        subsystem_level = self.config.get(f"logging.levels.subsystems.{self.subsystem}", default_level)
        module_level = self.config.get(f"logging.levels.modules.{self.module}", subsystem_level)
        
        # Simple level hierarchy: DEBUG < INFO < WARNING < ERROR
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        return levels.get(level, 1) >= levels.get(module_level, 1)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        if not self._should_log(level):
            return
            
        log_entry = self._create_log_entry(level, message, **kwargs)
        
        if not self._db_ready:
            # Buffer logs during bootstrap
            self._bootstrap_buffer.append(log_entry)
            if len(self._bootstrap_buffer) > self._max_buffer_size:
                self._bootstrap_buffer.pop(0)  # Remove oldest
            self._try_fallback_logging(log_entry)
        else:
            # Normal database logging
            self._send_to_database(log_entry)
    
    def _try_fallback_logging(self, log_entry: LogEntry):
        """Multi-layer fallback for when database isn't ready"""
        
        # Layer 1: Console output (always available)
        if self.config.get("logging.bootstrap.fallback_console", True):
            print(f"[{log_entry.timestamp}] {log_entry.level} "
                  f"{log_entry.subsystem}.{log_entry.module}: {log_entry.message}")
        
        # Layer 2: Temporary file (if configured)
        if self.config.get("logging.bootstrap.fallback_temp_file", False):
            self._write_to_temp_file(log_entry)
    
    def _write_to_temp_file(self, log_entry: LogEntry):
        """Write to temporary file as fallback"""
        try:
            temp_log_path = Path.home() / ".aico" / "bootstrap.log"
            temp_log_path.parent.mkdir(exist_ok=True)
            with open(temp_log_path, "a", encoding="utf-8") as f:
                f.write(log_entry.to_json() + "\n")
        except Exception:
            pass  # Silent fallback failure
    
    def _send_to_database(self, log_entry: LogEntry):
        """Send log entry to database via transport"""
        if self.transport:
            try:
                self.transport.send_log(log_entry)
            except Exception as e:
                # Fallback to console if transport fails
                print(f"[LOG TRANSPORT ERROR] {log_entry.level} "
                      f"{log_entry.subsystem}.{log_entry.module}: {log_entry.message}")
    
    def mark_database_ready(self):
        """Called after database initialization to flush bootstrap buffer"""
        self._db_ready = True
        # Flush bootstrap buffer to database
        for buffered_log in self._bootstrap_buffer:
            self._send_to_database(buffered_log)
        self._bootstrap_buffer.clear()
    
    # Public logging methods
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log an exception with traceback"""
        kwargs["extra"] = kwargs.get("extra", {})
        kwargs["extra"]["traceback"] = traceback.format_exc()
        self._log("ERROR", message, **kwargs)


class AICOLoggerFactory:
    """Factory for creating configured logger instances"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self._transport = None
        self._loggers = []  # Track created loggers
    
    def create_logger(self, subsystem: str, module: str) -> AICOLogger:
        """Create a logger instance for the specified subsystem and module"""
        logger = AICOLogger(
            subsystem=subsystem,
            module=module,
            config_manager=self.config,
            transport=self._get_transport()
        )
        self._loggers.append(logger)  # Track logger
        return logger
    
    def _get_transport(self):
        """Get or create the logging transport (ZeroMQ)"""
        if not self._transport and ZMQ_AVAILABLE:
            self._transport = ZMQLogTransport(self.config)
        return self._transport
    
    def mark_all_databases_ready(self):
        """Mark database ready for all created loggers"""
        for logger in self._loggers:
            logger.mark_database_ready()


class DirectDatabaseTransport:
    """Direct database transport for CLI commands (bypasses ZeroMQ)"""
    
    def __init__(self, config_manager, db_connection):
        self.config = config_manager
        self.db = db_connection
        self.repository = LogRepository(db_connection)
    
    def send_log(self, log_entry: LogEntry):
        """Send log entry directly to database"""
        try:
            self.repository.store_log(log_entry)
        except Exception as e:
            # Debug: Print error to understand why logging fails
            print(f"[CLI LOG ERROR] Failed to store log: {e}")
            import traceback
            print(f"[CLI LOG ERROR] Traceback: {traceback.format_exc()}")


class ZMQLogTransport:
    """ZeroMQ transport for sending logs to the message bus"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self._context = None
        self._socket = None
        self._setup_zmq()
    
    def _setup_zmq(self):
        """Setup ZeroMQ connection"""
        if not ZMQ_AVAILABLE:
            return
            
        try:
            self._context = zmq.Context()
            self._socket = self._context.socket(zmq.PUB)
            backend_port = self.config.get("message_bus.backend_port", 5555)
            self._socket.connect(f"tcp://localhost:{backend_port}")
        except Exception:
            # Silent failure - fallback will handle logging
            pass
    
    def send_log(self, log_entry: LogEntry):
        """Send log entry to message bus"""
        if not self._socket:
            raise Exception("ZMQ transport not available")
            
        topic = self.config.get("logging.transport.zmq_topic", "logs")
        full_topic = f"{topic}.{log_entry.subsystem}.{log_entry.module}"
        
        self._socket.send_multipart([
            full_topic.encode('utf-8'),
            log_entry.to_json().encode('utf-8')
        ])
    
    def close(self):
        """Clean up ZMQ resources"""
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()


class LogCollector:
    """Collects logs from ZeroMQ message bus and stores in database"""
    
    def __init__(self, config_manager, db_connection):
        self.config = config_manager
        self.db = db_connection
        self._context = None
        self._socket = None
        self._running = False
        
    def start(self):
        """Start collecting logs from message bus"""
        if not ZMQ_AVAILABLE:
            return
            
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        
        backend_port = self.config.get("message_bus.backend_port", 5555)
        self._socket.bind(f"tcp://*:{backend_port}")
        
        # Subscribe to all log topics
        topic = self.config.get("logging.transport.zmq_topic", "logs")
        self._socket.setsockopt(zmq.SUBSCRIBE, f"{topic}.".encode('utf-8'))
        
        self._running = True
        while self._running:
            try:
                topic_bytes, message_bytes = self._socket.recv_multipart(zmq.NOBLOCK)
                log_data = json.loads(message_bytes.decode('utf-8'))
                self._store_log(log_data)
            except zmq.Again:
                continue
            except Exception as e:
                # Log collector error - print to console as last resort
                print(f"[LOG COLLECTOR ERROR] {e}")
    
    def _store_log(self, log_data: Dict[str, Any]):
        """Store log entry in database"""
        try:
            self.db.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name,
                    file_path, line_number, topic, message, user_id,
                    session_id, trace_id, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                log_data.get("timestamp"),
                log_data.get("level"),
                log_data.get("subsystem"),
                log_data.get("module"),
                log_data.get("function_name"),
                log_data.get("file_path"),
                log_data.get("line_number"),
                log_data.get("topic"),
                log_data.get("message"),
                log_data.get("user_id"),
                log_data.get("session_id"),
                log_data.get("trace_id"),
                json.dumps(log_data.get("extra")) if log_data.get("extra") else None
            ])
        except Exception as e:
            print(f"[LOG STORAGE ERROR] {e}")
    
    def stop(self):
        """Stop collecting logs"""
        self._running = False
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()


class LogRepository:
    """Database operations for log storage and retrieval"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_logs(self, limit: int = 100, **filters) -> List[Dict[str, Any]]:
        """Retrieve logs with optional filtering"""
        where_clauses = []
        params = []
        
        if filters.get("level"):
            where_clauses.append("level = ?")
            params.append(filters["level"])
        
        if filters.get("subsystem"):
            where_clauses.append("subsystem = ?")
            params.append(filters["subsystem"])
            
        if filters.get("module"):
            where_clauses.append("module = ?")
            params.append(filters["module"])
            
        if filters.get("since"):
            where_clauses.append("timestamp >= ?")
            params.append(filters["since"])
            
        if filters.get("trace_id"):
            where_clauses.append("trace_id = ?")
            params.append(filters["trace_id"])
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        sql = f"""
            SELECT id, timestamp, level, subsystem, module, function_name,
                   file_path, line_number, topic, message, user_id,
                   session_id, trace_id, extra
            FROM logs 
            WHERE {where_sql}
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        params.append(limit)
        
        rows = self.db.execute(sql, params).fetchall()
        
        # Convert tuples to dictionaries with proper column names
        column_names = [
            "id", "timestamp", "level", "subsystem", "module", "function_name",
            "file_path", "line_number", "topic", "message", "user_id",
            "session_id", "trace_id", "extra"
        ]
        
        return [dict(zip(column_names, row)) for row in rows]
    
    def delete_logs(self, **criteria) -> int:
        """Delete logs matching criteria, returns count deleted"""
        where_clauses = []
        params = []
        
        if criteria.get("before"):
            where_clauses.append("timestamp < ?")
            params.append(criteria["before"])
            
        if criteria.get("level"):
            where_clauses.append("level = ?")
            params.append(criteria["level"])
            
        if criteria.get("subsystem"):
            where_clauses.append("subsystem = ?")
            params.append(criteria["subsystem"])
        
        if not where_clauses:
            raise ValueError("Must provide deletion criteria")
        
        where_sql = " AND ".join(where_clauses)
        
        # Get count first
        count_sql = f"SELECT COUNT(*) FROM logs WHERE {where_sql}"
        count = self.db.execute(count_sql, params).fetchone()[0]
        
        # Delete
        delete_sql = f"DELETE FROM logs WHERE {where_sql}"
        self.db.execute(delete_sql, params)
        
        return count
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {}
        
        # Total count
        stats["total_logs"] = self.db.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        
        # Count by level
        level_counts = self.db.execute("""
            SELECT level, COUNT(*) as count 
            FROM logs 
            GROUP BY level 
            ORDER BY count DESC
        """).fetchall()
        stats["by_level"] = {row[0]: row[1] for row in level_counts}
        
        # Count by subsystem
        subsystem_counts = self.db.execute("""
            SELECT subsystem, COUNT(*) as count 
            FROM logs 
            GROUP BY subsystem 
            ORDER BY count DESC
        """).fetchall()
        stats["by_subsystem"] = {row[0]: row[1] for row in subsystem_counts}
        
        # Recent activity (last 24h)
        stats["last_24h"] = self.db.execute("""
            SELECT COUNT(*) FROM logs 
            WHERE timestamp >= datetime('now', '-24 hours')
        """).fetchone()[0]
        
        return stats


class LogRetentionManager:
    """Manages log retention and cleanup based on configuration"""
    
    def __init__(self, config_manager, db_connection):
        self.config = config_manager
        self.db = db_connection
    
    def cleanup_old_logs(self) -> Dict[str, int]:
        """Clean up logs based on retention policy"""
        retention_days = self.config.get("logging.retention.days", 30)
        max_size_mb = self.config.get("logging.retention.max_size_mb", 500)
        
        results = {}
        
        # Delete by age
        cutoff_date = datetime.utcnow().replace(microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - retention_days)
        
        age_deleted = self.db.execute("""
            DELETE FROM logs 
            WHERE timestamp < ?
        """, [cutoff_date.isoformat() + "Z"]).rowcount
        
        results["deleted_by_age"] = age_deleted
        
        # Check size and delete oldest if over limit
        # (This is a simplified approach - could be more sophisticated)
        total_size = self._get_logs_size_mb()
        if total_size > max_size_mb:
            # Delete oldest 20% of logs
            total_count = self.db.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            delete_count = int(total_count * 0.2)
            
            size_deleted = self.db.execute(f"""
                DELETE FROM logs 
                WHERE id IN (
                    SELECT id FROM logs 
                    ORDER BY timestamp ASC 
                    LIMIT {delete_count}
                )
            """).rowcount
            
            results["deleted_by_size"] = size_deleted
        else:
            results["deleted_by_size"] = 0
        
        return results
    
    def _get_logs_size_mb(self) -> float:
        """Estimate logs table size in MB"""
        # Simplified size estimation
        row_count = self.db.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        # Rough estimate: ~500 bytes per log entry
        estimated_bytes = row_count * 500
        return estimated_bytes / (1024 * 1024)


# Global factory instance (created by each subsystem)
_logger_factory: Optional[AICOLoggerFactory] = None


def initialize_logging(config_manager) -> AICOLoggerFactory:
    """Initialize the global logging factory"""
    global _logger_factory
    _logger_factory = AICOLoggerFactory(config_manager)
    return _logger_factory


def initialize_cli_logging(config_manager, db_connection) -> AICOLoggerFactory:
    """Initialize logging for CLI commands with direct database access"""
    global _logger_factory
    _logger_factory = AICOLoggerFactory(config_manager)
    _logger_factory._transport = DirectDatabaseTransport(config_manager, db_connection)
    _logger_factory._cli_mode = True  # Mark as CLI mode
    return _logger_factory


def is_cli_context() -> bool:
    """Detect if running in CLI context"""
    import sys
    # Check if running as PyInstaller bundle (CLI executable)
    if getattr(sys, 'frozen', False):
        return True
    # Check if main module suggests CLI context
    if hasattr(sys, 'argv') and len(sys.argv) > 0:
        return 'cli' in sys.argv[0] or 'aico.exe' in sys.argv[0]
    return False


def get_logger(subsystem: str, module: str) -> AICOLogger:
    """Get a logger instance (requires prior initialization)"""
    if not _logger_factory:
        raise RuntimeError("Logging not initialized. Call initialize_logging() first.")
    return _logger_factory.create_logger(subsystem, module)
