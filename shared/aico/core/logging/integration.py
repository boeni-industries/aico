"""
Logging Integration

Integration layer to add InfluxDB and Loki handlers to existing logging system.
Supports parallel logging to both systems during migration.
"""

import logging
import os
from typing import Optional
from .influx_handler import InfluxDBLogHandler
from .loki_handler import LokiLogHandler


def _resolve_log_level(service_name: str, log_level: Optional[int]) -> int:
    resolved_log_level = log_level
    if resolved_log_level is None:
        env_level = os.getenv(f"AICO_LOG_LEVEL_{service_name.upper()}") or os.getenv("AICO_LOG_LEVEL")
        if env_level:
            resolved_log_level = logging._nameToLevel.get(env_level.upper())
        else:
            try:
                from aico.core.config import ConfigurationManager

                config = ConfigurationManager()
                config.initialize(lightweight=True)

                configured_level = (
                    config.get(f"logging.levels.subsystems.{service_name}")
                    or config.get("logging.levels.default")
                    or "INFO"
                )
                resolved_log_level = logging._nameToLevel.get(str(configured_level).upper(), logging.INFO)
            except Exception:
                resolved_log_level = logging.INFO

    if resolved_log_level is None:
        resolved_log_level = logging.INFO

    return resolved_log_level


def add_influx_handler_to_logger(
    logger: logging.Logger,
    influx_url: str,
    org: str,
    bucket: str,
    token: str,
    service_name: str,
    level: Optional[int] = None,
    **handler_kwargs
) -> InfluxDBLogHandler:
    """
    Add InfluxDB handler to an existing logger.
    
    Args:
        logger: Python logger instance
        influx_url: InfluxDB URL
        org: InfluxDB organization
        bucket: InfluxDB bucket
        token: InfluxDB API token
        service_name: Service identifier
        level: Minimum log level for this handler
        **handler_kwargs: Additional InfluxDBLogHandler arguments
        
    Returns:
        The created InfluxDBLogHandler instance
    """
    raise RuntimeError(
        "InfluxDB logging has been removed. Use Loki logging via setup_loki_logging() / initialize_logging()."
    )


def setup_influx_logging(
    service_name: str,
    influx_url: Optional[str] = None,
    org: Optional[str] = None,
    bucket: Optional[str] = None,
    token: Optional[str] = None,
    enabled: bool = True,
    level: Optional[int] = None
) -> Optional[InfluxDBLogHandler]:
    """
    Set up InfluxDB logging for a service.
    
    Adds InfluxDB handler to the root logger, making it available
    to all loggers in the application.
    
    Args:
        service_name: Service identifier (backend, modelservice, cli, etc)
        influx_url: InfluxDB URL (defaults to config or localhost)
        org: InfluxDB org (defaults to config or 'aico')
        bucket: InfluxDB bucket (defaults to config or 'aico_telemetry')
        token: InfluxDB token (from keyring if not provided)
        enabled: Whether to enable InfluxDB logging
        
    Returns:
        InfluxDBLogHandler instance or None if disabled/failed
    """
    # InfluxDB log export is no longer supported. Keep this function as a
    # compatibility shim to ensure older code paths can't silently write logs.
    return None


def add_loki_handler_to_logger(
    logger: logging.Logger,
    loki_url: str,
    service_name: str,
    level: Optional[int] = None,
    **handler_kwargs
) -> LokiLogHandler:
    """
    Add Loki handler to an existing logger.
    
    Args:
        logger: Python logger instance
        loki_url: Loki URL
        service_name: Service identifier
        level: Minimum log level for this handler
        **handler_kwargs: Additional LokiLogHandler arguments
        
    Returns:
        The created LokiLogHandler instance
    """
    resolved_level = _resolve_log_level(service_name=service_name, log_level=level)
    handler = LokiLogHandler(
        loki_url=loki_url,
        service_name=service_name,
        **handler_kwargs
    )
    handler.setLevel(resolved_level)
    logger.addHandler(handler)
    return handler


def setup_loki_logging(
    service_name: str,
    loki_url: Optional[str] = None,
    enabled: bool = True,
    level: Optional[int] = None
) -> Optional[LokiLogHandler]:
    """
    Set up Loki logging for a service.
    
    Adds Loki handler to the root logger, making it available
    to all loggers in the application.
    
    Args:
        service_name: Service identifier (backend, modelservice, cli, etc)
        loki_url: Loki URL (defaults to config or localhost)
        enabled: Whether to enable Loki logging
        level: Minimum log level
        
    Returns:
        LokiLogHandler instance or None if disabled/failed
    """
    if not enabled:
        return None
    
    try:
        # Get config if not provided
        if not loki_url:
            from aico.core.config import ConfigurationManager
            
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            
            loki_url = loki_url or config.get("loki.url", "http://127.0.0.1:3100")
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        handler = add_loki_handler_to_logger(
            logger=root_logger,
            loki_url=loki_url,
            service_name=service_name,
            level=level
        )
        
        print(f"[Loki Logging] Enabled for service '{service_name}'", flush=True)
        return handler
    
    except Exception as e:
        print(f"[Loki Logging] Setup failed: {e}", flush=True)
        return None


# Global handler registry for cleanup
_influx_handlers = []
_loki_handlers = []


def register_influx_handler(handler: InfluxDBLogHandler):
    """Register handler for cleanup on shutdown."""
    global _influx_handlers
    _influx_handlers.append(handler)


def register_loki_handler(handler: LokiLogHandler):
    """Register handler for cleanup on shutdown."""
    global _loki_handlers
    _loki_handlers.append(handler)


def shutdown_influx_logging():
    """Shutdown all InfluxDB handlers gracefully."""
    global _influx_handlers
    for handler in _influx_handlers:
        try:
            handler.close()
        except Exception as e:
            print(f"[InfluxDB Logging] Shutdown error: {e}", flush=True)
    _influx_handlers.clear()


def shutdown_loki_logging():
    """Shutdown all Loki handlers gracefully."""
    global _loki_handlers
    for handler in _loki_handlers:
        try:
            handler.close()
        except Exception as e:
            print(f"[Loki Logging] Shutdown error: {e}", flush=True)
    _loki_handlers.clear()


def shutdown_all_logging():
    """Shutdown all logging handlers gracefully."""
    shutdown_influx_logging()
    shutdown_loki_logging()
