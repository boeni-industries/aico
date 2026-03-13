"""
Core Message Bus Implementation for AICO

Provides NATS-based message bus for internal communication
using Protocol Buffers for all message serialization.
"""

import asyncio
from datetime import datetime, timezone
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

# OpenTelemetry for W3C trace context propagation
try:
    from opentelemetry import trace, context
    from opentelemetry.propagate import inject, extract
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    context = None

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
    metadata.timestamp.CopyFrom(_create_timestamp(datetime.now(timezone.utc)))
    metadata.source = source
    metadata.message_type = message_type
    metadata.version = "1.0"
    return metadata


def _inject_trace_context() -> Dict[str, str]:
    """Inject W3C trace context into a carrier dict for NATS headers"""
    if not OTEL_AVAILABLE:
        return {}
    
    carrier = {}
    inject(carrier)
    return carrier


def _extract_trace_context(headers: Optional[Dict[str, str]]) -> Optional[object]:
    """Extract W3C trace context from NATS headers and return context"""
    if not OTEL_AVAILABLE or not headers:
        return None
    
    # Extract trace context from headers
    ctx = extract(headers)
    return ctx


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

    async def _nats_error_callback(self, error: Exception):
        """Custom error callback for NATS client to provide detailed error logging.
        
        This replaces the generic 'nats: encountered error' message from the NATS library
        with actionable information about what failed and why.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Provide context-specific error messages
        if isinstance(error, NATSTimeoutError):
            self.logger.error(
                f"NATS request timed out: {error_msg}",
                extra={
                    "error_type": error_type,
                    "client_id": self.client_id,
                    "nats_url": self._nats_url,
                },
                exc_info=error
            )
        elif isinstance(error, NATSError):
            self.logger.error(
                f"NATS protocol error: {error_msg}",
                extra={
                    "error_type": error_type,
                    "client_id": self.client_id,
                    "nats_url": self._nats_url,
                },
                exc_info=error
            )
        elif isinstance(error, ConnectionError):
            self.logger.error(
                f"NATS connection error: {error_msg}",
                extra={
                    "error_type": error_type,
                    "client_id": self.client_id,
                    "nats_url": self._nats_url,
                },
                exc_info=error
            )
        else:
            # Generic error with full context
            self.logger.error(
                f"NATS client error ({error_type}): {error_msg}",
                extra={
                    "error_type": error_type,
                    "client_id": self.client_id,
                    "nats_url": self._nats_url,
                },
                exc_info=error
            )

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
            await nc.connect(
                servers=[self._nats_url],
                error_cb=self._nats_error_callback
            )
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

    def _topic_to_subject(self, topic: str, tenant_id: Optional[str] = None) -> str:
        """Convert topic to NATS subject with optional tenant scoping.
        
        Args:
            topic: Base topic string
            tenant_id: Optional tenant ID for scoping (injected as 'aico.<tenant_id>.' prefix)
            
        Returns:
            NATS subject string with tenant scope if provided
        """
        subject = topic.replace("/", ".")
        
        # Inject tenant scope if provided and not already present
        if tenant_id and not subject.startswith("aico."):
            subject = f"aico.{tenant_id}.{subject}"
        
        return subject

    def _pattern_to_subject(self, pattern: str) -> str:
        # If pattern already contains NATS wildcards (* or >) or starts with 'aico.' tenant prefix,
        # it's a literal NATS subject pattern - pass through unchanged.
        if pattern.startswith("aico.") or "*" in pattern or ">" in pattern:
            return pattern
        
        # Otherwise, convert ZMQ-style prefix patterns like "conversation/" or "conversation/*"
        # to NATS subjects with wildcards.
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
    
    async def request(
        self,
        topic: str,
        payload: ProtobufMessage,
        *,
        tenant_id: Optional[str] = None,
        timeout: float = 5.0,
        attributes: Optional[Dict[str, str]] = None,
    ) -> ProtobufMessage:
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

            # Tenant scope is an explicit parameter (Option A). We still inject it into
            # envelope metadata for downstream services that need it for processing.
            if tenant_id:
                metadata.attributes["tenant_id"] = tenant_id
            
            if attributes:
                if "tenant_id" in attributes:
                    raise MessageBusError("tenant_id must be passed explicitly, not via attributes")
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
            
            # Inject W3C trace context into NATS headers
            trace_headers = _inject_trace_context()
            
            subject = self._topic_to_subject(topic, tenant_id=tenant_id)
            
            try:
                # Send request and wait for reply
                reply_msg = await self._nats.request(subject, message_data, timeout=timeout, headers=trace_headers if trace_headers else None)
                
                # Parse reply envelope
                reply_envelope = AicoMessage()
                reply_envelope.ParseFromString(reply_msg.data)
                
                return reply_envelope
                
            except NATSTimeoutError:
                raise MessageBusTimeoutError(f"Request to '{topic}' timed out after {timeout}s")
            except Exception as e:
                raise MessageBusError(f"Request failed: {e}")
    
    async def publish(
        self,
        topic: str,
        payload: ProtobufMessage,
        *,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
    ):
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
            # Use correlation_id as envelope message_id if provided (ensures envelope ID matches payload ID)
            envelope_message_id = correlation_id if correlation_id else str(uuid.uuid4())
            metadata = _create_message_metadata(
                message_id=envelope_message_id,
                source=self.client_id,
                message_type=topic
            )

            # Tenant scope is an explicit parameter (Option A). We still inject it into
            # envelope metadata for downstream services that need it for processing.
            if tenant_id:
                metadata.attributes["tenant_id"] = tenant_id
            
            # Add optional attributes (correlation_id already used as message_id if provided)
            if correlation_id:
                metadata.attributes["correlation_id"] = correlation_id
            if reply_to:
                metadata.attributes["reply_to"] = reply_to
            if attributes:
                if "tenant_id" in attributes:
                    raise MessageBusError("tenant_id must be passed explicitly, not via attributes")
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
            
            # Inject W3C trace context into NATS headers
            trace_headers = _inject_trace_context()
            
            subject = self._topic_to_subject(topic, tenant_id=tenant_id)
            await self._nats.publish(subject, message_data, headers=trace_headers if trace_headers else None)
            
            # Metrics are automatically recorded by track_message context manager
            # (duration and count are tracked automatically)
            
            # Security logging: Message publication (disabled to prevent feedback loop)
            # encryption_status = "encrypted" if self.encryption_enabled else "plaintext"
            # self.logger.debug(f"Published {encryption_status} protobuf message to topic '{topic}': {metadata.message_id}")
            # self.logger.debug(f"Message data length: {len(message_data)} bytes")
            # Skip security warnings for infrastructure components to prevent feedback loops
            if not self.encryption_enabled and self.client_id not in ["log_consumer"]:
                self.logger.warning(f"[SECURITY] WARNING: Message {metadata.message_id} sent in plaintext to topic '{topic}'")
            
            # Encrypted message logging disabled to prevent log spam
            # Messages are encrypted and working - no need to log every single one at DEBUG level
            
            # Persist message if enabled
            if self.persistence_enabled:
                await self._persist_message(message)

    async def publish_durable(
        self,
        topic: str,
        payload: ProtobufMessage,
        *,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
        audit_subject: str = "audit.events.bus",
    ) -> None:
        if not self.running or self._nats is None:
            raise MessageBusError("Client not connected")

        from aico.core.jetstream import JetStreamManager, JetStreamStreamSpec
        from nats.js.api import RetentionPolicy

        # Create message metadata
        metadata = _create_message_metadata(
            message_id=str(uuid.uuid4()),
            source=self.client_id,
            message_type=topic,
        )

        # Tenant scope is an explicit parameter (Option A). We still inject it into
        # envelope metadata for downstream services that need it for processing.
        if tenant_id:
            metadata.attributes["tenant_id"] = tenant_id

        if correlation_id:
            metadata.attributes["correlation_id"] = correlation_id
        if reply_to:
            metadata.attributes["reply_to"] = reply_to
        if attributes:
            if "tenant_id" in attributes:
                raise MessageBusError("tenant_id must be passed explicitly, not via attributes")
            metadata.attributes.update(attributes)

        from ..proto.aico_core_envelope_pb2 import AicoMessage

        message = AicoMessage()
        message.metadata.CopyFrom(metadata)

        any_payload = ProtoAny()
        any_payload.Pack(payload)
        message.any_payload.CopyFrom(any_payload)

        message_data = message.SerializeToString()
        
        subject = self._topic_to_subject(topic, tenant_id=tenant_id)

        # Inject W3C trace context
        trace_headers = _inject_trace_context()

        js = JetStreamManager(self._nats)
        await js.ensure_stream(
            JetStreamStreamSpec(
                name="OUTBOX_EVENTS",
                subjects=["aico.*.conversation.>", "aico.*.interaction.>"],  # Tenant-scoped wildcards
                retention=RetentionPolicy.LIMITS,
                max_age_seconds=60 * 60 * 24 * 7,
                duplicate_window_seconds=60 * 60,
            )
        )
        await js.ensure_stream(
            JetStreamStreamSpec(
                name="INTERACTION_NOTIFICATIONS",
                subjects=["aico.*.interaction.notifications.>"],  # Tenant-scoped wildcards
                retention=RetentionPolicy.LIMITS,
                max_age_seconds=60 * 60 * 24 * 7,
                duplicate_window_seconds=60 * 60,
            )
        )
        await js.ensure_stream(
            JetStreamStreamSpec(
                name="AUDIT_EVENTS",
                subjects=["audit.events.>"],
                retention=RetentionPolicy.LIMITS,
                max_age_seconds=60 * 60 * 24 * 30,
                duplicate_window_seconds=60 * 60,
            )
        )

        # Merge trace context with message ID headers
        publish_headers = {"Nats-Msg-Id": metadata.message_id}
        if trace_headers:
            publish_headers.update(trace_headers)
        
        await js.publish(subject, message_data, headers=publish_headers)
        
        # Merge trace context with audit headers
        audit_headers = {
            "Nats-Msg-Id": f"audit:{metadata.message_id}",
            "aico-original-subject": subject,
            "aico-message-id": metadata.message_id,
        }
        if trace_headers:
            audit_headers.update(trace_headers)
        
        await js.publish(audit_subject, message_data, headers=audit_headers)
    
    async def subscribe(self, topic_pattern: str, callback: Callable[[AicoMessage], None], tenant_id: Optional[str] = None):
        """Subscribe to messages matching a topic pattern.
        
        Args:
            topic_pattern: Topic pattern to subscribe to
            callback: Callback function to invoke for each message
            tenant_id: Optional tenant ID for scoped subscription (prepends 'aico.<tenant_id>.')
        """
        if not self.running or self._nats is None:
            raise MessageBusError("Client not connected")

        # Convert pattern to subject and apply tenant scoping
        base_subject = self._pattern_to_subject(topic_pattern)
        if tenant_id and not base_subject.startswith("aico."):
            subject = f"aico.{tenant_id}.{base_subject}"
        else:
            subject = base_subject

        async def _handler(msg):
            from ..proto.aico_core_envelope_pb2 import AicoMessage

            envelope = AicoMessage()
            envelope.ParseFromString(msg.data)
            
            # Extract W3C trace context from NATS headers
            trace_ctx = _extract_trace_context(msg.headers)
            
            if OTEL_AVAILABLE:
                # If trace context exists, activate it; otherwise start new trace
                from opentelemetry.context import attach, detach
                token = None
                if trace_ctx:
                    token = attach(trace_ctx)
                
                try:
                    # Always create a span for message processing
                    tracer = trace.get_tracer("aico.bus")
                    with tracer.start_as_current_span(
                        f"process_message.{topic_pattern}",
                        attributes={
                            "messaging.system": "nats",
                            "messaging.destination": subject,
                            "messaging.operation": "process",
                            "messaging.message_id": envelope.metadata.message_id,
                        }
                    ):
                        await self._invoke_callback(callback, envelope)
                finally:
                    if token:
                        detach(token)
            else:
                # OpenTelemetry not available, process without tracing
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
            "Legacy message loop is disabled. "
            "This codebase is NATS-only: subscribe() registers NATS callbacks directly."
        )
    
    
    
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
            "Embedded broker is disabled. This codebase is NATS-only; "
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
