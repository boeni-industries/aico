"""
Message Router for AICO API Gateway

Routes external API requests to internal message bus topics with:
- Topic mapping and transformation
- Request/response correlation
- Timeout handling
- Error recovery
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Shared modules now installed via UV editable install

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core import AicoMessage, MessageMetadata


@dataclass
class RoutingResult:
    """Result of message routing"""
    success: bool
    response: Optional[Any] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageRouter:
    """
    Routes external requests to internal message bus topics
    
    Handles:
    - Topic mapping (external API paths → internal topics)
    - Request/response correlation
    - Timeout management
    - Error handling and recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("api_gateway", "router")
        
        # Configuration
        self.timeout = config.get("timeout", 30)
        self.max_message_size = config.get("max_message_size", 10485760)  # 10MB
        self.topic_mapping = config.get("topic_mapping", {})
        
        # Message bus client (set by gateway)
        self.message_bus: Optional[MessageBusClient] = None
        
        # Pending requests for correlation
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        self.logger.info("Message router initialized", extra={
            "timeout": self.timeout,
            "topic_mappings": len(self.topic_mapping)
        })
    
    async def set_message_bus(self, message_bus: MessageBusClient):
        """Set message bus client and set up response handling"""
        self.logger.info("[ROUTER] Setting message bus client...")
        self.message_bus = message_bus
        
        # Subscribe to response topics (using ZMQ prefix matching)
        self.logger.info("[ROUTER] Subscribing to api/response/ topics...")
        await self.message_bus.subscribe("api/response/", self._handle_response)
        self.logger.info("[ROUTER] Subscribing to system/error/ topics...")
        await self.message_bus.subscribe("system/error/", self._handle_error)
        
        self.logger.info("[ROUTER] Message bus connected for routing")
    
    async def route_message(self, message: AicoMessage) -> RoutingResult:
        """
        Route message to appropriate internal topic
        
        Args:
            message: External message to route
            
        Returns:
            RoutingResult with response or error
        """
        try:
            if not self.message_bus:
                return RoutingResult(
                    success=False,
                    error="Message bus not connected"
                )
            
            # Generate correlation ID for request/response tracking
            correlation_id = str(uuid.uuid4())
            
            # Map external topic to internal topic
            internal_topic = self._map_topic(message.metadata.message_type)
            if not internal_topic:
                return RoutingResult(
                    success=False,
                    error=f"No route found for topic: {message.metadata.message_type}"
                )
            
            # Validate message size
            if self._estimate_message_size(message) > self.max_message_size:
                return RoutingResult(
                    success=False,
                    error="Message size exceeds maximum allowed"
                )
            
            # Create future for response tracking
            response_future = asyncio.Future()
            self.pending_requests[correlation_id] = response_future
            
            # Update message metadata for routing
            message.metadata.correlation_id = correlation_id
            message.metadata.source = "api_gateway"
            
            # Publish to internal topic
            await self.message_bus.publish(
                internal_topic,
                message.payload,
                priority=message.metadata.priority,
                correlation_id=correlation_id,
                attributes={
                    "external_topic": message.metadata.message_type,
                    "gateway_route": "true"
                }
            )
            
            self.logger.debug(f"Message routed: {message.metadata.message_type} → {internal_topic}", extra={
                "correlation_id": correlation_id,
                "message_id": message.metadata.message_id
            })
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(response_future, timeout=self.timeout)
                return RoutingResult(
                    success=True,
                    response=response,
                    correlation_id=correlation_id
                )
            except asyncio.TimeoutError:
                return RoutingResult(
                    success=False,
                    error=f"Request timeout after {self.timeout}s",
                    correlation_id=correlation_id
                )
            finally:
                # Clean up pending request
                self.pending_requests.pop(correlation_id, None)
                
        except Exception as e:
            self.logger.error(f"Message routing error: {e}")
            return RoutingResult(
                success=False,
                error=str(e)
            )
    
    def _map_topic(self, external_topic: str) -> Optional[str]:
        """Map external API topic to internal message bus topic"""
        
        # Direct mapping
        if external_topic in self.topic_mapping:
            return self.topic_mapping[external_topic]
        
        # Pattern-based mapping
        for pattern, internal_topic in self.topic_mapping.items():
            if self._topic_matches_pattern(external_topic, pattern):
                return internal_topic
        
        # Default mapping: api/* → internal topic
        if external_topic.startswith("api/"):
            return external_topic[4:]  # Remove "api/" prefix
        
        # No mapping found
        return None
    
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (simple prefix matching, no wildcards needed)"""
        # For API gateway routing, we only need simple prefix or exact matching
        # ZMQ handles prefix filtering at socket level, this is for API route mapping
        if pattern == "*":
            return True
        
        # Simple prefix matching (no wildcards needed)
        if pattern.endswith("/"):
            return topic.startswith(pattern)
        
        return topic == pattern
    
    def _estimate_message_size(self, message: AicoMessage) -> int:
        """Estimate message size in bytes"""
        try:
            # Convert to dict and estimate JSON size
            message_dict = message.to_dict()
            import json
            return len(json.dumps(message_dict).encode('utf-8'))
        except:
            # Fallback estimation
            return 1024  # 1KB default
    
    async def _handle_response(self, response_message: AicoMessage):
        """Handle response from internal services"""
        try:
            correlation_id = response_message.metadata.correlation_id
            if not correlation_id:
                self.logger.warning("Response message missing correlation_id")
                return
            
            # Find pending request
            future = self.pending_requests.get(correlation_id)
            if not future or future.done():
                self.logger.debug(f"No pending request for correlation_id: {correlation_id}")
                return
            
            # Complete the future with response
            future.set_result(response_message.payload)
            
            self.logger.debug(f"Response delivered for correlation_id: {correlation_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling response: {e}")
    
    async def _handle_error(self, error_message: AicoMessage):
        """Handle error from internal services"""
        try:
            correlation_id = error_message.metadata.correlation_id
            if not correlation_id:
                return
            
            # Find pending request
            future = self.pending_requests.get(correlation_id)
            if not future or future.done():
                return
            
            # Complete the future with error
            error_info = error_message.payload
            error_text = error_info.get("error", "Internal service error")
            future.set_exception(Exception(error_text))
            
            self.logger.debug(f"Error delivered for correlation_id: {correlation_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling error message: {e}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "pending_requests": len(self.pending_requests),
            "topic_mappings": len(self.topic_mapping),
            "timeout": self.timeout,
            "max_message_size": self.max_message_size
        }
    
    def add_topic_mapping(self, external_topic: str, internal_topic: str):
        """Add new topic mapping"""
        self.topic_mapping[external_topic] = internal_topic
        self.logger.info(f"Added topic mapping: {external_topic} → {internal_topic}")
    
    def remove_topic_mapping(self, external_topic: str):
        """Remove topic mapping"""
        if external_topic in self.topic_mapping:
            internal_topic = self.topic_mapping.pop(external_topic)
            self.logger.info(f"Removed topic mapping: {external_topic} → {internal_topic}")
    
    async def cleanup(self):
        """Clean up pending requests and resources"""
        # Cancel all pending requests
        for correlation_id, future in self.pending_requests.items():
            if not future.done():
                future.cancel()
        
        self.pending_requests.clear()
        self.logger.info("Message router cleaned up")
