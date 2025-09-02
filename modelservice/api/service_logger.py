"""
Service Logger for Modelservice

Provides logging functionality that submits logs to API Gateway
while maintaining fallback to local AICO logging system.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from .logging_client import APIGatewayLoggingClient


class ServiceLogger:
    """
    Logger that submits logs to API Gateway with fallback to local logging
    
    Integrates with AICO's existing logging patterns while adding
    API Gateway submission for centralized log collection.
    """
    
    def __init__(self, logging_client: APIGatewayLoggingClient, subsystem: str = "modelservice", module: str = "api"):
        self.logging_client = logging_client
        self.subsystem = subsystem
        self.module = module
        
        # Fallback to local AICO logger
        self.local_logger = get_logger(subsystem, module)
        
        # Track API Gateway availability
        self._api_gateway_available = False  # Start pessimistic, force initial check
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
    
    async def _check_api_gateway_availability(self) -> bool:
        """Check if API Gateway is available for logging"""
        current_time = datetime.utcnow().timestamp()
        
        # Only check periodically to avoid overhead
        if current_time - self._last_health_check < self._health_check_interval:
            return self._api_gateway_available
        
        try:
            health = await self.logging_client.check_api_gateway_health()
            self._api_gateway_available = health.get("reachable", False)
            self._last_health_check = current_time
            
            if not self._api_gateway_available:
                self.local_logger.warning("API Gateway not available for logging, using local fallback")
            
            return self._api_gateway_available
            
        except Exception as e:
            self.local_logger.error(f"Failed to check API Gateway health: {e}")
            self._api_gateway_available = False
            self._last_health_check = current_time
            return False
    
    async def _log_async(self, level: str, message: str, topic: Optional[str] = None, **extra):
        """Async logging with API Gateway submission and local fallback"""
        try:
            # Always log locally first (immediate, reliable)
            log_method = getattr(self.local_logger, level.lower(), self.local_logger.info)
            log_method(message, extra={"topic": topic or AICOTopics.LOGS_ENTRY, **extra})
            
            # Try to submit to API Gateway if available
            if await self._check_api_gateway_availability():
                success = await self.logging_client.submit_log(
                    level=level,
                    message=message,
                    module=self.module,
                    topic=topic,
                    **extra
                )
                
                if not success:
                    self.local_logger.debug("Failed to submit log to API Gateway, local logging completed")
            
        except Exception as e:
            # Ensure local logging always works
            self.local_logger.error(f"Service logging error: {e}", extra={"original_message": message})
    
    def _log_sync(self, level: str, message: str, topic: Optional[str] = None, **extra):
        """Synchronous logging wrapper"""
        try:
            # Create new event loop if none exists
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async logging in background task
        task = loop.create_task(self._log_async(level, message, topic, **extra))
        
        # Don't wait for completion to avoid blocking
        # The local logging already happened synchronously
    
    def debug(self, message: str, topic: Optional[str] = None, **extra):
        """Debug level logging"""
        self._log_sync("DEBUG", message, topic, **extra)
    
    def info(self, message: str, topic: Optional[str] = None, **extra):
        """Info level logging"""
        self._log_sync("INFO", message, topic, **extra)
    
    def warning(self, message: str, topic: Optional[str] = None, **extra):
        """Warning level logging"""
        self._log_sync("WARNING", message, topic, **extra)
    
    def error(self, message: str, topic: Optional[str] = None, **extra):
        """Error level logging"""
        self._log_sync("ERROR", message, topic, **extra)
    
    def critical(self, message: str, topic: Optional[str] = None, **extra):
        """Critical level logging"""
        self._log_sync("CRITICAL", message, topic, **extra)


# Global service logger instance
_service_logger: Optional[ServiceLogger] = None


def get_service_logger(logging_client: APIGatewayLoggingClient, 
                      subsystem: str = "modelservice", 
                      module: str = "api") -> ServiceLogger:
    """Get or create service logger instance"""
    global _service_logger
    
    if _service_logger is None:
        _service_logger = ServiceLogger(logging_client, subsystem, module)
    
    return _service_logger
