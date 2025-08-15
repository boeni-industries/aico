"""
AICO Unified Logging System

Provides unified logging infrastructure for all AICO subsystems with:
- Configuration-driven behavior
- Database-only storage (no file logging)
- Bootstrap buffering for early logging
- Multi-layer fallback mechanisms
- ZeroMQ message bus integration
"""

import logging
import os
import sys
import time
import uuid
import zmq
import zmq.asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from google.protobuf.timestamp_pb2 import Timestamp

from ..proto.core import LogEntry, LogLevel
import inspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aico.core.config import ConfigurationManager

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False


def _create_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp"""
    timestamp = Timestamp()
    timestamp.FromDatetime(dt)
    return timestamp


def _python_level_to_protobuf(level: int) -> LogLevel:
    """Convert Python logging level to protobuf LogLevel"""
    if level >= 50:
        return LogLevel.CRITICAL
    elif level >= 40:
        return LogLevel.ERROR
    elif level >= 30:
        return LogLevel.WARNING
    elif level >= 20:
        return LogLevel.INFO
    elif level >= 10:
        return LogLevel.DEBUG
    else:
        return LogLevel.UNKNOWN


class AICOLogger:
    """Main logger class with bootstrap buffering and fallback mechanisms"""
    
    def __init__(self, subsystem: str, module: str, config_manager, transport=None):
        self.subsystem = subsystem
        self.module = module
        self.config = config_manager
        self.transport = transport
        self._bootstrap_buffer: List[LogEntry] = []
        # If we have a transport, assume database is ready (CLI mode or ZMQ initialized)
        self._db_ready = transport is not None
        self._max_buffer_size = self.config.get("logging.bootstrap.buffer_size", 100)
        
    def _create_log_entry(self, level: str, message: str, **kwargs) -> LogEntry:
        """Create a structured protobuf log entry with automatic context detection"""
        
        # Get caller information automatically
        frame = inspect.currentframe().f_back.f_back  # Skip this method and the calling log method
        function_name = frame.f_code.co_name if frame else None
        file_path = frame.f_code.co_filename if frame else None
        line_number = frame.f_lineno if frame else None
        
        # Clean up file path (just filename, not full path)
        if file_path:
            file_path = Path(file_path).name
            
        # Create protobuf LogEntry
        log_entry = LogEntry()
        log_entry.timestamp.CopyFrom(_create_timestamp(datetime.utcnow()))
        log_entry.level = _python_level_to_protobuf(getattr(logging, level.upper(), 20))
        log_entry.subsystem = self.subsystem
        log_entry.module = self.module
        log_entry.function = function_name or ""
        log_entry.message = message
        log_entry.topic = kwargs.get("topic", f"{self.subsystem}.{self.module}")
        
        # Optional fields
        if file_path:
            log_entry.file_path = file_path
        if line_number:
            log_entry.line_number = line_number
        if kwargs.get("user_id"):
            log_entry.user_id = kwargs["user_id"]
        if kwargs.get("session_id"):
            log_entry.session_id = kwargs["session_id"]
        if kwargs.get("trace_id"):
            log_entry.trace_id = kwargs["trace_id"]
        if kwargs.get("extra"):
            for key, value in kwargs["extra"].items():
                log_entry.extra[key] = str(value)
                
        return log_entry
    
    def _should_log(self, level: str) -> bool:
        """Determine if a log message should be recorded based on configured levels."""
        # Access the core domain configuration directly
        core_config = self.config.config_cache.get('core', {})
        
        # Hierarchical configuration: module > subsystem > default
        default_level = core_config.get('logging', {}).get('levels', {}).get('default', 'INFO')
        subsystem_level = core_config.get('logging', {}).get('levels', {}).get('subsystems', {}).get(self.subsystem, default_level)
        module_level = core_config.get('logging', {}).get('levels', {}).get('modules', {}).get(self.module, subsystem_level)
        
        # Convert levels to numeric values for comparison
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        result = levels.get(level, 1) >= levels.get(module_level, 1)
        
        return result
    
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
            # Convert protobuf timestamp to readable format
            from datetime import datetime
            timestamp = datetime.fromtimestamp(log_entry.timestamp.seconds + log_entry.timestamp.nanos / 1e9)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"[{timestamp_str}] {log_entry.level} "
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
        except Exception as e:
            # Last resort fallback failed - log to stderr but don't crash
            # This is acceptable because it's the final fallback in a chain
            import sys
            print(f"[LOGGING] Warning: Emergency file fallback failed: {e}", file=sys.stderr)
            print(f"[LOGGING] Lost log: {log_entry.level} {log_entry.subsystem}.{log_entry.module}: {log_entry.message}", file=sys.stderr)
    
    def _send_to_database(self, log_entry: LogEntry):
        """Send log entry to database via transport or fallback logging"""
        if self.transport:
            try:
                self.transport.send_log(log_entry)
            except Exception as e:
                # Print error and fallback, never log recursively
                print(f"[AICO LOGGING] Failed to send log to transport: {e}", file=sys.stderr)
                import traceback
                print(traceback.format_exc(), file=sys.stderr)
                self._try_fallback_logging(log_entry)
        else:
            self._try_fallback_logging(log_entry)
    
    def mark_database_ready(self):
        """Called after database initialization to flush bootstrap buffer"""
        self._db_ready = True
        # Flush bootstrap buffer to database
        for buffered_log in self._bootstrap_buffer:
            try:
                self._send_to_database(buffered_log)
            except Exception as e:
                print(f"[AICO LOGGING] Error flushing buffered log: {e}", file=sys.stderr)
                import traceback
                print(traceback.format_exc(), file=sys.stderr)
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
        self._db_ready = False  # Track global database ready state
    
    def create_logger(self, subsystem: str, module: str) -> AICOLogger:
        """Create a logger instance for the specified subsystem and module"""
        transport = self._get_transport()
        logger = AICOLogger(
            subsystem=subsystem,
            module=module,
            config_manager=self.config,
            transport=transport
        )
        # Apply global database ready state to new logger
        if self._db_ready:
            logger._db_ready = True
        
        self._loggers.append(logger)  # Track logger
        return logger
    
    def _get_transport(self):
        """Get or create transport for this logger factory"""
        if not self._transport and ZMQ_AVAILABLE:
            self._transport = ZMQLogTransport(self.config)
            self._transport.initialize()
        return self._transport
    
    def mark_all_databases_ready(self):
        """Mark database ready for all created loggers"""
        self._db_ready = True  
        for logger in self._loggers:
            logger.mark_database_ready()


class DirectDatabaseTransport:
    """Direct database transport for CLI commands (bypasses ZeroMQ)"""

    def __init__(self, config_manager, db_connection):
        self.config = config_manager
        self.db = db_connection
        self.repository = LogRepository(db_connection)

    def send_log(self, log_entry: LogEntry):
        try:
            self.repository.store_log(log_entry)
        except Exception as e:
            print(f"[CLI LOG ERROR] Failed to store log: {e}", file=sys.stderr)
            import traceback
            print(traceback.format_exc(), file=sys.stderr)


class ZMQLogTransport:
    """ZeroMQ-based log transport for sending logs to message bus"""
    
    def __init__(self, config):
        self.config = config
        self._socket = None
        self._context = None
        
    def initialize(self):
        """Initialize the ZMQ transport"""
        if not ZMQ_AVAILABLE:
            return
            
        try:
            import zmq
            
            self._context = zmq.Context()
            self._socket = self._context.socket(zmq.PUB)
            
            # Get message bus configuration - connect to broker frontend port
            host = self.config.get("message_bus.host", "localhost")
            publisher_port = self.config.get("message_bus.pub_port", 5555)
            address = f"tcp://{host}:{publisher_port}"
            
            self._socket.connect(address)
        except Exception as e:
            # Debug: Print ZMQ transport initialization failure
            print(f"[ZMQ TRANSPORT] Failed to initialize: {e}")
            import traceback
            print(f"[ZMQ TRANSPORT] Traceback: {traceback.format_exc()}")
            self._socket = None
            self._context = None
    
    def send_log(self, log_entry: LogEntry):
        """Send log entry to message bus as protobuf LogEntry"""
        if not self._socket:
            return
            
        try:
            topic = self.config.get("logging.transport.zmq_topic", "logs")
            full_topic = f"{topic}.{log_entry.subsystem}.{log_entry.module}"
            
            # Send protobuf LogEntry (binary serialization)
            self._socket.send_multipart([
                full_topic.encode('utf-8'),
                log_entry.SerializeToString()
            ], zmq.NOBLOCK)
            
        except Exception as e:
            # Log transport failure but don't crash - logging must be resilient
            # This is acceptable because logging failures shouldn't break the application
            import sys
            print(f"[ZMQ TRANSPORT] Warning: Failed to send log via ZMQ: {e}", file=sys.stderr)
            raise e  # Re-raise to trigger fallback logging
    
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

    def store_log(self, log_entry):
        """Persist a protobuf LogEntry to the logs table"""
        import json
        from aico.proto.core.logging_pb2 import LogLevel
        try:
            timestamp_str = log_entry.timestamp.ToDatetime().isoformat() + "Z"
            level_str = LogLevel.Name(log_entry.level)
            extra_json = None
            if log_entry.extra:
                try:
                    extra_json = json.dumps(dict(log_entry.extra))
                except Exception:
                    extra_json = json.dumps({k: str(v) for k, v in dict(log_entry.extra).items()})
            file_path = getattr(log_entry, 'file_path', None)
            line_number = getattr(log_entry, 'line_number', None)
            user_id = getattr(log_entry, 'user_id', None)
            session_id = getattr(log_entry, 'session_id', None)
            trace_id = getattr(log_entry, 'trace_id', None)
            self.db.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name, 
                    file_path, line_number, topic, message, user_id, 
                    session_id, trace_id, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp_str,
                level_str,
                log_entry.subsystem,
                log_entry.module,
                log_entry.function,
                file_path,
                line_number,
                log_entry.topic,
                log_entry.message,
                user_id,
                session_id,
                trace_id,
                extra_json
            ))
            self.db.commit()
        except Exception as e:
            print(f"[REPOSITORY DEBUG] Failed to persist log in LogRepository: {e}", file=sys.stderr)
            print(f"[REPOSITORY DEBUG] Log entry details: level={log_entry.level}, subsystem={log_entry.subsystem}, module={log_entry.module}, message={log_entry.message}", file=sys.stderr)
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
    
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
    _logger_factory.mark_all_databases_ready()  # Mark database as ready for CLI
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
