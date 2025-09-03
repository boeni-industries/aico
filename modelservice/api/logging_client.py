"""
AICO Logging Client for Modelservice

Uses standard AICO internal logging system with ZMQ transport
for consistent logging across all backend services.
"""

from typing import Dict, Any, Optional
from fastapi import Depends

from aico.core.logging import get_logger
from .dependencies import get_modelservice_config


class AICOLoggingClient:
    """AICO internal logging client using standard ZMQ transport"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Create loggers for different modules
        self._loggers = {}
    
    def _get_logger(self, module: str):
        """Get or create logger for specific module"""
        if module not in self._loggers:
            self._loggers[module] = get_logger("modelservice", module)
        return self._loggers[module]
    def submit_log(self, level: str, message: str, module: str = "api", 
                   topic: Optional[str] = None, **extra) -> bool:
        """Submit log entry using AICO internal logging system"""
        try:
            logger = self._get_logger(module)
            
            # Map level to logger method
            level_methods = {
                'DEBUG': logger.debug,
                'INFO': logger.info,
                'WARNING': logger.warning,
                'ERROR': logger.error,
                'CRITICAL': logger.error
            }
            
            log_method = level_methods.get(level.upper(), logger.info)
            
            # Create extra context
            extra_context = {}
            if topic:
                extra_context['topic'] = topic
            if extra:
                extra_context.update(extra)
            
            # Log using AICO internal system
            if extra_context:
                log_method(message, extra=extra_context)
            else:
                log_method(message)
                
            return True
            
        except Exception as e:
            # Fallback to print if logging fails
            print(f"[ERROR] Failed to log message: {e}")
            return False
    
    async def check_api_gateway_health(self) -> Dict[str, Any]:
        """Health check - simplified for internal logging system"""
        return {
            "status": "healthy",
            "reachable": True,
            "response_time_ms": 0,
            "note": "Using AICO internal logging system"
        }

# Dependency injection for logging client
def get_logging_client(
    config: Dict[str, Any] = Depends(get_modelservice_config)
) -> AICOLoggingClient:
    """Get AICO logging client instance."""
    return AICOLoggingClient(config)
