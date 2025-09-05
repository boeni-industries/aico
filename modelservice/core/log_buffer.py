"""
Simple log buffering for modelservice startup.

Captures logs before ZMQ service is available and flushes them once connected.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from aico.core.logging import get_logger


class StartupLogBuffer:
    """Simple buffer for logs generated before ZMQ service is ready."""
    
    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self.is_flushed = False
        self.max_buffer_size = 1000  # Prevent memory issues
        
    def add_log(self, level: str, message: str, subsystem: str = "modelservice", module: str = "startup", **kwargs):
        """Add a log entry to the buffer."""
        if self.is_flushed:
            # Buffer already flushed, log normally
            logger = get_logger(subsystem, module)
            getattr(logger, level.lower())(message, **kwargs)
            return
            
        if len(self.buffer) >= self.max_buffer_size:
            # Buffer full, drop oldest entries
            self.buffer = self.buffer[100:]  # Keep last 900 entries
            
        log_entry = {
            "timestamp": datetime.utcnow(),
            "level": level,
            "message": message,
            "subsystem": subsystem,
            "module": module,
            "kwargs": kwargs
        }
        self.buffer.append(log_entry)
        
    def flush_to_logger(self):
        """Flush all buffered logs to the normal logging system."""
        if self.is_flushed:
            return
            
        print(f"📤 Flushing {len(self.buffer)} buffered log entries...")
        
        for entry in self.buffer:
            try:
                logger = get_logger(entry["subsystem"], entry["module"])
                log_method = getattr(logger, entry["level"].lower())
                log_method(entry["message"], **entry["kwargs"])
            except Exception as e:
                # Fallback to console if logger fails
                print(f"[{entry['timestamp']}] {entry['level']}: {entry['message']}")
                
        self.buffer.clear()
        self.is_flushed = True
        print("✅ Log buffer flushed successfully")


# Global buffer instance
_startup_buffer = StartupLogBuffer()


def buffer_log(level: str, message: str, **kwargs):
    """Buffer a log entry during startup."""
    _startup_buffer.add_log(level, message, **kwargs)


def flush_startup_logs():
    """Flush all startup logs to the normal logging system."""
    _startup_buffer.flush_to_logger()


def info(message: str, **kwargs):
    """Buffer an info log."""
    buffer_log("INFO", message, **kwargs)


def warning(message: str, **kwargs):
    """Buffer a warning log."""
    buffer_log("WARNING", message, **kwargs)


def error(message: str, **kwargs):
    """Buffer an error log."""
    buffer_log("ERROR", message, **kwargs)


def debug(message: str, **kwargs):
    """Buffer a debug log."""
    buffer_log("DEBUG", message, **kwargs)
