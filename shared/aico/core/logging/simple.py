"""
AICO Simple Logging System

Clean, minimal logging with InfluxDB backend.
Replaces the old 934-line complexity with ~100 lines of clarity.

Usage:
    # Initialize once at service startup
    from aico.core.logging import initialize_logging
    initialize_logging("backend", enable_influx=True)
    
    # Get loggers anywhere
    from aico.core.logging import get_logger
    logger = get_logger("api.gateway")
    logger.info("Request received", extra={"user_id": "123"})
"""

import logging
import os
import sys
from typing import Optional

from .influx_handler import InfluxDBLogHandler

# Global state
_initialized = False
_service_name = None
_influx_handler = None


def initialize_logging(
    service_name: str,
    enable_influx: bool = True,
    enable_console: bool = True,
    log_level: Optional[int] = None,
    influx_url: Optional[str] = None,
    influx_org: Optional[str] = None,
    influx_bucket: Optional[str] = None,
    influx_token: Optional[str] = None
):
    """
    Initialize logging for a service.
    
    Call this ONCE at service startup before any logging.
    
    Args:
        service_name: Service identifier (backend, modelservice, cli, etc)
        enable_influx: Enable InfluxDB logging
        enable_console: Enable console logging
        log_level: Minimum log level
        influx_url: InfluxDB URL (auto-detected if None)
        influx_org: InfluxDB org (auto-detected if None)
        influx_bucket: InfluxDB bucket (auto-detected if None)
        influx_token: InfluxDB token (from keyring if None)
    """
    global _initialized, _service_name, _influx_handler
    
    if _initialized:
        print(f"[Logging] Already initialized for service '{_service_name}'", flush=True)
        return
    
    _service_name = service_name

    resolved_log_level = log_level
    if resolved_log_level is None:
        env_level = os.getenv(f"AICO_LOG_LEVEL_{service_name.upper()}") or os.getenv("AICO_LOG_LEVEL")
        if env_level:
            resolved_log_level = logging._nameToLevel.get(env_level.upper())
        else:
            try:
                import importlib

                config_module = importlib.import_module('aico.core.config')
                ConfigurationManager = config_module.ConfigurationManager

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
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_log_level)

    # Suppress noisy third-party INFO logs (e.g. periodic health checks)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(resolved_log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Add InfluxDB handler
    if enable_influx:
        try:
            # Auto-detect config if not provided (lazy import to avoid circular deps)
            if not all([influx_url, influx_org, influx_bucket, influx_token]):
                # Use lazy imports to avoid triggering logging during config initialization
                import importlib
                
                # Import config without triggering its logging
                config_module = importlib.import_module('aico.core.config')
                ConfigurationManager = config_module.ConfigurationManager
                
                config = ConfigurationManager()
                config.initialize(lightweight=True)
                
                influx_url = influx_url or config.get("influx.url", "http://127.0.0.1:8086")
                influx_org = influx_org or config.get("influx.org", "aico")
                influx_bucket = influx_bucket or config.get("influx.bucket", "aico_telemetry")

                
                if not influx_token:
                    security_module = importlib.import_module('aico.security')
                    AICOKeyManager = security_module.AICOKeyManager
                    key_manager = AICOKeyManager(config)
                    influx_token = key_manager.get_database_password("influx", username="admin_token")
            
            if influx_token:
                _influx_handler = InfluxDBLogHandler(
                    influx_url=influx_url,
                    org=influx_org,
                    bucket=influx_bucket,
                    token=influx_token,
                    service_name=service_name,
                    buffer_size=20000,
                    flush_interval=2.0,
                    batch_size=1000
                )
                _influx_handler.setLevel(resolved_log_level)
                root_logger.addHandler(_influx_handler)
                print(f"[Logging] InfluxDB enabled for service '{service_name}'", flush=True)
            else:
                print(f"[Logging] InfluxDB token not available, skipping", flush=True)
        
        except Exception as e:
            print(f"[Logging] Failed to setup InfluxDB: {e}", flush=True)
    
    _initialized = True
    print(f"[Logging] Initialized for service '{service_name}'", flush=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Returns a standard Python logger with InfluxDB handler attached.
    Can be called before initialize_logging() - will return basic logger.
    
    Args:
        name: Full logger name with service context (e.g. "backend.api.gateway", "shared.security.key_manager")
        
    Returns:
        Standard Python logging.Logger instance
        
    Example:
        logger = get_logger("backend.api.gateway")
        logger.info("Request received", extra={"user_id": "123"})
    """
    return logging.getLogger(name)


def shutdown_logging():
    """
    Shutdown logging system gracefully.
    
    Flushes all buffered logs and closes handlers.
    Call this on service shutdown.
    """
    global _influx_handler, _initialized
    
    if _influx_handler:
        try:
            _influx_handler.close()
            print(f"[Logging] InfluxDB handler closed", flush=True)
        except Exception as e:
            print(f"[Logging] Error closing InfluxDB handler: {e}", flush=True)
        _influx_handler = None
    
    # Shutdown Python logging
    logging.shutdown()
    
    _initialized = False
    print(f"[Logging] Shutdown complete", flush=True)


def get_influx_stats() -> dict:
    """
    Get InfluxDB handler statistics.
    
    Returns:
        Dictionary with stats or empty dict if handler not available
    """
    if _influx_handler:
        return _influx_handler.get_stats()
    return {}


def is_initialized() -> bool:
    """Check if logging has been initialized."""
    return _initialized


def get_service_name() -> Optional[str]:
    """Get the current service name."""
    return _service_name
