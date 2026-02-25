"""
Core Message Bus Implementation for AICO

Provides a hybrid broker pattern with ZeroMQ for internal communication
using Protocol Buffers for all message serialization.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Callable, Set
import uuid
from .topics import AICOTopics
from .logging import get_logger
from nats.aio.client import Client as NATS
from nats.errors import Error as NATSError
from nats.errors import TimeoutError as NATSTimeoutError
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.any_pb2 import Any as ProtoAny
from google.protobuf.message import Message as ProtobufMessage

# Optional metrics import
# Note: We have both bus.py (this file) and bus/ (directory) in aico.core
# To avoid naming conflicts, we import using importlib
try:
    import importlib.util
    import os
    import sys
    
    # Load metrics module directly from the bus directory
    metrics_path = os.path.join(os.path.dirname(__file__), 'bus', 'metrics.py')
    spec = importlib.util.spec_from_file_location("bus_metrics", metrics_path)
    metrics_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics_module)
    track_message = metrics_module.track_message
    METRICS_AVAILABLE = True
except Exception as e:
    from contextlib import contextmanager
    METRICS_AVAILABLE = False
    
    # No-op context manager when metrics aren't available
    @contextmanager
    def track_message(*args, **kwargs):
        class NoOpTracker:
            def set_success(self, success): pass
            def set_message_count(self, count): pass
            def set_processing_time(self, time_ms): pass
        yield NoOpTracker()

from .config import ConfigurationManager

# Optional protobuf imports to avoid chicken/egg problem with CLI
try:
    from ..proto.aico_core_envelope_pb2 import AicoMessage, MessageMetadata
except ImportError:
    # Protobuf files not generated yet - use fallbacks
    AicoMessage = None
    MessageMetadata = None
try:
    from aico.core.logging import get_logger
except ImportError:
    from shared.aico.core.logging import get_logger


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


class MessageBusTimeoutError(MessageBusError):
    """Raised when a request/reply times out"""
    pass  # Standard exception class definition - inherits from MessageBusError


class MessageBusClient:
    """Client interface for connecting to the message bus"""
    
    def __init__(self, client_id: str, config_manager=None, **_ignored: object):
        self.client_id = client_id
        self.config = config_manager
        self._no_subscription_warned_topics: Set[str] = set()
        self.running = False
        self.connected = False
        self.subscriptions = {}
        self.encryption_enabled = True  # Default to encrypted
        
        # Get logger with service context
        try:
            self.logger = get_logger(f"shared.bus.client.{client_id}")
        except RuntimeError:
            # Logging not initialized yet - use fallback
            import logging
            self.logger = logging.getLogger(f"shared.bus.client.{client_id}")
        
        self.subscriptions: Dict[str, Callable] = {}
        self.running = False
        self.connected = False  # Initialize connected property
        
        # Message persistence (optional)
        self.persistence_enabled = False
        self.message_log = None
        
        # NATS
        self._nats: Optional[NATS] = None
        self._nats_url: Optional[str] = None

    async def connect(self):
        """Connect to the message bus"""
        try:
            # Get configuration from config
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            bus_config = config.get("message_bus", {})

            # NATS-only
            self._nats_url = (
                bus_config.get("nats_url")
                or bus_config.get("url")
                or "nats://localhost:4222"
            )
            
            self.logger.info(
                "Connecting to NATS message bus",
                extra={"nats_url": self._nats_url, "client_id": self.client_id},
            )

            nc = NATS()
            await nc.connect(servers=[self._nats_url])
            self._nats = nc

            self.running = True
            self.connected = True  # Add connected property for compatibility

            # Compatibility attribute for callers that want to display connection target
            self.bus_url = self._nats_url

        except Exception as e:
            self.logger.error(f"Failed to connect to message bus: {e}")
            raise MessageBusError(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from the message bus"""
        self.running = False
        self.connected = False  # Update connected property

        if self._nats is not None:
            try:
                await self._nats.drain()
            finally:
                await self._nats.close()
            self._nats = None

        self.logger.info("Disconnected from message bus")

    def _topic_to_subject(self, topic: str) -> str:
        return topic.replace("/", ".")

    def _pattern_to_subject(self, pattern: str) -> str:
        # Existing callers use ZMQ-style prefix patterns like "conversation/" or "conversation/*".
        # For NATS we map those to subjects with wildcards.
        subject = self._topic_to_subject(pattern)
        if subject in {"*", "**"}:
            return ">"
        if subject.endswith("*"):
            subject = subject[:-1]
        if subject.endswith("."):
            return subject + ">"
        if subject.endswith(".*"):
            return subject[:-2] + ".>"
        return subject
    
    async def _verify_broker_available(self, host: str, port: int) -> bool:
        """Verify that the message bus broker is actually running and accepting connections."""
        import socket
        try:
            # Try to establish a TCP connection to the broker port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # 2 second timeout
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0  # 0 means connection successful
        except Exception:
            return False
    
    async def request(self, topic: str, payload: ProtobufMessage, 
                     timeout: float = 5.0,
                     attributes: Optional[Dict[str, str]] = None) -> ProtobufMessage:
        """Send a request and wait for a reply (NATS request/reply pattern)
        
        Args:
            topic: Topic to send request to
            payload: Protobuf message payload
            timeout: Timeout in seconds (default 5.0)
            attributes: Optional additional metadata attributes
            
        Returns:
            Reply message (protobuf)
            
        Raises:
            MessageBusError: If client not connected or request fails
            MessageBusTimeoutError: If no reply received within timeout
        """
        if not self.running or self._nats is None:
            raise MessageBusError("Client not connected")
        
        # Track request metrics
        with track_message(topic, client_id=self.client_id, direction="request") as tracker:
            # Create message metadata
            metadata = _create_message_metadata(
                message_id=str(uuid.uuid4()),
                source=self.client_id,
                message_type=topic
            )
            
            # Add optional attributes
            if attributes:
                metadata.attributes.update(attributes)
            
            # Create AICO message envelope
            from ..proto.aico_core_envelope_pb2 import AicoMessage
            message = AicoMessage()
            message.metadata.CopyFrom(metadata)
            
            # Pack payload into Any field
            any_payload = ProtoAny()
            any_payload.Pack(payload)
            message.any_payload.CopyFrom(any_payload)
            
            # Serialize message
            message_data = message.SerializeToString()
            
            subject = self._topic_to_subject(topic)
            
            try:
                # Send request and wait for reply
                reply_msg = await self._nats.request(subject, message_data, timeout=timeout)
                
                # Parse reply envelope
                reply_envelope = AicoMessage()
                reply_envelope.ParseFromString(reply_msg.data)
                
                return reply_envelope
                
            except NATSTimeoutError:
                raise MessageBusTimeoutError(f"Request to '{topic}' timed out after {timeout}s")
            except Exception as e:
                raise MessageBusError(f"Request failed: {e}")
    
    async def publish(self, topic: str, payload: ProtobufMessage, 
                     correlation_id: Optional[str] = None, 
                     reply_to: Optional[str] = None,
                     attributes: Optional[Dict[str, str]] = None):
        """Publish a protobuf message to a topic
        
        Args:
            topic: Topic to publish to
            payload: Protobuf message payload
            correlation_id: Optional correlation ID for request/response matching
            reply_to: Optional specific response topic for this request (enables targeted responses)
            attributes: Optional additional metadata attributes
        """
        if not self.running or self._nats is None:
            raise MessageBusError("Client not connected")
        
        # Track message publication metrics with client context
        with track_message(topic, client_id=self.client_id, direction="publish") as tracker:
            # Create message metadata
            metadata = _create_message_metadata(
                message_id=str(uuid.uuid4()),
                source=self.client_id,
                message_type=topic
            )
            
            # Add optional attributes
            if correlation_id:
                metadata.attributes["correlation_id"] = correlation_id
            if reply_to:
                metadata.attributes["reply_to"] = reply_to
            if attributes:
                metadata.attributes.update(attributes)
            
            # Create AICO message envelope
            from ..proto.aico_core_envelope_pb2 import AicoMessage
            message = AicoMessage()
            message.metadata.CopyFrom(metadata)
            
            # Pack payload into Any field
            any_payload = ProtoAny()
            any_payload.Pack(payload)
            message.any_payload.CopyFrom(any_payload)
            
            # Serialize message
            message_data = message.SerializeToString()
            
            subject = self._topic_to_subject(topic)
            await self._nats.publish(subject, message_data)
            
            # Metrics are automatically recorded by track_message context manager
            # (duration and count are tracked automatically)
            
            # Security logging: Message publication (disabled to prevent feedback loop)
            # encryption_status = "encrypted" if self.encryption_enabled else "plaintext"
            # self.logger.debug(f"Published {encryption_status} protobuf message to topic '{topic}': {metadata.message_id}")
            # self.logger.debug(f"Message data length: {len(message_data)} bytes")
            # Skip security warnings for infrastructure components to prevent feedback loops
            if not self.encryption_enabled and self.client_id not in ["log_consumer", "zmq_log_transport"]:
                self.logger.warning(f"[SECURITY] WARNING: Message {metadata.message_id} sent in plaintext to topic '{topic}'")
            
            # Encrypted message logging disabled to prevent log spam
            # Messages are encrypted and working - no need to log every single one at DEBUG level
            
            # Persist message if enabled
            if self.persistence_enabled:
                await self._persist_message(message)
    
    async def subscribe(self, topic_pattern: str, callback: Callable[[AicoMessage], None]):
        """Subscribe to messages matching a topic pattern"""
        if not self.running or self._nats is None:
            raise MessageBusError("Client not connected")

        subject = self._pattern_to_subject(topic_pattern)

        async def _handler(msg):
            from ..proto.aico_core_envelope_pb2 import AicoMessage

            envelope = AicoMessage()
            envelope.ParseFromString(msg.data)
            await self._invoke_callback(callback, envelope)

        sid = await self._nats.subscribe(subject, cb=_handler)

        # Store subscription handle under the original pattern
        self.subscriptions[topic_pattern] = sid
        
        # Security logging: Subscription
        self.logger.info(
            "Subscribed to NATS subject",
            extra={"topic_pattern": topic_pattern, "subject": subject, "client_id": self.client_id},
        )
        
    async def unsubscribe(self, topic_pattern: str):
        """Unsubscribe from a topic pattern"""
        if not self.running or self._nats is None:
            return

        sid = self.subscriptions.get(topic_pattern)
        if sid is None:
            return

        await self._nats.unsubscribe(sid)
        del self.subscriptions[topic_pattern]
        self.logger.info(f"Unsubscribed from topic pattern: {topic_pattern}")
    
    async def _message_loop(self):
        """Main message processing loop"""
        raise MessageBusError(
            "Legacy ZMQ message loop is disabled. "
            "This codebase is NATS-only: subscribe() registers NATS callbacks directly."
        )
    
    def _pattern_to_zmq_filter(self, pattern: str) -> str:
        """Convert subscription pattern to ZeroMQ prefix filter"""
        # ZMQ uses simple prefix matching, no wildcards needed
        # "*" or "**" means subscribe to all messages (empty filter)
        if pattern == "*" or pattern == "**":
            return ""  # Empty filter = receive all messages
        
        # For any other pattern, use it directly as ZMQ prefix filter
        # ZMQ will match any topic that starts with this prefix
        return pattern
    
    
    async def _invoke_callback(self, callback, message):
        """Invoke callback with proper error handling"""
        # Extract topic from message metadata for metrics
        topic = message.metadata.message_type if message.metadata else "unknown"
        source = message.metadata.source if message.metadata else "unknown"
        
        # Track message processing metrics with context
        with track_message(topic, client_id=self.client_id, direction="consume", source=source) as tracker:
            # Invoke callback
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
            
            # Metrics are automatically recorded by track_message context manager
    
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
    """Broker stub (NATS-only).

    In NATS-only mode, the broker is an external service (Docker: aico-nats).
    """

    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        self.config_manager = config_manager or ConfigurationManager()
        self.logger = get_logger("shared.bus.broker")
    
    async def start(self):
        """Start the message bus broker"""
        raise MessageBusError(
            "Embedded ZMQ broker is disabled. This codebase is NATS-only; "
            "run NATS as an external service (Docker: aico-nats) and connect via MessageBusClient."
        )

    async def stop(self):
        """Stop the message bus broker"""
        return


# Convenience functions for common usage patterns

async def create_client(client_id: str) -> MessageBusClient:
    """Create and connect a message bus client"""
    client = MessageBusClient(client_id)
    await client.connect()
    return client


async def publish_message(client: MessageBusClient, topic: str, payload: ProtobufMessage):
    """Convenience function to publish a protobuf message"""
    await client.publish(topic, payload)


def create_broker() -> MessageBusBroker:
    """Create a message bus broker"""
    return MessageBusBroker()
