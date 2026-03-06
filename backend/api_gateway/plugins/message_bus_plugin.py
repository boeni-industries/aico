"""
Message Bus Plugin for AICO API Gateway

Integrates the central message bus broker into the modular plugin architecture,
maintaining architectural consistency by treating message bus as a plugin
rather than external dependency injection.
"""

import asyncio
from typing import Dict, Any, Optional

from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from aico.core.logging import get_logger


class MessageBusPlugin(BasePlugin):
    """
    Message bus plugin for centralized message broker and module coordination
    
    Provides unified message bus infrastructure as a plugin component,
    maintaining architectural consistency with the modular design.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="message_bus",
            version="1.0.0",
            description="Central message bus broker for inter-module communication",
            priority=PluginPriority.INFRASTRUCTURE,  # Infrastructure-level plugin
            dependencies=[],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "persistence_enabled": {"type": "boolean", "default": True},
                "topic_permissions": {"type": "object", "default": {}}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize plugin with dependencies"""
        # No dependencies needed - message bus is pure infrastructure
        pass
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request - required by PluginInterface"""
        return context
    
    async def start(self) -> None:
        """Start the message bus broker"""
        # NATS-only: broker is external (Docker: aico-nats). This plugin is kept
        # for compatibility with the plugin system but does not start any embedded broker.
        self.logger.info("Message bus plugin start skipped (NATS-only; external bus)")
    
    async def stop(self) -> None:
        """Stop the message bus broker"""
        return
    
    
    async def process_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Message bus doesn't process responses - it's infrastructure"""
        return context
    
    async def health_check(self) -> Dict[str, Any]:
        """Check message bus health status"""
        if not self.enabled:
            return {"status": "disabled", "message": "Message bus plugin disabled"}

        return {"status": "external", "message": "NATS is external"}

    async def shutdown(self) -> None:
        """Cleanup message bus plugin resources"""
        self.logger.info("Shutting down message bus plugin...")
        self.logger.info("Message bus plugin shutdown complete")
