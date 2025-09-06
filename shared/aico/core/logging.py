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
import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from google.protobuf.timestamp_pb2 import Timestamp
from .topics import AICOTopics
from .logging_context import get_logging_context, create_infrastructure_logger

# MessageBusClient will be imported lazily to avoid circular imports
MessageBusClient = None


class LogBuffer:
    """Simple in-memory buffer for logs during startup before ZMQ transport is ready"""
    
    def __init__(self, max_size: int = 1000):
        self._buffer = []
        self._max_size = max_size
    
    def add(self, log_entry: 'LogEntry'):
        """Add log entry to buffer, removing oldest if at capacity"""
        if len(self._buffer) >= self._max_size:
            self._buffer.pop(0)  # Remove oldest
        self._buffer.append(log_entry)
    
    def flush_to_transport(self, transport):
        """Flush all buffered logs to transport and clear buffer"""
        while self._buffer:
            log_entry = self._buffer.pop(0)
            try:
                transport.send_log(log_entry)
            except Exception:
                # If transport fails, put log back and stop flushing
                self._buffer.insert(0, log_entry)
                break
    
    def size(self) -> int:
        """Get current buffer size"""
        return len(self._buffer)
    
    def clear(self):
        """Clear all buffered logs"""
        self._buffer.clear()

# Optional protobuf imports to avoid chicken/egg problem with CLI
try:
    from aico.proto.aico_core_logging_pb2 import LogEntry, LogLevel
