"""
Core Message Bus Implementation for AICO

Provides a hybrid broker pattern with ZeroMQ for internal communication
using Protocol Buffers for all message serialization.
"""

import asyncio
import platform
import threading
import uuid
import zmq
import zmq.asyncio
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.any_pb2 import Any as ProtoAny
from google.protobuf.message import Message as ProtobufMessage

# Windows compatibility fix for ZeroMQ
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .config import ConfigurationManager
from ..proto.core import AicoMessage, MessageMetadata
from aico.core.logging import get_logger


def _create_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp"""
    timestamp = Timestamp()
    timestamp.FromDatetime(dt)
    return timestamp


def _create_message_metadata(message_id: str, source: str, message_type: str) -> MessageMetadata:
    """Create protobuf MessageMetadata"""
    metadata = MessageMetadata()
    metadata.message_id = message_id
    metadata.timestamp.CopyFrom(_create_timestamp(datetime.utcnow()))
    metadata.source = source
    metadata.message_type = message_type
    metadata.version = "1.0"
    return metadata


class MessageBusError(Exception):
    """Base exception for message bus errors"""
    pass  # Standard exception class definition - no additional implementation needed


class TopicAccessError(MessageBusError):
    """Raised when access to a topic is denied"""
    pass  # Standard exception class definition - inherits from MessageBusError


class MessageBusClient:
    """Client interface for connecting to the message bus"""
    
    def __init__(self, client_id: str, broker_address: str = "tcp://localhost:5555"):
        self.client_id = client_id
        self.broker_address = broker_address  # Keep for logging, but use config for actual connection
        self.logger = get_logger("bus", f"client.{client_id}")
        
        # ZeroMQ context and sockets
        self.context = zmq.asyncio.Context()
        self.publisher = None
        self.subscriber = None
        self.subscriptions: Dict[str, Callable] = {}
        self.running = False
        
        # Message persistence (optional)
        self.persistence_enabled = False
        self.message_log = None
    
    async def connect(self):
        """Connect to the message bus"""
        try:
            # Get configuration from config
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            bus_config = config.get("message_bus", {})
            host = bus_config.get("host", "localhost")
            pub_port = bus_config.get("pub_port", 5555)
            sub_port = bus_config.get("sub_port", 5556)
            
            self.logger.info(f"Connecting to message bus at {host}:{pub_port}/{sub_port}")
            
            # Publisher socket for sending messages
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.publisher.connect(f"tcp://{host}:{pub_port}")
            
            # Subscriber socket for receiving messages
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            
            self.running = True
            # Update broker_address to reflect actual connection
            self.broker_address = f"tcp://{host}:{pub_port}"
            self.logger.info(f"Connected to message bus at {self.broker_address}")
            
            # Start message processing loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to connect to message bus: {e}")
            raise MessageBusError(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from the message bus"""
        self.running = False
        
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        
        self.context.term()
        self.logger.info("Disconnected from message bus")
    
    async def publish(self, topic: str, payload: ProtobufMessage, 
                     correlation_id: Optional[str] = None, attributes: Optional[Dict[str, str]] = None):
        """Publish a protobuf message to a topic"""
        if not self.running:
            raise MessageBusError("Client not connected")
        
        # Create message metadata
        metadata = _create_message_metadata(
            message_id=str(uuid.uuid4()),
            source=self.client_id,
            message_type=topic
        )
        
        # Add optional attributes
        if correlation_id:
            metadata.attributes["correlation_id"] = correlation_id
        if attributes:
            metadata.attributes.update(attributes)
        
        # Create AICO message envelope
        message = AicoMessage()
        message.metadata.CopyFrom(metadata)
        
        # Pack payload into Any field
        any_payload = ProtoAny()
        any_payload.Pack(payload)
        message.any_payload.CopyFrom(any_payload)
        
        # Serialize to binary protobuf
        message_data = message.SerializeToString()
        
        # Send message with topic as routing key
        await self.publisher.send_multipart([topic.encode('utf-8'), message_data])
        
        self.logger.debug(f"Published protobuf message to topic '{topic}': {metadata.message_id}")
        
        # Persist message if enabled
        if self.persistence_enabled:
            await self._persist_message(message)
    
    async def subscribe(self, topic_pattern: str, callback: Callable[[AicoMessage], None]):
        """Subscribe to messages matching a topic pattern"""
        if not self.running:
            raise MessageBusError("Client not connected")
            
        # Convert pattern to ZMQ filter
        zmq_filter = self._pattern_to_zmq_filter(topic_pattern)
        self.subscriber.setsockopt(zmq.SUBSCRIBE, zmq_filter.encode('utf-8'))
        
        # Store callback for application-level pattern matching
        self.subscriptions[topic_pattern] = callback
        
        self.logger.info(f"Subscribed to topic pattern: {topic_pattern}")
        
    async def unsubscribe(self, topic_pattern: str):
        """Unsubscribe from a topic pattern"""
        if topic_pattern in self.subscriptions:
            del self.subscriptions[topic_pattern]
            self.subscriber.setsockopt(zmq.UNSUBSCRIBE, topic_pattern.encode('utf-8'))
            self.logger.info(f"Unsubscribed from topic pattern: {topic_pattern}")
    
    async def _message_loop(self):
        """Main message processing loop"""
        while self.running:
            try:
                # Receive message with topic
                topic, message_data = await self.subscriber.recv_multipart()
                topic = topic.decode('utf-8')
                
                # Deserialize protobuf message
                message = AicoMessage()
                message.ParseFromString(message_data)
                
                # Find matching subscriptions and invoke callbacks
                for pattern, callback in self.subscriptions.items():
                    if self._topic_matches_pattern(topic, pattern):
                        await self._invoke_callback(callback, message)
                        
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in message loop: {e}")
                    await asyncio.sleep(0.1)  # Brief pause on error
    
    def _pattern_to_zmq_filter(self, pattern: str) -> str:
        """Convert wildcard pattern to ZeroMQ prefix filter"""
        if pattern == "*" or pattern == "**":
            return ""  # Empty filter = receive all messages
        
        # Find the longest prefix before any wildcard
        if "*" in pattern:
            # For "test.*" -> "test."
            # For "system.auth.*" -> "system.auth."
            wildcard_pos = pattern.find("*")
            prefix = pattern[:wildcard_pos]
            # Remove trailing dot if pattern ends with ".*"
            if prefix.endswith("."):
                return prefix
            else:
                return prefix
        else:
            # No wildcards, use exact pattern as filter
            return pattern
    
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches subscription pattern"""
        # Simple wildcard matching (* for any segment, ** for any path)
        if pattern == "*" or pattern == "**":
            return True
        
        if "*" not in pattern:
            return topic == pattern
        
        # Convert pattern to regex-like matching
        topic_parts = topic.split('.')
        pattern_parts = pattern.split('.')
        
        return self._match_parts(topic_parts, pattern_parts)
    
    def _match_parts(self, topic_parts: List[str], pattern_parts: List[str]) -> bool:
        """Match topic parts against pattern parts"""
        if not pattern_parts:
            return not topic_parts
        
        if not topic_parts:
            return all(p == "*" for p in pattern_parts)
        
        if pattern_parts[0] == "*":
            return self._match_parts(topic_parts[1:], pattern_parts[1:])
        elif pattern_parts[0] == "**":
            # Match any number of segments
            for i in range(len(topic_parts) + 1):
                if self._match_parts(topic_parts[i:], pattern_parts[1:]):
                    return True
            return False
        else:
            return (topic_parts[0] == pattern_parts[0] and 
                   self._match_parts(topic_parts[1:], pattern_parts[1:]))
    
    async def _invoke_callback(self, callback: Callable, message: AicoMessage):
        """Invoke callback, handling both sync and async functions"""
        if asyncio.iscoroutinefunction(callback):
            await callback(message)
        else:
            callback(message)
    
    async def _persist_message(self, message: AicoMessage):
        """Persist message using the provided handler (if persistence enabled)"""
        if self.persistence_enabled and self.message_log:
            try:
                if asyncio.iscoroutinefunction(self.message_log):
                    await self.message_log(message)
                else:
                    self.message_log(message)
            except Exception as e:
                self.logger.error(f"Error persisting message: {e}")
    
    def enable_persistence(self, persistence_handler: Callable):
        """Enable message persistence with a handler function
        
        Args:
            persistence_handler: Async function that takes (message: AicoMessage) -> None
        """
        self.persistence_enabled = True
        self.message_log = persistence_handler
        self.logger.info("Message persistence enabled")


class MessageBusBroker:
    """Central message bus broker running in the backend service"""
    
    def __init__(self, bind_address: str = "tcp://*:5555"):
        self.bind_address = bind_address
        self.logger = get_logger("bus", "broker")
        
        # Parse ports from config
        from aico.core.config import ConfigurationManager
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        bus_config = config.get("message_bus", {})
        self.pub_port = bus_config.get("pub_port", 5555)
        self.sub_port = bus_config.get("sub_port", 5556)
        
        # ZeroMQ context and sockets
        self.context = zmq.asyncio.Context()
        self.frontend = None  # Receives from publishers
        self.backend = None   # Sends to subscribers
        
        self.running = False
        self.clients: Set[str] = set()
        
        # Topic access control
        self.topic_permissions: Dict[str, Set[str]] = {}
    
    async def start(self):
        """Start the message bus broker"""
        try:
            # Frontend socket for publishers
            self.frontend = self.context.socket(zmq.XSUB)
            self.frontend.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.frontend.bind(f"tcp://*:{self.pub_port}")
            
            # Backend socket for subscribers
            self.backend = self.context.socket(zmq.XPUB)
            self.backend.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.backend.bind(f"tcp://*:{self.sub_port}")
            
            self.running = True
            self.logger.info(f"Message bus broker started on {self.bind_address}")
            
            # Start proxy loop
            asyncio.create_task(self._proxy_loop())
            
            # Give the task a moment to start
            await asyncio.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Failed to start message bus broker: {e}")
            raise MessageBusError(f"Broker startup failed: {e}")
    
    async def stop(self):
        """Stop the message bus broker"""
        self.running = False
        
        # Close sockets with proper cleanup
        if self.frontend:
            self.frontend.close(linger=0)
        if self.backend:
            self.backend.close(linger=0)
        
        # Wait for proxy thread to finish if it exists
        if hasattr(self, 'proxy_thread') and self.proxy_thread.is_alive():
            # Give the thread a moment to notice the closed sockets and exit
            await asyncio.sleep(0.2)
            if self.proxy_thread.is_alive():
                self.logger.warning("Proxy thread still running after socket close")
        
        # Small delay to ensure sockets are fully closed
        await asyncio.sleep(0.1)
        
        # Terminate context
        if self.context:
            self.context.term()
        
        self.logger.info("Message bus broker stopped")
    
    async def _proxy_loop(self):
        """Main proxy loop for forwarding messages"""
        try:
            # Run ZeroMQ proxy in thread pool to avoid blocking event loop
            import concurrent.futures
            import threading
            
            def run_proxy():
                """Run the blocking ZeroMQ proxy in a separate thread"""
                try:
                    # Use ZeroMQ proxy for efficient message forwarding
                    zmq.proxy(self.frontend, self.backend)
                    
                    self.logger.info("zmq.proxy() returned (this should never happen)")
                except Exception as e:
                    self.logger.error(f"Error in proxy thread: {e}")
                    import traceback
                    self.logger.error(f"Proxy thread traceback: {traceback.format_exc()}")
                finally:
                    self.logger.info("Proxy thread exiting")
            
            # Start proxy in background thread
            self.proxy_thread = threading.Thread(target=run_proxy, daemon=True)
            self.proxy_thread.start()
            self.logger.info("ZeroMQ proxy started in background thread")
            
        except Exception as e:
            if self.running:
                self.logger.error(f"Error starting proxy loop: {e}")
    
    def add_topic_permission(self, client_id: str, topic_pattern: str):
        """Grant topic access permission to a client"""
        if client_id not in self.topic_permissions:
            self.topic_permissions[client_id] = set()
        self.topic_permissions[client_id].add(topic_pattern)
        self.logger.info(f"Granted topic '{topic_pattern}' access to client '{client_id}'")
    
    def remove_topic_permission(self, client_id: str, topic_pattern: str):
        """Revoke topic access permission from a client"""
        if client_id in self.topic_permissions:
            self.topic_permissions[client_id].discard(topic_pattern)
            self.logger.info(f"Revoked topic '{topic_pattern}' access from client '{client_id}'")


# Convenience functions for common usage patterns

async def create_client(client_id: str, broker_address: str = "tcp://localhost:5555") -> MessageBusClient:
    """Create and connect a message bus client"""
    client = MessageBusClient(client_id, broker_address)
    await client.connect()
    return client


async def publish_message(client: MessageBusClient, topic: str, payload: ProtobufMessage):
    """Convenience function to publish a protobuf message"""
    await client.publish(topic, payload)


def create_broker(bind_address: str = "tcp://*:5555") -> MessageBusBroker:
    """Create a message bus broker"""
    return MessageBusBroker(bind_address)
