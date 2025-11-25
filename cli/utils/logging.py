"""
CLI-Specific Isolated Logging System

Provides direct database logging for CLI commands without dependency on 
the shared ZMQ-based logging infrastructure. This ensures CLI commands
work independently and don't interfere with backend logging.
"""

import json
import sqlite3
import atexit
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

class LogLevel(Enum):
    """Log levels matching AICO protobuf LogLevel enum"""
    UNKNOWN = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class CLILogger:
    """Isolated CLI logger that writes directly to database"""
    
    def __init__(self, subsystem: str, module: str, db_connection, config_manager):
        self.subsystem = subsystem
        self.module = module
        self.db = db_connection  # Store connection - will be cleaned up by manager
        self.config = config_manager
        self._validate_logs_table()
    
    def _validate_logs_table(self):
        """Validate that logs table exists - FAIL LOUDLY if missing"""
        try:
            # Check if logs table exists
            result = self.db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='logs'
            """).fetchone()
            
            if not result:
                raise RuntimeError(
                    "CRITICAL: logs table does not exist in database. "
                    "Run 'aico db init' to initialize the database schema first."
                )
            
            # Validate table structure has required columns
            columns = self.db.execute("PRAGMA table_info(logs)").fetchall()
            required_columns = {
                'id', 'timestamp', 'level', 'subsystem', 'module', 
                'message', 'function_name', 'file_path', 'line_number',
                'topic', 'user_uuid', 'session_id', 'trace_id', 'extra'
            }
            existing_columns = {col[1] for col in columns}
            
            missing_columns = required_columns - existing_columns
            if missing_columns:
                raise RuntimeError(
                    f"CRITICAL: logs table is missing required columns: {missing_columns}. "
                    "Run 'aico db init' to update the database schema."
                )
                
        except sqlite3.Error as e:
            raise RuntimeError(f"CRITICAL: Failed to validate logs table: {e}") from e
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method with configuration-based filtering"""
        # Check if this log level should be processed based on configuration
        if not self._should_log(level):
            return
            
        try:
            # Get caller information
            import inspect
            frame = inspect.currentframe().f_back.f_back
            function_name = frame.f_code.co_name if frame else None
            file_path = Path(frame.f_code.co_filename).name if frame else None
            line_number = frame.f_lineno if frame else None
            
            # Create timestamp
            timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            
            # Prepare extra data
            extra_json = None
            if kwargs.get('extra'):
                try:
                    extra_json = json.dumps(kwargs['extra'])
                except Exception:
                    extra_json = str(kwargs['extra'])
            
            # Insert log entry - FAIL LOUDLY if this fails
            # Format matches AICO LogRepository.store_log() exactly
            self.db.execute("""
                INSERT INTO logs (
                    timestamp, level, subsystem, module, function_name,
                    file_path, line_number, topic, message, user_uuid,
                    session_id, trace_id, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                level.name,
                "cli",  # Always use "cli" as subsystem for CLI logging
                self.module,
                function_name,
                file_path,
                line_number,
                kwargs.get('topic', f"cli.{self.module}"),  # Topic format: cli.module
                message,
                kwargs.get('user_uuid'),
                kwargs.get('session_id'),
                kwargs.get('trace_id'),
                extra_json
            ))
            self.db.commit()
            
        except Exception as e:
            # FAIL LOUDLY - don't silently continue
            import sys
            print(f"\n=== CLI LOGGING SYSTEM FAILURE ===", file=sys.stderr)
            print(f"CRITICAL: Failed to write log to database: {e}", file=sys.stderr)
            print(f"Message that failed to log: {level.name} {self.subsystem}.{self.module}: {message}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            print(f"=== END CLI LOGGING FAILURE ===", file=sys.stderr)
            raise RuntimeError(f"CLI logging system failed: {e}") from e
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if this log level should be processed based on configuration"""
        try:
            # Get log level configuration
            default_level = self.config.get('logging.levels.default', 'INFO')
            subsystem_level = self.config.get(f'logging.levels.subsystems.{self.subsystem}', default_level)
            module_level = self.config.get(f'logging.levels.modules.{self.module}', subsystem_level)
            
            # Convert string level to enum value
            configured_level = getattr(LogLevel, module_level.upper(), LogLevel.INFO)
            
            return level.value >= configured_level.value
        except Exception:
            # If configuration fails, default to INFO level
            return level.value >= LogLevel.INFO.value
    
    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)

class CLILoggingManager:
    """Manager for CLI logging system"""
    
    def __init__(self):
        self._loggers: Dict[str, CLILogger] = {}
        self._db_connection = None
        self._config_manager = None
    
    def initialize(self, db_connection, config_manager):
        """Initialize CLI logging with database connection and configuration"""
        if not db_connection:
            raise RuntimeError("CRITICAL: Database connection is required for CLI logging")
        if not config_manager:
            raise RuntimeError("CRITICAL: Configuration manager is required for CLI logging")
        
        # Clean up previous connection if it exists
        self.cleanup()
            
        self._db_connection = db_connection
        self._config_manager = config_manager
        # Clear any existing loggers to force re-creation with new connection
        self._loggers.clear()
    
    def cleanup(self):
        """Clean up resources - clear references but DON'T close connection (command owns it)"""
        # Just clear references - the connection is owned by the command, not us
        self._db_connection = None
        self._config_manager = None
        self._loggers.clear()
    
    def get_logger(self, subsystem: str, module: str) -> CLILogger:
        """Get or create a CLI logger"""
        if not self._db_connection:
            raise RuntimeError(
                "CRITICAL: CLI logging not initialized. Call initialize() with database connection first."
            )
        if not self._config_manager:
            raise RuntimeError(
                "CRITICAL: CLI logging not initialized. Call initialize() with configuration manager first."
            )
        
        key = f"{subsystem}.{module}"
        if key not in self._loggers:
            self._loggers[key] = CLILogger(subsystem, module, self._db_connection, self._config_manager)
        
        return self._loggers[key]
    
    def is_initialized(self) -> bool:
        """Check if CLI logging is initialized"""
        return self._db_connection is not None and self._config_manager is not None

# Global CLI logging manager instance
_cli_logging_manager = CLILoggingManager()

# Register cleanup handler to close database connections on exit
atexit.register(_cli_logging_manager.cleanup)

def initialize_cli_logging(db_connection, config_manager):
    """Initialize CLI logging system with database connection and configuration"""
    _cli_logging_manager.initialize(db_connection, config_manager)

def get_cli_logger(subsystem: str, module: str) -> CLILogger:
    """Get a CLI logger instance"""
    return _cli_logging_manager.get_logger(subsystem, module)

def is_cli_logging_initialized() -> bool:
    """Check if CLI logging is initialized"""
    return _cli_logging_manager.is_initialized()
