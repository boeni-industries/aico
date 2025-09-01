"""
Log Consumer Plugin for AICO API Gateway

Integrates ZMQ log consumption into the modular plugin architecture,
maintaining architectural consistency by treating log consumer as a plugin
rather than an external dependency injection.
"""

import asyncio
from typing import Dict, Any, Optional

from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from aico.core.config import ConfigurationManager
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics


class LogConsumerPlugin(BasePlugin):
    """
    Log consumer plugin for centralized log collection via ZMQ transport
    
    Provides unified logging infrastructure as a plugin component,
    maintaining architectural consistency with the modular design.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.log_consumer: Optional[Any] = None
        self.db_connection: Optional[Any] = None
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="log_consumer",
            version="1.0.0",
            description="ZMQ log transport consumer for centralized logging",
            priority=PluginPriority.INFRASTRUCTURE,  # Infrastructure-level plugin
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "zmq_sub_port": {"type": "integer", "default": 5556},
                "zmq_host": {"type": "string", "default": "localhost"},
                "topic_prefix": {"type": "string", "default": "logs/"},
                "batch_size": {"type": "integer", "default": 100},
                "flush_interval": {"type": "integer", "default": 5}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize log consumer with database connection"""
        try:
            # Create log consumer service directly
            from backend.services.log_consumer_service import LogConsumerService
            
            self.log_consumer = LogConsumerService("log_consumer", self.container)
            self.logger.info(f"Log consumer service created: {self.log_consumer is not None}")
            
            await self.log_consumer.initialize()
            self.logger.info("Log consumer service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize log consumer plugin: {e}", exc_info=True)
            # Don't raise - let plugin continue without log consumer
            self.log_consumer = None
    
    async def start(self) -> None:
        """Start the log consumer service"""
        if not self.enabled:
            self.logger.info("Log consumer plugin disabled")
            return
            
        if not self.log_consumer:
            self.logger.warning("Log consumer not initialized - attempting to initialize now")
            try:
                await self.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize log consumer during start: {e}")
                return
        
        try:
            await self.log_consumer.start()
            self.running = True
            self.logger.info("Log consumer plugin started - ZMQ log transport active")
            
        except Exception as e:
            self.logger.error(f"Failed to start log consumer plugin: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the log consumer service"""
        if self.log_consumer:
            try:
                await self.log_consumer.stop()  # stop() is async in LogConsumerService
                self.logger.info("Log consumer plugin stopped")
            except Exception as e:
                self.logger.error(f"Error stopping log consumer plugin: {e}")
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Log consumer doesn't process requests - it's infrastructure"""
        return context
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Log consumer doesn't process responses - it's infrastructure"""
        return context
    
    def get_log_consumer(self) -> Optional[Any]:
        """Get the log consumer instance for external access"""
        return self.log_consumer
    
    async def health_check(self) -> Dict[str, Any]:
        """Check log consumer health status"""
        if not self.enabled:
            return {"status": "disabled", "message": "Log consumer plugin disabled"}
        
        if not self.log_consumer:
            return {"status": "error", "message": "Log consumer not initialized"}
        
        try:
            # Check if log consumer is running
            is_running = getattr(self.log_consumer, 'running', False)
            
            return {
                "status": "healthy" if is_running else "stopped",
                "message": f"Log consumer {'running' if is_running else 'stopped'}",
                "db_connection": "available" if self.db_connection else "none",
                "zmq_transport": "active" if is_running else "inactive"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Health check failed: {e}"
            }
    
    async def shutdown(self) -> None:
        """Cleanup log consumer plugin resources"""
        self.logger.info("Shutting down log consumer plugin...")
        if self.log_consumer:
            try:
                await self.log_consumer.stop()
                self.log_consumer = None
            except Exception as e:
                self.logger.error(f"Error during log consumer shutdown: {e}")
        self.logger.info("Log consumer plugin shutdown complete")