except ImportError:
    # Protobuf files not generated yet - use fallbacks
    LogEntry = None
    LogLevel = None
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
        # If we have a transport, assume database is ready (CLI mode or ZMQ initialized)
        self._db_ready = transport is not None
        
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
        if kwargs.get("user_uuid"):
            log_entry.user_uuid = kwargs["user_uuid"]
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
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Internal logging method with simple execution chain"""
        # Create LogEntry protobuf message
        log_entry = LogEntry()
        log_entry.timestamp.GetCurrentTime()
        log_entry.level = level
        log_entry.subsystem = self.subsystem
        log_entry.module = self.module
        log_entry.message = message
        
        # Add caller information
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            log_entry.function = caller_frame.f_code.co_name
            log_entry.file_path = caller_frame.f_code.co_filename
            log_entry.line_number = caller_frame.f_lineno
        
        # Add extra data if provided
        if extra:
            # Convert extra data to string values for protobuf map<string, string>
            for key, value in extra.items():
                log_entry.extra[key] = str(value)
        
        global _logger_factory
        
        # Prevent feedback loop: do not send logs from ZMQ/log_consumer to ZMQ or database
        if self._is_transport_disabled():
            self._console_fallback(log_entry)
            return
        
        # Simple execution chain: ZMQ transport → Buffer → Console fallback
        if _logger_factory and _logger_factory._transport and self._is_zmq_transport_ready():
            # ZMQ transport is ready - send directly
            _logger_factory._transport.send_log(log_entry)
        elif _logger_factory:
            # ZMQ not ready - add to buffer
            _logger_factory._log_buffer.add(log_entry)
        else:
            # No logger factory - console fallback
            self._console_fallback(log_entry)
    
    def _console_fallback(self, log_entry: LogEntry):
        """Simple console fallback for when all else fails"""
        try:
            from aico.proto.aico_core_logging_pb2 import LogLevel
            level_name = LogLevel.Name(log_entry.level) if LogLevel else 'UNKNOWN'
        except (ImportError, AttributeError):
            level_name = 'UNKNOWN'
            
        timestamp = log_entry.timestamp.ToDatetime().strftime('%Y-%m-%d %H:%M:%S') if hasattr(log_entry.timestamp, 'ToDatetime') else 'UNKNOWN'
        print(f"[FALLBACK] {timestamp} {level_name} {log_entry.subsystem}.{log_entry.module} {log_entry.message}", file=sys.stderr, flush=True)
    
    # Removed complex direct database fallback - using simple buffer approach
    
    # Removed complex fallback methods - using simple buffer approach
    
    def _should_log_level(self, log_level, config_manager) -> bool:
        """Check if log entry should be logged based on configured levels"""
        try:
            # Convert protobuf level to string
            if hasattr(log_level, 'name'):
                level_name = log_level.name
            elif str(log_level) in ['10', '20', '30', '40', '50']:
                level_map = {'10': 'DEBUG', '20': 'INFO', '30': 'WARNING', '40': 'ERROR', '50': 'CRITICAL'}
                level_name = level_map.get(str(log_level), 'INFO')
            else:
                level_name = str(log_level).upper()
            
            # Get configured level with proper hierarchical lookup
            # Check subsystem-specific level first, then default
            subsystem = getattr(self, 'subsystem', '')
            module = getattr(self, 'module', '')
            
            # Try subsystem.module first, then subsystem, then default
            subsystem_key = f"logging.levels.subsystems.{subsystem}"
            module_key = f"logging.levels.modules.{module}"
            
            configured_level = (
                config_manager.get(module_key) or
                config_manager.get(subsystem_key) or  
                config_manager.get("logging.levels.default", "INFO")
            )
            
            # Level hierarchy: DEBUG < INFO < WARNING < ERROR < CRITICAL
            level_hierarchy = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
            
            current_level_value = level_hierarchy.get(level_name, 20)  # Default to INFO
            configured_level_value = level_hierarchy.get(configured_level, 20)  # Default to INFO
            
            # Only log if current level is >= configured level
            return current_level_value >= configured_level_value
            
        except Exception:
            # If level checking fails, default to allowing the log
            return True
    
    def _is_zmq_transport_ready(self) -> bool:
        """Check if ZMQ transport is ready to send logs"""
        global _logger_factory
        if not _logger_factory or not _logger_factory._transport:
            return False
        
        transport = _logger_factory._transport
        broker_available = getattr(transport, '_broker_available', False)
        client_connected = getattr(transport, '_message_bus_client', None) and getattr(transport._message_bus_client, 'connected', False)
        
        return broker_available and client_connected
    
    # Removed complex fallback methods - using simple buffer approach
    
    def _is_transport_disabled(self) -> bool:
        """Determine if ZMQ transport should be disabled for this logger to prevent feedback loops.

        Rules:
        - Config-driven via `logging.disable_zmq_for` list of "subsystem.module" strings
        - Built-in safeguard: disable for service.log_consumer by default
        """
        try:
            disabled_list = self.config.get("logging.disable_zmq_for", []) or []
        except Exception:
            disabled_list = []

        key = f"{self.subsystem}.{self.module}"
        if key in disabled_list:
            return True

        # Built-in safeguard to avoid infinite loop if not explicitly configured
        if self.subsystem == "service" and self.module.startswith("log_consumer"):
            return True

        return False
    
    def mark_database_ready(self):
        """Called after database initialization (no-op, buffer removed)"""
        self._db_ready = True
    
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
        self._loggers: Dict[str, AICOLogger] = {}  # Track created loggers
        self._db_ready = False  # Track global database ready state
        self._zmq_context = None
        self._log_buffer = LogBuffer()  # Buffer for startup logs

    def get_zmq_context(self):
        """Get or create the shared ZMQ context (regular, not asyncio)."""
        if self._zmq_context is None and ZMQ_AVAILABLE:
            import zmq
            self._zmq_context = zmq.Context()
        return self._zmq_context

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
            # Add debug output to confirm db_ready state is applied to new loggers
            #print(f"[LOGGER FACTORY] Applied db_ready=True to new logger {subsystem}.{module}")
        
        logger_key = f"{subsystem}:{module}"
        self._loggers[logger_key] = logger  # Track logger
        return logger

    def _get_transport(self):
        """Get or create transport for this logger factory"""
        if not self._transport and ZMQ_AVAILABLE:
            context = self.get_zmq_context()
            import sys
            print(f"[DEBUG] Logger factory getting ZMQ context: {context is not None}", file=sys.stderr, flush=True)
            if context:
                self._transport = ZMQLogTransport(self.config, context)
                print(f"[DEBUG] Created ZMQ transport, initializing...", file=sys.stderr, flush=True)
                self._transport.initialize()
                print(f"[DEBUG] ZMQ transport initialization complete", file=sys.stderr, flush=True)
        return self._transport
    
    def reinitialize_loggers(self):
        """Re-initialize all existing loggers with the current transports."""
        # Debug print for logger re-initialization
        # print("[LOGGING] Re-initializing all existing loggers with ZMQ transport...")
        transport = self._get_transport()
        if not transport:
            # print("[LOGGING] Re-initialization skipped: ZMQ transport not available.")
            return

        for logger_name, logger in self._loggers.items():
            if not logger.transport:
                # print(f"[LOGGING] Updating transport for logger: {logger_name}")
                logger.transport = transport

    def mark_all_databases_ready(self):
        """Mark database ready for all created loggers"""
        self._db_ready = True  
        # Iterate over logger instances, not keys, to propagate readiness
        for logger in self._loggers.values():
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
            # LOUD FAILURE: Print to stderr AND raise exception
            import sys
            error_msg = f"CRITICAL: DirectDatabaseTransport failed to store log: {e}"
            print(error_msg, file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Don't raise - would break CLI, but make it very visible
            print(f"[LOGGING FAILURE] Message lost: {log_entry.message}", file=sys.stderr)


class ZMQLogTransport:
    """ZeroMQ-based log transport for distributed logging"""
    
    def __init__(self, config: 'ConfigurationManager', zmq_context):
        self.config = config
        self._zmq_context = zmq_context
        self._message_bus_client = None
        self._initialized = False
        self._broker_available = False
        self._logger = create_infrastructure_logger("zmq_log_transport")

    def initialize(self):
        """Initialize the ZMQ transport"""
        import sys
        
        # Lazy import to avoid circular dependencies
        global MessageBusClient
        if MessageBusClient is None:
            try:
                from aico.core.bus import MessageBusClient as _MessageBusClient
                MessageBusClient = _MessageBusClient
                print(f"[ZMQ TRANSPORT] Lazy import of MessageBusClient successful", file=sys.stderr, flush=True)
            except ImportError as e:
                print(f"[ZMQ TRANSPORT] Failed to import MessageBusClient: {e}", file=sys.stderr, flush=True)
                return
        
        print(f"[ZMQ TRANSPORT] initialize() called, ZMQ_AVAILABLE={ZMQ_AVAILABLE}, MessageBusClient={MessageBusClient is not None}", file=sys.stderr, flush=True)
        
        if not ZMQ_AVAILABLE or not MessageBusClient:
            print(f"[ZMQ TRANSPORT] Skipping initialization - missing dependencies", file=sys.stderr, flush=True)
            return
        
        print(f"[ZMQ TRANSPORT] Creating MessageBusClient...", file=sys.stderr, flush=True)
        self._message_bus_client = MessageBusClient("zmq_log_transport")
        self._initialized = True
        print(f"[ZMQ TRANSPORT] MessageBusClient created successfully", file=sys.stderr, flush=True)
            
    def send_log(self, log_entry: LogEntry):
        """Send log entry via ZMQ message bus"""
        if not self._initialized:
            return  # Skip if not initialized
        
        # Check if we should skip ZMQ transport due to logging context
        context = get_logging_context()
        if context.is_infrastructure_context and 'zmq' in context.excluded_transports:
            return  # Skip ZMQ transport to prevent circular logging
        
        # Convert LogEntry to protobuf message
        from ..proto.aico_core_envelope_pb2 import AicoMessage
        from ..proto.aico_core_logging_pb2 import LogEntry
        from google.protobuf.any_pb2 import Any as ProtoAny
        
        log_msg = LogEntry()
        log_msg.timestamp.CopyFrom(log_entry.timestamp)
        log_msg.level = log_entry.level
        log_msg.subsystem = log_entry.subsystem
        log_msg.module = log_entry.module
        log_msg.message = log_entry.message
        log_msg.metadata.update(log_entry.metadata)
        
        # Pack LogEntry into Any payload
        any_payload = ProtoAny()
        any_payload.Pack(log_msg)
        
        aico_msg = AicoMessage()
        aico_msg.any_payload.CopyFrom(any_payload)
        
        # Determine topic based on subsystem and module
        topic = AICOTopics.get_log_topic(log_entry.subsystem, log_entry.module)
        
        # Schedule async send
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_send_log(topic, log_entry))
        except RuntimeError:
            # No event loop running, skip ZMQ logging
            pass
    
    async def _async_send_log(self, topic: str, log_entry: LogEntry):
        """Async method to send log entry to ZMQ broker"""
        if not self._message_bus_client:
            return
        
        try:
            # Ensure client is connected
            if not self._message_bus_client.connected:
                await self._message_bus_client.connect()
            
            if self._message_bus_client.connected:
                await self._message_bus_client.publish(topic, log_entry)
        except Exception:
            # Silently fail - logs will use direct database fallback
            pass
    
    def mark_broker_ready(self):
        """Mark the ZMQ broker as ready and attempt to connect client"""
        import sys
        print(f"[ZMQ TRANSPORT] mark_broker_ready() called", file=sys.stderr, flush=True)
        self._broker_available = True
        
        # Debug the client state
        if self._message_bus_client:
            print(f"[ZMQ TRANSPORT] Client exists, connected={self._message_bus_client.connected}", file=sys.stderr, flush=True)
        else:
            print(f"[ZMQ TRANSPORT] No message bus client found", file=sys.stderr, flush=True)
            return
        
        # Immediately connect the client when broker becomes available
        if not self._message_bus_client.connected:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._connect_client())
                print(f"[ZMQ TRANSPORT] Scheduled client connection task", file=sys.stderr, flush=True)
            except RuntimeError:
                print(f"[ZMQ TRANSPORT] No event loop - will connect on first log", file=sys.stderr, flush=True)
                pass  # Connection will be established lazily when first log is sent
        else:
            print(f"[ZMQ TRANSPORT] Client already connected", file=sys.stderr, flush=True)
        
        # Flush buffered logs from LogBuffer when broker becomes ready
        self._flush_log_buffer()
    
    def _flush_log_buffer(self):
        """Flush any buffered logs from the LogBuffer to ZMQ transport"""
        global _logger_factory
        if not _logger_factory or not _logger_factory._log_buffer:
            return
        
        import sys
        buffer_size = len(_logger_factory._log_buffer._buffer)
        if buffer_size > 0:
            print(f"[ZMQ TRANSPORT] Flushing {buffer_size} buffered logs to ZMQ transport", file=sys.stderr, flush=True)
            _logger_factory._log_buffer.flush_to_transport(self)
            print(f"[ZMQ TRANSPORT] Successfully flushed buffered logs", file=sys.stderr, flush=True)
        else:
            print(f"[ZMQ TRANSPORT] No buffered logs to flush", file=sys.stderr, flush=True)
    
    async def _connect_client(self):
        """Helper method to connect the message bus client"""
        try:
            await self._message_bus_client.connect()
            import sys
            print(f"[ZMQ TRANSPORT] Client connected successfully", file=sys.stderr, flush=True)
        except Exception as e:
            import sys
            print(f"[ZMQ TRANSPORT] Client connection failed: {e}", file=sys.stderr, flush=True)
            pass  # Silently fail
    
    def close(self):
        """Clean up encrypted ZMQ transport resources"""
        if self._message_bus_client:
            # Properly disconnect the client
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._message_bus_client.disconnect())
            except RuntimeError:
                pass  # No running loop
            self._message_bus_client = None
        self._initialized = False


class LogRepository:
    """Database operations for log storage and retrieval"""
    
    def __init__(self, db_connection):
        self.db = db_connection

    def store_log(self, log_entry):
        """Persist a protobuf LogEntry to the logs table"""
        import json
        try:
            from aico.proto.aico_core_logging_pb2 import LogLevel
        except ImportError:
            # Fallback if protobuf not available
            LogLevel = None
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
            user_uuid = getattr(log_entry, 'user_uuid', None)
            session_id = getattr(log_entry, 'session_id', None)
            trace_id = getattr(log_entry, 'trace_id', None)
            self.db.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name, 
                    file_path, line_number, topic, message, user_uuid, 
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
                user_uuid,
                session_id,
                trace_id,
                extra_json
            ))
            self.db.commit()
        except Exception as e:
            # LOUD FAILURE: Print to stderr with full details
            import sys
            error_msg = f"CRITICAL: LogRepository failed to persist log: {e}"
            print(error_msg, file=sys.stderr)
            print(f"[LOST LOG] level={LogLevel.Name(log_entry.level) if LogLevel else 'UNKNOWN'}, subsystem={log_entry.subsystem}, module={log_entry.module}, message={log_entry.message}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Don't raise - would break application, but make failure very visible
    
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
                   file_path, line_number, topic, message, user_uuid,
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
            "file_path", "line_number", "topic", "message", "user_uuid",
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


# Global logger factory instances
_logger_factory: Optional[AICOLoggerFactory] = None
_cli_logger_factory: Optional[AICOLoggerFactory] = None

# Removed early startup buffer - using direct database fallback instead


def initialize_logging(config_manager) -> AICOLoggerFactory:
    """Initialize the global logging factory (idempotent)"""
    global _logger_factory
    if _logger_factory is None:
        _logger_factory = AICOLoggerFactory(config_manager)
        # Debug print for logger factory initialization
        import sys
        print(f"[LOGGING] Initialized new AICOLoggerFactory", file=sys.stderr, flush=True)
    else:
        # Debug print for existing logger factory
        # print(f"[LOGGING] Using existing AICOLoggerFactory")
        pass
    return _logger_factory


def get_logger_factory() -> Optional[AICOLoggerFactory]:
    """Get the global logger factory instance."""
    return _logger_factory


def initialize_cli_logging(config_manager, db_connection) -> AICOLoggerFactory:
    """Initialize logging for CLI commands with direct database access"""
    global _cli_logger_factory
    
    print(f"[DEBUG] CLI logging: Creating CLI factory with DirectDatabaseTransport")
    _cli_logger_factory = AICOLoggerFactory(config_manager)
    _cli_logger_factory._transport = DirectDatabaseTransport(config_manager, db_connection)
    _cli_logger_factory._cli_mode = True
    _cli_logger_factory.mark_all_databases_ready()
    
    # Verify the transport is working by creating and testing a logger
    try:
        test_logger = _cli_logger_factory.create_logger("cli", "init_test")
        test_logger.info("CLI logging factory initialized and verified")
        print(f"[DEBUG] CLI logging: Factory verification successful")
        print(f"[DEBUG] CLI logging: CLI factory set globally: {_cli_logger_factory is not None}")
    except Exception as e:
        print(f"[ERROR] CLI logging: Factory verification failed: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"CLI logging initialization failed: {e}")
    
    return _cli_logger_factory


def is_cli_context() -> bool:
    """Detect if running in CLI context - only warn for direct CLI logger usage"""
    import sys
    import inspect
    
    # Check if running as PyInstaller bundle (CLI executable)
    if getattr(sys, 'frozen', False):
        # Only warn if called directly from CLI code, not from shared modules
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_file = frame.f_back.f_back.f_code.co_filename
            return 'cli' in caller_file and 'shared' not in caller_file
        return True
    
    # Check if main module suggests CLI context
    if hasattr(sys, 'argv') and len(sys.argv) > 0:
        if 'cli' in sys.argv[0] or 'aico.exe' in sys.argv[0]:
            # Only warn if called directly from CLI code, not from shared modules
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller_file = frame.f_back.f_back.f_code.co_filename
                return 'cli' in caller_file and 'shared' not in caller_file
            return True
    return False


def get_logger(subsystem: str, module: str) -> AICOLogger:
    """Get a logger instance (requires prior initialization)"""
    global _cli_logger_factory, _logger_factory
    
    # Use CLI factory if available (CLI context takes priority)
    if _cli_logger_factory:
        return _cli_logger_factory.create_logger(subsystem, module)
    
    if not _logger_factory:
        raise RuntimeError("Logging not initialized. Call initialize_logging() or initialize_cli_logging() first.")
    
    # Warn if using backend factory in potential CLI context
    if is_cli_context():
        print(f"[WARNING] Using backend logger factory in CLI context - logs may not persist to database")
    
    return _logger_factory.create_logger(subsystem, module)


def _get_zmq_transport() -> Optional[ZMQLogTransport]:
    """Get the global ZMQ transport instance for broker ready notifications"""
    if _logger_factory and hasattr(_logger_factory, '_transport'):
        return _logger_factory._transport
    return None




