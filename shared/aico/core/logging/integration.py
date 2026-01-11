"""
InfluxDB Logging Integration

Simple integration layer to add InfluxDB handler to existing logging system.
Works alongside existing handlers without disrupting current architecture.
"""

import logging
from typing import Optional
from .influx_handler import InfluxDBLogHandler


def add_influx_handler_to_logger(
    logger: logging.Logger,
    influx_url: str,
    org: str,
    bucket: str,
    token: str,
    service_name: str,
    level: int = logging.DEBUG,
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
    handler = InfluxDBLogHandler(
        influx_url=influx_url,
        org=org,
        bucket=bucket,
        token=token,
        service_name=service_name,
        **handler_kwargs
    )
    handler.setLevel(level)
    logger.addHandler(handler)
    return handler


def setup_influx_logging(
    service_name: str,
    influx_url: Optional[str] = None,
    org: Optional[str] = None,
    bucket: Optional[str] = None,
    token: Optional[str] = None,
    enabled: bool = True
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
            
            influx_url = influx_url or config.get("core.database.influx.url", "http://127.0.0.1:8086")
            org = org or config.get("core.database.influx.org", "aico")
            bucket = bucket or config.get("core.database.influx.bucket", "aico_telemetry")
            
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
            level=logging.DEBUG
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
