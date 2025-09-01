"""
Rate Limiting Plugin for AICO API Gateway

Implements token bucket rate limiting in the modular plugin architecture.
"""

from typing import Dict, Any
from backend.core.plugin_base import BasePlugin, PluginMetadata, PluginPriority
from ..middleware.rate_limiter import RateLimiter, RateLimitExceeded
from aico.core.logging import get_logger


class RateLimitingPlugin(BasePlugin):
    """
    Rate limiting plugin using token bucket algorithm
    
    Wraps existing RateLimiter middleware into the plugin system.
    """
    
    def __init__(self, name: str, container):
        super().__init__(name, container)
        self.rate_limiter: RateLimiter = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="rate_limiting",
            version="1.0.0",
            description="Token bucket rate limiting plugin",
            priority=PluginPriority.HIGH,  # Rate limiting runs after security
            dependencies=["security"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "default_requests_per_minute": {"type": "integer", "default": 100},
                "burst_size": {"type": "integer", "default": 20},
                "cleanup_interval_minutes": {"type": "integer", "default": 5}
            }
        )
    
    async def initialize(self) -> None:
        """Initialize rate limiter"""
        try:
            # Use plugin config for rate limiter
            rate_limit_config = self.get_config("core.api_gateway.rate_limiting", {})
            self.rate_limiter = RateLimiter(rate_limit_config)
            
            self.logger.info("Rate limiting plugin initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rate limiting plugin: {e}")
            raise
    
    async def start(self) -> None:
        """Start the rate limiting plugin"""
        self.logger.info("Rate limiting plugin started")
    
    async def stop(self) -> None:
        """Stop the rate limiting plugin"""
        self.logger.info("Rate limiting plugin stopped")
    
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through rate limiting"""
        if not self.enabled:
            return context
        
        try:
            client_info = context.get('client_info', {})
            client_id = client_info.get('client_id', 'unknown')
            
            # Check rate limit
            await self.rate_limiter.check_rate_limit(client_id)
            
            self.logger.debug(f"Rate limit check passed for client: {client_id}")
            return context
            
        except RateLimitExceeded as e:
            self.logger.warning(f"Rate limit exceeded: {e}")
            context['error'] = {
                'status_code': 429,
                'message': 'Rate limit exceeded',
                'detail': str(e)
            }
            return context
        except Exception as e:
            self.logger.error(f"Rate limiting plugin error: {e}")
            # On error, allow request (fail open)
            return context
    
    async def shutdown(self) -> None:
        """Cleanup rate limiting plugin resources"""
        if self.rate_limiter:
            await self.rate_limiter.shutdown()
        self.logger.info("Rate limiting plugin shutdown")
