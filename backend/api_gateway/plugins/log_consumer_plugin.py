"""
Log Consumer Plugin for AICO API Gateway

Integrates ZMQ log consumption into the modular plugin architecture,
maintaining architectural consistency by treating log consumer as a plugin
rather than an external dependency injection.
"""

import asyncio
from typing import Dict, Any, Optional

from ..core.plugin_registry import PluginInterface, PluginMetadata, PluginPriority
from aico.core.logging import get_logger


class LogConsumerPlugin(PluginInterface):
    """
    Log consumer plugin for centralized log collection via ZMQ transport
    
    Provides unified logging infrastructure as a plugin component,
    maintaining architectural consistency with the modular design.
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
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
                "topic_prefix": {"type": "string", "default": "logs."},
                "batch_size": {"type": "integer", "default": 100},
                "flush_interval": {"type": "integer", "default": 5}
            }
        )
    
    async def initialize(self, dependencies: Dict[str, Any]) -> None:
        """Initialize log consumer with database connection"""
        try:
            config_manager = dependencies.get('config')
            self.db_connection = dependencies.get('db_connection')
            
            if not config_manager:
                raise ValueError("ConfigurationManager dependency required")
            
            if not self.db_connection:
                self.logger.warning("No database connection provided - log consumer will not persist logs")
                return
            
            # Import and initialize log consumer
            from backend.log_consumer import AICOLogConsumer
            from aico.core.logging import initialize_logging

            # Get the shared ZMQ context from the global logger factory
            logger_factory = initialize_logging(config_manager)
            zmq_context = logger_factory.get_zmq_context()

            if not zmq_context:
                self.logger.error("Failed to get ZMQ context for LogConsumerPlugin")
                return

            self.log_consumer = AICOLogConsumer(
                config_manager=config_manager,
                db_connection=self.db_connection,
                zmq_context=zmq_context
            )
            
            self.logger.info("Log consumer plugin initialized", extra={
                "db_connection": "provided" if self.db_connection else "none",
                "zmq_enabled": True
            })
            
        except Exception as e:
            self.logger.error(f"Failed to initialize log consumer plugin: {e}")
            raise
    
    async def start(self) -> None:
        """Start the log consumer service"""
        if not self.enabled or not self.log_consumer:
            self.logger.info("Log consumer plugin disabled or not initialized")
            return
        
        try:
            await self.log_consumer.start()
            self.logger.info("Log consumer plugin started - ZMQ log transport active")
            
        except Exception as e:
            self.logger.error(f"Failed to start log consumer plugin: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the log consumer service"""
        if self.log_consumer:
            try:
                await self.log_consumer.stop()
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
