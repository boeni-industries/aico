"""
AICO Logging System

Clean, simple logging with Loki backend for centralized log aggregation.

Usage:
    # Initialize once at service startup
    from aico.core.logging import initialize_logging
    initialize_logging("backend", enable_loki=True)
    
    # Get loggers anywhere
    from aico.core.logging import get_logger
    logger = get_logger("api.gateway")
    logger.info("Request received", extra={"user_id": "123"})
"""

from .simple import (
    initialize_logging,
    get_logger,
    set_log_context,
    clear_log_context,
    shutdown_logging,
    get_loki_stats,
    is_initialized,
    get_service_name
)

__all__ = [
    'initialize_logging',
    'get_logger',
    'set_log_context',
    'clear_log_context',
    'shutdown_logging',
    'get_loki_stats',
    'is_initialized',
    'get_service_name'
]
