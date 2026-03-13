"""
Gateway Message Router

Routes HTTP/WebSocket requests to Core service via NATS messaging.
Implements request/reply pattern with timeout handling and error recovery.

This component is the bridge between HTTP/WS protocols and NATS messaging,
ensuring Gateway remains stateless and delegates all business logic to Core.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from aico.core.logging import get_logger
from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient


@dataclass
class RouteResult:
    """Result of a routed message"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: int = 200


class MessageRouter:
    """
    Gateway Message Router
    
    Routes requests from Gateway to Core service via NATS.
    Handles request/reply pattern, timeouts, and error recovery.
    
    Responsibilities:
    - Route HTTP/WS requests to NATS subjects
    - Handle request/reply pattern
    - Timeout management
    - Error handling and retries
    - Event subscriptions for real-time updates
    """
    
    def __init__(self, config: ConfigurationManager, message_bus: MessageBusClient):
        self.config = config
        self.message_bus = message_bus
        self.logger = get_logger("gateway.middleware.message_router")
        
        # Routing configuration
        self.default_timeout = config.get("message_bus.timeout", 5.0)
        self.max_retries = config.get("message_router.max_retries", 2)
        
        # Subject prefixes for routing
        self.core_prefix = "core"
        self.gateway_prefix = "gateway"
        
        # Event subscriptions
        self.subscriptions: Dict[str, Callable] = {}
        
        self.logger.info("Message router initialized", extra={
            "default_timeout": self.default_timeout,
            "max_retries": self.max_retries
        })
    
    async def route_request(
        self,
        subject: str,
        payload: Dict[str, Any],
        timeout: Optional[float] = None,
        retry: bool = True
    ) -> RouteResult:
        """
        Route request to NATS subject and wait for reply
        
        Args:
            subject: NATS subject to send request to
            payload: Request payload
            timeout: Request timeout in seconds (default: 5.0)
            retry: Whether to retry on failure
        
        Returns:
            RouteResult with response data or error
        """
        timeout = timeout or self.default_timeout
        attempts = 0
        max_attempts = self.max_retries + 1 if retry else 1
        
        while attempts < max_attempts:
            attempts += 1
            
            try:
                self.logger.debug(f"Routing request to {subject}", extra={
                    "subject": subject,
                    "attempt": attempts,
                    "timeout": timeout
                })
                
                # Send request and wait for reply
                response = await asyncio.wait_for(
                    self.message_bus.request(subject, payload),
                    timeout=timeout
                )
                
                # Parse response
                if isinstance(response, dict):
                    response_data = response
                else:
                    response_data = json.loads(response) if isinstance(response, (str, bytes)) else {}
                
                # Check for error in response
                if response_data.get("error"):
                    error_msg = response_data.get("error")
                    status_code = response_data.get("status_code", 500)
                    
                    self.logger.warning(f"Core returned error", extra={
                        "subject": subject,
                        "error": error_msg,
                        "status_code": status_code
                    })
                    
                    return RouteResult(
                        success=False,
                        error=error_msg,
                        status_code=status_code
                    )
                
                # Success
                self.logger.debug(f"Request routed successfully", extra={
                    "subject": subject,
                    "attempt": attempts
                })
                
                return RouteResult(
                    success=True,
                    data=response_data.get("data", response_data),
                    status_code=response_data.get("status_code", 200)
                )
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Request timeout on attempt {attempts}", extra={
                    "subject": subject,
                    "timeout": timeout,
                    "attempt": attempts
                })
                
                if attempts >= max_attempts:
                    return RouteResult(
                        success=False,
                        error=f"Request timeout after {attempts} attempts",
                        status_code=504
                    )
                
                # Exponential backoff before retry
                await asyncio.sleep(0.1 * (2 ** (attempts - 1)))
                
            except Exception as e:
                self.logger.error(f"Request routing error: {e}", extra={
                    "subject": subject,
                    "attempt": attempts,
                    "error": str(e)
                })
                
                if attempts >= max_attempts:
                    return RouteResult(
                        success=False,
                        error=f"Request failed: {str(e)}",
                        status_code=503
                    )
                
                await asyncio.sleep(0.1 * (2 ** (attempts - 1)))
        
        return RouteResult(
            success=False,
            error="Max retries exceeded",
            status_code=503
        )
    
    async def route_to_core(
        self,
        operation: str,
        data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> RouteResult:
        """
        Route request to Core service
        
        Args:
            operation: Operation name (e.g., "user.create", "conversation.list")
            data: Request data
            timeout: Request timeout
        
        Returns:
            RouteResult with response
        """
        subject = f"{self.core_prefix}.{operation}"
        
        # Add metadata
        payload = {
            "operation": operation,
            "data": data,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "gateway"
            }
        }
        
        return await self.route_request(subject, payload, timeout)
    
    async def subscribe_to_events(
        self,
        topics: list,
        callback: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """
        Subscribe to Core events for real-time updates
        
        Args:
            topics: List of event topics to subscribe to
            callback: Callback function for received events
        
        Returns:
            True if subscription successful
        """
        try:
            for topic in topics:
                subject = f"{self.core_prefix}.events.{topic}"
                
                # Create wrapper callback that handles message parsing
                async def message_handler(msg):
                    try:
                        if isinstance(msg, dict):
                            data = msg
                        else:
                            data = json.loads(msg) if isinstance(msg, (str, bytes)) else {}
                        
                        await callback(data)
                    except Exception as e:
                        self.logger.error(f"Event callback error: {e}", extra={
                            "topic": topic,
                            "error": str(e)
                        })
                
                # Subscribe to subject
                await self.message_bus.subscribe(subject, message_handler)
                self.subscriptions[topic] = callback
                
                self.logger.info(f"Subscribed to events", extra={"topic": topic})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Event subscription error: {e}", extra={
                "topics": topics,
                "error": str(e)
            })
            return False
    
    async def unsubscribe_from_events(self, topics: list) -> bool:
        """
        Unsubscribe from Core events
        
        Args:
            topics: List of event topics to unsubscribe from
        
        Returns:
            True if unsubscription successful
        """
        try:
            for topic in topics:
                subject = f"{self.core_prefix}.events.{topic}"
                
                # Unsubscribe from subject
                await self.message_bus.unsubscribe(subject)
                
                if topic in self.subscriptions:
                    del self.subscriptions[topic]
                
                self.logger.info(f"Unsubscribed from events", extra={"topic": topic})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Event unsubscription error: {e}", extra={
                "topics": topics,
                "error": str(e)
            })
            return False
    
    async def publish_event(
        self,
        topic: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Publish event to Gateway topic (for Gateway-specific events)
        
        Args:
            topic: Event topic
            data: Event data
        
        Returns:
            True if publish successful
        """
        try:
            subject = f"{self.gateway_prefix}.events.{topic}"
            
            payload = {
                "topic": topic,
                "data": data,
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "gateway"
                }
            }
            
            await self.message_bus.publish(subject, payload)
            
            self.logger.debug(f"Published event", extra={"topic": topic})
            return True
            
        except Exception as e:
            self.logger.error(f"Event publish error: {e}", extra={
                "topic": topic,
                "error": str(e)
            })
            return False
    
    def get_subscriptions(self) -> list:
        """Get list of active subscriptions"""
        return list(self.subscriptions.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "active_subscriptions": len(self.subscriptions),
            "subscribed_topics": list(self.subscriptions.keys()),
            "default_timeout": self.default_timeout,
            "max_retries": self.max_retries
        }


class CoreOperations:
    """
    Convenience wrapper for common Core operations
    
    Provides typed methods for common operations to avoid
    string-based subject construction throughout the codebase.
    """
    
    def __init__(self, router: MessageRouter):
        self.router = router
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> RouteResult:
        """Create user in Core"""
        return await self.router.route_to_core("user.create", user_data)
    
    async def get_user(self, user_id: str) -> RouteResult:
        """Get user from Core"""
        return await self.router.route_to_core("user.get", {"user_id": user_id})
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> RouteResult:
        """Update user in Core"""
        return await self.router.route_to_core("user.update", {
            "user_id": user_id,
            "updates": updates
        })
    
    # Conversation operations
    async def list_conversations(self, user_id: str) -> RouteResult:
        """List user conversations"""
        return await self.router.route_to_core("conversation.list", {"user_id": user_id})
    
    async def get_conversation(self, conversation_id: str) -> RouteResult:
        """Get conversation details"""
        return await self.router.route_to_core("conversation.get", {
            "conversation_id": conversation_id
        })
    
    async def send_message(self, conversation_id: str, message: Dict[str, Any]) -> RouteResult:
        """Send message to conversation"""
        return await self.router.route_to_core("conversation.message", {
            "conversation_id": conversation_id,
            "message": message
        })
    
    # System operations
    async def get_system_topology(self) -> RouteResult:
        """Get system topology"""
        return await self.router.route_to_core("system.topology", {})
    
    async def health_check(self) -> RouteResult:
        """Check Core health"""
        return await self.router.route_to_core("system.health", {})
