"""
InfluxDB Logging Integration

Simple integration layer to add InfluxDB handler to existing logging system.
Works alongside existing handlers without disrupting current architecture.
"""

import logging
import os
from typing import Optional
from .influx_handler import InfluxDBLogHandler


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
    resolved_level = _resolve_log_level(service_name=service_name, log_level=level)
    handler = InfluxDBLogHandler(
        influx_url=influx_url,
        org=org,
        bucket=bucket,
        token=token,
        service_name=service_name,
        **handler_kwargs
    )
    handler.setLevel(resolved_level)
    logger.addHandler(handler)
    return handler


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
    if not enabled:
        return None
    
    try:
        # Get config if not provided
        if not all([influx_url, org, bucket, token]):
            from aico.core.config import ConfigurationManager
            from aico.security import AICOKeyManager
            
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            
            influx_url = influx_url or config.get("influx.url", "http://127.0.0.1:8086")
            org = org or config.get("influx.org", "aico")
            bucket = bucket or config.get("influx.bucket", "aico_telemetry")
            
            if not token:
                key_manager = AICOKeyManager(config)
                token = key_manager.get_database_password("influx", username="admin_token")
        
        if not token:
            print(f"[InfluxDB Logging] No token available, skipping setup", flush=True)
            return None
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        handler = add_influx_handler_to_logger(
            logger=root_logger,
            influx_url=influx_url,
            org=org,
            bucket=bucket,
            token=token,
            service_name=service_name,
            level=level
        )
        
        print(f"[InfluxDB Logging] Enabled for service '{service_name}'", flush=True)
        return handler
    
    except Exception as e:
        print(f"[InfluxDB Logging] Setup failed: {e}", flush=True)
        return None


# Global handler registry for cleanup
_influx_handlers = []


def register_influx_handler(handler: InfluxDBLogHandler):
    """Register handler for cleanup on shutdown."""
    global _influx_handlers
    _influx_handlers.append(handler)


def shutdown_influx_logging():
    """Shutdown all InfluxDB handlers gracefully."""
    global _influx_handlers
    for handler in _influx_handlers:
        try:
            handler.close()
        except Exception as e:
            print(f"[InfluxDB Logging] Shutdown error: {e}", flush=True)
    _influx_handlers.clear()
