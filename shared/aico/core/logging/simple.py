"""
AICO Simple Logging System

Clean, minimal logging with Loki backend for centralized log aggregation.

Usage:
    # Initialize once at service startup
    from aico.core.logging import initialize_logging
    initialize_logging("backend", enable_loki=True)
    
    # Get loggers anywhere
    from aico.core.logging import get_logger
    logger = get_logger("api.gateway")
    logger.info("Request received", extra={"user_id": "123"})
"""

import logging
import os
import sys
import contextvars
from typing import Optional

from .loki_handler import LokiLogHandler

_ctx_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("aico_request_id", default=None)
_ctx_client_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("aico_client_id", default=None)
_ctx_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("aico_session_id", default=None)
_ctx_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("aico_user_id", default=None)
_ctx_conversation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("aico_conversation_id", default=None)


class _AICOLogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _ctx_request_id.get()
        client_id = _ctx_client_id.get()
        session_id = _ctx_session_id.get()
        user_id = _ctx_user_id.get()
        conversation_id = _ctx_conversation_id.get()

        if request_id and not getattr(record, "request_id", None):
            record.request_id = request_id
        if client_id and not getattr(record, "client_id", None):
            record.client_id = client_id
        if session_id and not getattr(record, "session_id", None):
            record.session_id = session_id
        if user_id and not getattr(record, "user_id", None):
            record.user_id = user_id
        if conversation_id and not getattr(record, "conversation_id", None):
            record.conversation_id = conversation_id

        return True


def set_log_context(
    *,
    request_id: Optional[str] = None,
    client_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
):
    if request_id is not None:
        _ctx_request_id.set(request_id)
    if client_id is not None:
        _ctx_client_id.set(client_id)
    if session_id is not None:
        _ctx_session_id.set(session_id)
    if user_id is not None:
        _ctx_user_id.set(user_id)
    if conversation_id is not None:
        _ctx_conversation_id.set(conversation_id)


def clear_log_context():
    _ctx_request_id.set(None)
    _ctx_client_id.set(None)
    _ctx_session_id.set(None)
    _ctx_user_id.set(None)
    _ctx_conversation_id.set(None)

# Global state
_initialized = False
_service_name = None
_loki_handler = None


def initialize_logging(
    service_name: str,
    enable_loki: bool = True,
    enable_console: bool = True,
    log_level: Optional[int] = None,
    loki_url: Optional[str] = None
):
    """
    Initialize logging for a service.
    
    Call this ONCE at service startup before any logging.
    
    Args:
        service_name: Service identifier (backend, modelservice, cli, etc)
        enable_loki: Enable Loki logging
        enable_console: Enable console logging
        log_level: Minimum log level
        loki_url: Loki URL (auto-detected if None)
    """
    global _initialized, _service_name, _loki_handler
    
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

    # Inject request/user correlation fields into every record
    root_logger.addFilter(_AICOLogContextFilter())

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
    
    # Add Loki handler
    if enable_loki:
        try:
            # Auto-detect config if not provided
            if not loki_url:
                loki_url = os.getenv("AICO_LOKI_URL") or loki_url

            if not loki_url:
                import importlib
                
                config_module = importlib.import_module('aico.core.config')
                ConfigurationManager = config_module.ConfigurationManager
                
                config = ConfigurationManager()
                config.initialize(lightweight=True)
                
                loki_url = loki_url or config.get("loki.url", "http://127.0.0.1:3100")
            
            _loki_handler = LokiLogHandler(
                loki_url=loki_url,
                service_name=service_name,
                buffer_size=20000,
                flush_interval=2.0,
                batch_size=1000
            )
            _loki_handler.setLevel(resolved_log_level)
            root_logger.addHandler(_loki_handler)
            print(f"[Logging] Loki enabled for service '{service_name}'", flush=True)
        
        except Exception as e:
            print(f"[Logging] Failed to setup Loki: {e}", flush=True)
    
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
    global _loki_handler, _initialized
    
    if _loki_handler:
        try:
            _loki_handler.close()
            print(f"[Logging] Loki handler closed", flush=True)
        except Exception as e:
            print(f"[Logging] Error closing Loki handler: {e}", flush=True)
        _loki_handler = None
    
    # Shutdown Python logging
    logging.shutdown()
    
    _initialized = False
    print(f"[Logging] Shutdown complete", flush=True)


def get_loki_stats() -> dict:
    """
    Get Loki handler statistics.
    
    Returns:
        Dictionary with stats or empty dict if handler not available
    """
    if _loki_handler:
        return _loki_handler.get_stats()
    return {}


def is_initialized() -> bool:
    """Check if logging has been initialized."""
    return _initialized


def get_service_name() -> Optional[str]:
    """Get the current service name."""
    return _service_name
