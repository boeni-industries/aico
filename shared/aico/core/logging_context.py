"""
AICO Logging Context Management

Provides clean isolation for logging infrastructure components to prevent
circular dependencies and feedback loops.
"""

import logging
import threading
from typing import Optional, Set
from contextlib import contextmanager


class LoggingContext:
    """Thread-local context manager for logging isolation"""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def is_infrastructure_context(self) -> bool:
        """Check if we're in logging infrastructure context"""
        return getattr(self._local, 'infrastructure_context', False)
    
    @property
    def excluded_transports(self) -> Set[str]:
        """Get set of transport types to exclude in current context"""
        return getattr(self._local, 'excluded_transports', set())
    
    @contextmanager
    def infrastructure_logging(self, component_name: str):
        """Context manager for logging infrastructure components"""
        old_context = getattr(self._local, 'infrastructure_context', False)
        old_excluded = getattr(self._local, 'excluded_transports', set())
        
        try:
            self._local.infrastructure_context = True
            self._local.excluded_transports = old_excluded | {'zmq'}
            self._local.component_name = component_name
            yield
        finally:
            self._local.infrastructure_context = old_context
            self._local.excluded_transports = old_excluded
            if hasattr(self._local, 'component_name'):
                delattr(self._local, 'component_name')


# Global context instance
_logging_context = LoggingContext()


def get_logging_context() -> LoggingContext:
    """Get the global logging context"""
    return _logging_context


class InfrastructureLogger:
    """Logger for infrastructure components that avoids circular dependencies"""
    
    def __init__(self, name: str):
        self.name = name
        self._python_logger = logging.getLogger(f"aico.infrastructure.{name}")
        # Set to WARNING level to reduce console spam - only show warnings and errors
        self._python_logger.setLevel(logging.WARNING)
        
        # Only add handler if none exists
        if not self._python_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s infrastructure.%(name)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self._python_logger.addHandler(handler)
            self._python_logger.propagate = False
    
    def debug(self, message: str, **kwargs):
        self._python_logger.debug(message)
    
    def info(self, message: str, **kwargs):
        self._python_logger.info(message)
    
    def warning(self, message: str, **kwargs):
        self._python_logger.warning(message)
    
    def error(self, message: str, **kwargs):
        self._python_logger.error(message)
    
    def critical(self, message: str, **kwargs):
        self._python_logger.critical(message)


def create_infrastructure_logger(component_name: str) -> InfrastructureLogger:
    """Create a logger for infrastructure components"""
    return InfrastructureLogger(component_name)
