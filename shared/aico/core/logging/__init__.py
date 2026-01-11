"""
AICO Logging System

Clean, simple logging with InfluxDB backend for centralized telemetry.

Usage:
    # Initialize once at service startup
    from aico.core.logging import initialize_logging
    initialize_logging("backend", enable_influx=True)
    
    # Get loggers anywhere
    from aico.core.logging import get_logger
    logger = get_logger("api.gateway")
    logger.info("Request received", extra={"user_id": "123"})
"""

from .simple import (
    initialize_logging,
    get_logger,
    shutdown_logging,
    get_influx_stats,
    is_initialized,
    get_service_name
)

from .influx_handler import InfluxDBLogHandler

__all__ = [
    'initialize_logging',
    'get_logger',
    'shutdown_logging',
    'get_influx_stats',
    'is_initialized',
    'get_service_name',
    'InfluxDBLogHandler'
]
