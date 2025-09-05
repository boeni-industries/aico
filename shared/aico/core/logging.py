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

# MessageBusClient will be imported lazily to avoid circular imports
MessageBusClient = None

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
        """Internal logging method that handles transport routing"""
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
            for key, value in extra.items():
                log_entry.extra[key] = str(value)
        
        # Route to appropriate transport or direct database fallback
        global _logger_factory
        
        # Prevent feedback loop: do not send logs from ZMQ/log_consumer to ZMQ or database
        if self._is_transport_disabled():
            # Only fallback log (console/file), never to ZMQ or database
            self._try_fallback_logging(log_entry)
            return
        
        if _logger_factory and _logger_factory._transport and self._is_zmq_transport_ready():
            _logger_factory._transport.send_log(log_entry)  # ZMQ logging
        else:
            # Direct database fallback for early startup logs
            self._direct_database_fallback(log_entry)  # Direct DB logging
    
    def _log_to_console(self, level: str, message: str, **kwargs):
        """Log to console as fallback - DISABLED (logs go to database only)"""
        # Console logging disabled - logs should only go to database via ZMQ transport
        # This method is kept for emergency fallback scenarios only
        pass
    
    def _direct_database_fallback(self, log_entry: LogEntry) -> None:
        """
        Direct database fallback when ZMQ transport is not available.
        
        This method attempts to write logs directly to the database during
        early startup when the ZMQ transport is not yet ready.
        """
        # Skip if level filtering is configured and this entry doesn't meet threshold
        global _logger_factory
        if _logger_factory and hasattr(_logger_factory, 'config'):
            if not self._should_log_level(log_entry.level, _logger_factory.config):
                return  # Skip logging if level is below threshold
                
        # Prevent recursion by checking if we're already in a fallback operation
        if hasattr(self, '_in_fallback') and self._in_fallback:
            self._fallback_log(log_entry)
            return
        
        try:
            self._in_fallback = True
            if _logger_factory and hasattr(_logger_factory, 'config'):
                # First try: get database connection from service container
                if hasattr(_logger_factory, 'container') and _logger_factory.container:
                    try:
                        db_connection = _logger_factory.container.get_service('database')
                        if db_connection:
                            direct_transport = DirectDatabaseTransport(_logger_factory.config, db_connection)
                            direct_transport.send_log(log_entry)
                            return
                    except:
                        pass
                
                # Fallback: create encrypted database connection using minimal key manager
                try:
                    db_connection = self._create_fallback_encrypted_connection(_logger_factory.config)
                    if db_connection:
                        # Use direct SQL insert instead of DirectDatabaseTransport to avoid protobuf issues
                        self._persist_log_entry_directly(db_connection, log_entry)
                        return
                except RuntimeError as e:
                    error_msg = str(e)
                    # Check if this is a security initialization error
                    if "Master key not found" in error_msg or "Run 'aico security init'" in error_msg:
                        # Security not initialized - this is expected during first run
                        # Fall back to console logging without error spam
                        pass
                    else:
                        pass  # Silent fallback for non-security errors
                    # Continue to final fallback
                except Exception as e:
                    pass  # Silent fallback for other errors
                    # Continue to final fallback
                
        except Exception as e:
            # Make fallback failures visible for debugging
            print(f"[LOGGING FALLBACK] Direct database fallback failed: {e}", file=sys.stderr)
        finally:
            self._in_fallback = False
        
        # Final fallback to console if database unavailable
        self._try_fallback_logging(log_entry)
    
    def _fallback_log(self, log_entry):
        """Fallback logging when ZMQ transport is not available"""
        # Skip if level filtering is configured and this entry doesn't meet threshold
        global _logger_factory
        if _logger_factory and hasattr(_logger_factory, 'config'):
            if not self._should_log_level(log_entry.level, _logger_factory.config):
                return  # Skip logging if level is below threshold
            
        try:
            self._in_fallback = True
            if _logger_factory and hasattr(_logger_factory, 'config'):
                # First try: get database connection from service container
                if hasattr(_logger_factory, 'container') and _logger_factory.container:
                    try:
                        db_connection = _logger_factory.container.get_service('database')
                        if db_connection:
                            direct_transport = DirectDatabaseTransport(_logger_factory.config, db_connection)
                            direct_transport.send_log(log_entry)
                            return
                    except Exception:
                        pass
                
                # Fallback: create encrypted database connection using minimal key manager
                try:
                    db_connection = self._create_fallback_encrypted_connection(_logger_factory.config)
                    if db_connection:
                        # Use direct SQL insert instead of DirectDatabaseTransport to avoid protobuf issues
                        self._persist_log_entry_directly(db_connection, log_entry)
                        return
                except RuntimeError as e:
                    error_msg = str(e)
                    # Check if this is a security initialization error
                    if "Master key not found" in error_msg or "Run 'aico security init'" in error_msg:
                        # Security not initialized - this is expected during first run
                        # Fall back to console logging without error spam
                        pass
                    else:
                        pass  # Silent fallback for non-security errors
                    # Continue to final fallback
                except Exception:
                    pass  # Silent fallback for other errors
                    # Continue to final fallback
                
        except Exception:
            # Silent fallback failure - don't spam logs
            pass
        finally:
            self._in_fallback = False
        
        # Final fallback to console if database unavailable
        self._try_fallback_logging(log_entry)
    _fallback_db_path = None
    
    def _create_fallback_encrypted_connection(self, config_manager):
        """Create encrypted database connection for fallback logging without any logging calls"""
        # Return cached connection if available
        if self._fallback_connection:
            try:
                # Test if connection is still valid
                self._fallback_connection.execute("SELECT 1").fetchone()
                return self._fallback_connection
            except Exception:
                # Connection is stale, clear cache and recreate
                self._fallback_connection = None
                self._fallback_encryption_key = None
                self._fallback_db_path = None
        
        try:
            import libsql
            import keyring
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.backends import default_backend
            from pathlib import Path
            
            # Get database path using proper AICO path resolution
            try:
                from aico.core.paths import AICOPaths
                directory_mode = config_manager.get("system.paths.directory_mode", "auto")
                db_path = AICOPaths.resolve_database_path("aico.db", directory_mode)
            except Exception as e:
                # Ultimate fallback if path resolution fails
                db_path = Path("aico.db")
            
            # FAIL LOUDLY: Database must exist - don't create it
            if not db_path.exists():
                raise FileNotFoundError(f"Database not found at {db_path}. Run 'aico db init' first.")
            
            # Get salt path
            salt_path = Path(f"{db_path}.salt")
            
            # FAIL LOUDLY: Salt file must exist if database exists
            if not salt_path.exists():
                raise FileNotFoundError(f"Database salt file not found at {salt_path}. Database may be corrupted.")
            
            # Reuse cached encryption key if available and path matches
            if self._fallback_encryption_key and self._fallback_db_path == db_path:
                encryption_key = self._fallback_encryption_key
            else:
                # Get master key from keyring without logging - use same service name as key manager
                service_name = config_manager.get("security.keyring_service_name", "AICO")
                try:
                    stored_key = keyring.get_password(service_name, "master_key")
                except Exception as e:
                    raise RuntimeError(f"Failed to retrieve master key from keyring: {e}")
                
                if not stored_key:
                    raise RuntimeError("Master key not found in keyring. Run 'aico security init' first.")
                
                master_key = bytes.fromhex(stored_key)
                
                # Read existing salt file
                with open(salt_path, 'rb') as f:
                    salt = f.read()
                
                # Derive database encryption key using PBKDF2 (minimal implementation)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,  # 256-bit key
                    salt=salt,
                    iterations=100000,  # Standard iterations
                    backend=default_backend()
                )
                
                context = master_key + b"aico-db-libsql"
                encryption_key = kdf.derive(context)
                
                # Cache the derived key and path
                self._fallback_encryption_key = encryption_key
                self._fallback_db_path = db_path
            
            # Create encrypted connection
            connection = libsql.connect(str(db_path))
            
            # Apply encryption key
            key_hex = encryption_key.hex()
            connection.execute(f"PRAGMA key = 'x\"{key_hex}\"'")
            
            # Set busy timeout for lock handling (other settings inherited from main connection)
            connection.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout for locks
            
            # Verify encryption is working
            try:
                connection.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
            except Exception as e:
                raise RuntimeError(f"Database encryption verification failed: {e}")
            
            # Cache the connection for reuse
            self._fallback_connection = connection
            result = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'").fetchone()
            if not result:
                connection.close()
                raise RuntimeError("Logs table not found in database. Run 'aico db init' to create schema.")
            
            # Verify schema matches expected columns
            columns = connection.execute("PRAGMA table_info(logs)").fetchall()
            column_names = {col[1] for col in columns}
            required_columns = {
                'timestamp', 'level', 'subsystem', 'module', 'function_name',
                'file_path', 'line_number', 'topic', 'message', 'user_uuid',
                'session_id', 'trace_id', 'extra'
            }
            
            if not required_columns.issubset(column_names):
                connection.close()
                missing = required_columns - column_names
                raise RuntimeError(f"Logs table schema mismatch. Missing columns: {missing}. Run 'aico db init' to fix schema.")
            
            # Cache the connection for reuse
            self._fallback_connection = connection
            return connection
            
        except Exception as e:
            # FAIL LOUDLY: Don't hide fallback connection errors
            raise RuntimeError(f"Fallback database connection failed: {e}")
    
    def _persist_log_entry_directly(self, db_connection, log_entry):
        """Directly persist log entry to database without protobuf complexity"""
        import time
        import random
        
        max_retries = 2  # Reduced retries to avoid long hangs
        base_delay = 0.05  # 50ms base delay
        
        for attempt in range(max_retries):
            try:
                from datetime import datetime, timezone
                
                # Convert protobuf timestamp to UTC ISO string
                if hasattr(log_entry.timestamp, 'seconds'):
                    # Use utcfromtimestamp to properly interpret the timestamp as UTC
                    timestamp = datetime.utcfromtimestamp(
                        log_entry.timestamp.seconds + log_entry.timestamp.nanos / 1e9
                    ).replace(tzinfo=timezone.utc)
                    timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
                else:
                    # Use utcnow() to ensure UTC timestamp
                    timestamp_str = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                
                # Convert level enum to string
                level_str = str(log_entry.level)
                if hasattr(log_entry, 'level') and hasattr(log_entry.level, 'name'):
                    level_str = log_entry.level.name
                elif str(log_entry.level) in ['10', '20', '30', '40', '50']:
                    level_map = {'10': 'DEBUG', '20': 'INFO', '30': 'WARNING', '40': 'ERROR', '50': 'CRITICAL'}
                    level_str = level_map.get(str(log_entry.level), 'INFO')
                
                # Prepare extra data as JSON
                extra_json = None
                if hasattr(log_entry, 'extra') and log_entry.extra:
                    try:
                        import json
                        extra_json = json.dumps(dict(log_entry.extra))
                    except Exception:
                        extra_json = str(log_entry.extra)
                
                # Insert directly into logs table with retry logic
                db_connection.execute("""
                    INSERT INTO logs (
                        timestamp, level, subsystem, module, function_name, 
                        file_path, line_number, topic, message, user_uuid, 
                        session_id, trace_id, extra
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_str,
                    level_str,
                    getattr(log_entry, 'subsystem', ''),
                    getattr(log_entry, 'module', ''),
                    getattr(log_entry, 'function', ''),
                    getattr(log_entry, 'file_path', None),
                    getattr(log_entry, 'line_number', None),
                    getattr(log_entry, 'topic', ''),
                    getattr(log_entry, 'message', ''),
                    getattr(log_entry, 'user_uuid', None),
                    getattr(log_entry, 'session_id', None),
                    getattr(log_entry, 'trace_id', None),
                    extra_json
                ))
                db_connection.commit()
                return  # Success - exit retry loop
                
            except Exception as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg or "busy" in error_msg:
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        # Linear backoff with minimal jitter for faster startup
                        delay = base_delay * (attempt + 1) + random.uniform(0, 0.01)
                        time.sleep(delay)
                        continue
                # Re-raise on final attempt or non-locking errors
                raise RuntimeError(f"Direct log persistence failed: {e}")
    
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
    
    def _try_fallback_logging(self, log_entry: LogEntry):
        """Multi-layer fallback for when database isn't ready"""
        
        # Skip if level filtering is configured and this entry doesn't meet threshold
        global _logger_factory
        if _logger_factory and hasattr(_logger_factory, 'config'):
            if not self._should_log_level(log_entry.level, _logger_factory.config):
                return  # Skip logging if level is below threshold
        
        # First try encrypted database fallback before falling back to console
        try:
            # Skip fallback logging if ZMQ transport is ready
            if _logger_factory and _logger_factory._transport and self._is_zmq_transport_ready():
                # ZMQ transport is ready, don't fallback to console
                return
                
            # Try encrypted database fallback first
            if not hasattr(self, '_in_fallback') or not self._in_fallback:
                try:
                    self._in_fallback = True
                    if _logger_factory and hasattr(_logger_factory, 'config'):
                        db_connection = self._create_fallback_encrypted_connection(_logger_factory.config)
                        if db_connection:
                            self._persist_log_entry_directly(db_connection, log_entry)
                            self._in_fallback = False
                            return
                except Exception:
                    # Silent failure, continue to console fallback
                    pass
                finally:
                    self._in_fallback = False
        except Exception:
            # Silent failure, continue to console fallback
            pass
            
        # Layer 1: Console output (only if encrypted database fallback failed and not disabled)
        fallback_console_enabled = self.config.get("logging.bootstrap.fallback_console", False)  # Default to False
        if fallback_console_enabled:
            # Convert protobuf timestamp to readable format
            from datetime import datetime
            # Use utcfromtimestamp to properly interpret the timestamp as UTC
            timestamp = datetime.utcfromtimestamp(log_entry.timestamp.seconds + log_entry.timestamp.nanos / 1e9)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Format main log line
            main_line = f"{timestamp_str} {log_entry.level} {log_entry.subsystem}.{log_entry.module} {log_entry.message}"
            print(main_line)
            
            # Format extra data with proper indentation and no truncation
            if hasattr(log_entry, 'extra') and log_entry.extra:
                import json
                try:
                    # Parse extra data if it's a JSON string
                    if isinstance(log_entry.extra, str):
                        extra_data = json.loads(log_entry.extra)
                    else:
                        extra_data = log_entry.extra
                    
                    # Format each key-value pair with proper indentation
                    for key, value in extra_data.items():
                        if isinstance(value, str) and len(value) > 80:
                            # For long strings, use multi-line format
                            print(f"    ├─ {key}: {value}")
                        else:
                            print(f"    ├─ {key}: {value}")
                except (json.JSONDecodeError, AttributeError, TypeError):
                    # Fallback for non-JSON extra data
                    print(f"    ├─ extra: {log_entry.extra}")
        
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
            # Last resort fallback failed - silent failure to avoid log spam
            # This is acceptable because it's the final fallback in a chain
            pass
    
    def _send_to_database(self, log_entry: LogEntry):
        """Send log entry to database via transport or fallback logging"""

        if self.transport and not self._is_transport_disabled():
            try:
 
                self.transport.send_log(log_entry)
                
            except Exception as e:
                # Silent fallback to avoid recursive logging
                self._try_fallback_logging(log_entry)
        else:
            self._try_fallback_logging(log_entry)
    
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
    """ZeroMQ transport for log messages using encrypted MessageBusClient"""
    
    def __init__(self, config: 'ConfigurationManager', zmq_context):
        self.config = config
        self._message_bus_client = None
        self._initialized = False
        self._broker_available = False

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
        """Send a log entry via ZMQ transport"""
        if not self._initialized or not ZMQ_AVAILABLE:
            return
        
        # Construct topic with hierarchical structure
        topic = AICOTopics.ZMQ_LOGS_PREFIX  # "logs/"
        if log_entry.subsystem:
            topic += log_entry.subsystem
            if log_entry.module:
                topic += "/" + log_entry.module
        
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


# Removed _transfer_early_buffer_to_transport - using direct database fallback instead

