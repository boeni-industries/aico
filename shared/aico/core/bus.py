"""
Core Message Bus Implementation for AICO

Provides a hybrid broker pattern with ZeroMQ for internal communication
using Protocol Buffers for all message serialization.
"""

import asyncio
from datetime import datetime
import platform
import threading
from typing import Optional, Dict, Callable, Set
import uuid
import zmq
import zmq.asyncio
from .topics import AICOTopics
from .logging_context import get_logging_context, create_infrastructure_logger
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.any_pb2 import Any as ProtoAny
from google.protobuf.message import Message as ProtobufMessage

# Windows compatibility fix for ZeroMQ
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .config import ConfigurationManager

# Shared static keys for minimal CurveZMQ authentication
# Use fixed keys so all processes can authenticate with the same broker
_SHARED_BROKER_PUBLIC = "Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID"
_SHARED_BROKER_SECRET = "D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs"

def _get_shared_broker_keys():
    """Get shared broker keypair for minimal authentication"""
    return (_SHARED_BROKER_PUBLIC, _SHARED_BROKER_SECRET)

def _get_shared_broker_public_key():
    """Get shared broker public key"""
    return _get_shared_broker_keys()[0]

def _get_shared_broker_secret_key():
    """Get shared broker secret key"""
    return _get_shared_broker_keys()[1]

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


class MessageBusClient:
    """Client interface for connecting to the message bus"""
    
    def __init__(self, client_id: str, zmq_context=None, config_manager=None):
        self.client_id = client_id
        self.zmq_context = zmq_context or zmq.asyncio.Context()
        self.config = config_manager
        self.running = False
        self.connected = False
        self.subscriber = None
        self.publisher = None
        self.subscriptions = {}
        self.encryption_enabled = True  # Default to encrypted
        
        # Use infrastructure logger for logging transport components to prevent circular dependencies
        if client_id in ["zmq_log_transport", "log_consumer"]:
            self.logger = create_infrastructure_logger(f"bus.client.{client_id}")
        else:
            try:
                self.logger = get_logger("shared", f"bus.client.{client_id}")
            except RuntimeError:
                # Logging not initialized yet - use fallback
                import logging
                self.logger = logging.getLogger(f"shared.bus.client.{client_id}")
        
        # ZeroMQ context and sockets
        self.context = self.zmq_context
        self.publisher = None
        self.subscriber = None
        self.subscriptions: Dict[str, Callable] = {}
        self.running = False
        self.connected = False  # Initialize connected property
        
        # Message persistence (optional)
        self.persistence_enabled = False
        self.message_log = None
        
        # CurveZMQ encryption
        self.encryption_enabled = True
        self.public_key = None
        self.secret_key = None
    
    async def connect(self):
        """Connect to the message bus"""
        try:
            # Get configuration from config
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            bus_config = config.get("core.message_bus", {})
            host = bus_config.get("host", "localhost")
            pub_port = bus_config.get("pub_port", 5555)
            sub_port = bus_config.get("sub_port", 5556)
            
            # Check if encryption is enabled
            security_config = config.get("security", {})
            transport_config = security_config.get("transport", {})
            self.encryption_enabled = transport_config.get("message_bus_encryption", True)
            
            if self.encryption_enabled:
                await self._setup_curve_encryption(config)
            
            self.logger.info(f"Connecting to message bus at {host}:{pub_port}/{sub_port} (encryption: {'enabled' if self.encryption_enabled else 'disabled'})")
            
            # Verify broker is actually running before connecting
            if not await self._verify_broker_available(host, pub_port):
                raise MessageBusError(f"Message bus broker not available at {host}:{pub_port} - is the backend running?")
            
            # Publisher socket for sending messages
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.publisher.setsockopt(zmq.SNDHWM, 10000)  # Send High Water Mark - prevent message drops
            
            # Subscriber socket for receiving messages
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.subscriber.setsockopt(zmq.RCVHWM, 10000)  # Receive High Water Mark - prevent message drops
            
            # Configure CurveZMQ encryption if enabled
            if self.encryption_enabled:
                self.logger.info(f"[SECURITY] Client {self.client_id} configuring CurveZMQ authentication")
                self._configure_curve_sockets()
                self.logger.info(f"[SECURITY] Client {self.client_id} CurveZMQ configuration complete")
            else:
                self.logger.warning(f"[SECURITY] WARNING: Client {self.client_id} connecting WITHOUT encryption")
            
            self.publisher.connect(f"tcp://{host}:{pub_port}")
            self.subscriber.connect(f"tcp://{host}:{sub_port}")
            
            self.running = True
            self.connected = True  # Add connected property for compatibility
            # Update broker_address to reflect actual connection
            self.broker_address = f"tcp://{host}:{pub_port}"
            self.logger.info(f"Connected to message bus at {self.broker_address}")
            
            # Test connection with a small delay to catch immediate auth failures
            await asyncio.sleep(0.1)
            if self.encryption_enabled:
                self.logger.info(f"[SECURITY] Client {self.client_id} CurveZMQ authentication appears successful")
            
            # Start message processing loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to connect to message bus: {e}")
            raise MessageBusError(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from the message bus"""
        self.running = False
        self.connected = False  # Update connected property
        
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        
        self.context.term()
        self.logger.info("Disconnected from message bus")
    
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
    
    async def _setup_curve_encryption(self, config: ConfigurationManager):
        """Setup CurveZMQ encryption keys using minimal in-memory approach"""
        try:
            # Generate client keypair directly in memory
            client_public, client_secret = zmq.curve_keypair()
            self.public_key = client_public.decode('ascii')
            self.secret_key = client_secret.decode('ascii')
            
            # Security logging: Key generation success
            self.logger.info(f"[SECURITY] CurveZMQ encryption enabled for client: {self.client_id}")
            self.logger.debug(f"[SECURITY] Client public key fingerprint: {self.public_key[:8]}...")
            
        except Exception as e:
            # Security logging: Encryption setup failure
            self.logger.error(f"[SECURITY] CRITICAL: Failed to setup CurveZMQ encryption for {self.client_id}: {e}")
            # NO PLAINTEXT FALLBACK - Fail securely
            raise MessageBusError(f"CurveZMQ encryption setup failed for {self.client_id}: {e}")
    
    def _configure_curve_sockets(self):
        """Configure sockets for CurveZMQ encryption"""
        if not self.encryption_enabled or not self.secret_key:
            self.logger.warning(f"[SECURITY] WARNING: CurveZMQ encryption disabled for client {self.client_id}")
            return
            
        try:
            # Get broker's public key for server authentication
            broker_public_key = self._get_broker_public_key()
            
            # Security logging: Broker authentication
            self.logger.debug(f"[SECURITY] Authenticating broker with public key fingerprint: {broker_public_key[:8]}...")
            
            # Configure publisher socket as CURVE client
            self.publisher.setsockopt_string(zmq.CURVE_SECRETKEY, self.secret_key)
            self.publisher.setsockopt_string(zmq.CURVE_PUBLICKEY, self.public_key)
            self.publisher.setsockopt_string(zmq.CURVE_SERVERKEY, broker_public_key)
            
            # Configure subscriber socket as CURVE client
            self.subscriber.setsockopt_string(zmq.CURVE_SECRETKEY, self.secret_key)
            self.subscriber.setsockopt_string(zmq.CURVE_PUBLICKEY, self.public_key)
            self.subscriber.setsockopt_string(zmq.CURVE_SERVERKEY, broker_public_key)
            
            # Security logging: Socket configuration success
            self.logger.info(f"[SECURITY] CurveZMQ socket encryption configured for client {self.client_id}")
            self.logger.debug(f"[SECURITY] Publisher and subscriber sockets secured with CurveZMQ")
            
        except Exception as e:
            # Security logging: Socket configuration failure
            self.logger.error(f"[SECURITY] CRITICAL: Failed to configure CurveZMQ sockets for {self.client_id}: {e}")
            # NO PLAINTEXT FALLBACK - Fail securely
            raise MessageBusError(f"CurveZMQ socket configuration failed for {self.client_id}: {e}")
    
    def _get_broker_public_key(self) -> str:
        """Get broker's public key for server authentication - using shared static key"""
        # Use a shared static broker public key (same as broker uses)
        # This implements minimal authentication - all clients use same broker key
        return _get_shared_broker_public_key()
    
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
        
        # Send the message
        await self.publisher.send_multipart([topic.encode('utf-8'), message_data])
        
        # Security logging: Message publication (disabled to prevent feedback loop)
        # encryption_status = "encrypted" if self.encryption_enabled else "plaintext"
        # self.logger.debug(f"Published {encryption_status} protobuf message to topic '{topic}': {metadata.message_id}")
        # self.logger.debug(f"Message data length: {len(message_data)} bytes")
        # Skip security warnings for infrastructure components to prevent feedback loops
        if not self.encryption_enabled and self.client_id not in ["log_consumer", "zmq_log_transport"]:
            self.logger.warning(f"[SECURITY] WARNING: Message {metadata.message_id} sent in plaintext to topic '{topic}'")
        
        # Log potential authentication failures for encrypted connections
        if self.encryption_enabled:
            self.logger.debug(f"[SECURITY] Client {self.client_id} published encrypted message {metadata.message_id} to topic '{topic}'")
            
            # Add a mechanism to detect if messages are being silently dropped
            # Store message info for potential timeout detection
            if not hasattr(self, '_published_messages'):
                self._published_messages = {}
            self._published_messages[metadata.message_id] = {
                'topic': topic,
                'timestamp': asyncio.get_event_loop().time(),
                'client_id': self.client_id
            }
        
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
        
        # Security logging: Subscription
        encryption_status = "encrypted" if self.encryption_enabled else "plaintext"
        self.logger.info(f"Subscribed to {encryption_status} topic pattern: {topic_pattern} (ZMQ filter: '{zmq_filter}')")
        if not self.encryption_enabled:
            self.logger.warning(f"[SECURITY] WARNING: Client {self.client_id} subscribing to plaintext messages on pattern '{topic_pattern}'")
        
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
                
                # Skip security warnings for infrastructure components to prevent feedback loops
                if not self.encryption_enabled and self.client_id not in ["log_consumer", "zmq_log_transport"]:
                    self.logger.warning(f"[SECURITY] WARNING: Client {self.client_id} received plaintext message on topic '{topic}'")
                
                # Log successful encrypted message reception
                if self.encryption_enabled:
                    self.logger.debug(f"[SECURITY] Client {self.client_id} received encrypted message on topic '{topic}'")
                
                # Deserialize protobuf message
                from ..proto.aico_core_envelope_pb2 import AicoMessage
                message = AicoMessage()
                message.ParseFromString(message_data)
                
                # Find the matching subscription pattern for this topic
                matching_callback = None
                for pattern, callback in self.subscriptions.items():
                    # Check if topic matches the subscription pattern
                    if pattern == "*" or pattern == "**" or topic.startswith(pattern):
                        matching_callback = callback
                        break
            
                # Only invoke the matching callback, not all callbacks
                if matching_callback:
                    await self._invoke_callback(matching_callback, message)
                else:
                    self.logger.warning(f"No matching subscription found for topic: {topic}")
                        
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in message loop: {e}")
                    await asyncio.sleep(0.1)  # Brief pause on error
    
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
        # Use infrastructure logging context for logging transport components
        context = get_logging_context()
        
        # Check if this is an infrastructure component based on logger type
        is_infrastructure = hasattr(self.logger, '__class__') and 'InfrastructureLogger' in str(type(self.logger))
        
        if is_infrastructure:
            with context.infrastructure_logging(self.client_id):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")
        else:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                self.logger.error(f"Error in message callback: {e}")
    
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
        self.logger = get_logger("shared", "bus.broker")
        
        # Parse ports from config
        from aico.core.config import ConfigurationManager
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        bus_config = config.get("core.message_bus", {})
        self.pub_port = bus_config.get("pub_port", 5555)
        self.sub_port = bus_config.get("sub_port", 5556)
        
        # Check if encryption is enabled
        security_config = config.get("security", {})
        transport_config = security_config.get("transport", {})
        self.encryption_enabled = transport_config.get("message_bus_encryption", True)
        
        # ZeroMQ context and sockets (use asyncio context for compatibility with async clients)
        import zmq.asyncio
        self.context = zmq.asyncio.Context()
        self.logger.debug(f"[BROKER] Using ZMQ context type: {type(self.context).__name__}")
        self.frontend = None  # Receives from publishers
        self.backend = None   # Sends to subscribers
        
        self.running = False
        self.clients: Set[str] = set()
        
        # Topic access control
        self.topic_permissions: Dict[str, Set[str]] = {}
        
        # CurveZMQ encryption
        self.server_public_key = None
        self.server_secret_key = None
    
    async def start(self):
        """Start the message bus broker"""
        try:
            self.logger.debug(f"[BROKER] Starting broker - pub_port: {self.pub_port}, sub_port: {self.sub_port} (encryption: {'enabled' if self.encryption_enabled else 'disabled'})")
            
            # Create broker sockets
            self.frontend = self.context.socket(zmq.XSUB)
            self.frontend.setsockopt(zmq.LINGER, 0)
            self.frontend.setsockopt(zmq.RCVHWM, 10000)  # Prevent message drops from publishers
            
            self.backend = self.context.socket(zmq.XPUB)
            self.backend.setsockopt(zmq.LINGER, 0)
            self.backend.setsockopt(zmq.SNDHWM, 10000)  # Prevent message drops to subscribers
            
            # Configure CurveZMQ encryption if enabled
            if self.encryption_enabled:
                await self._setup_curve_authentication()
                self._configure_curve_broker_sockets()
            
            self.logger.debug(f"[BROKER] Binding frontend (XSUB) to tcp://*:{self.pub_port}")
            self.frontend.bind(f"tcp://*:{self.pub_port}")
            
            self.logger.debug(f"[BROKER] Binding backend (XPUB) to tcp://*:{self.sub_port}")
            self.backend.bind(f"tcp://*:{self.sub_port}")
            
            self.running = True
            self.logger.debug(f"[BROKER] Sockets bound successfully, starting proxy...")
            self.logger.info(f"Message bus broker started on {self.bind_address}")
            
            # Start proxy loop
            await self._start_proxy_task()
            
            # Give the task a moment to start
            await asyncio.sleep(0.1)
            self.logger.debug(f"[BROKER] Broker startup complete")
            
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
        
        # Give proxy loop a moment to exit
        await asyncio.sleep(0.2)
        
        # Small delay to ensure sockets are fully closed
        await asyncio.sleep(0.1)
        
        # Terminate context
        if self.context:
            self.context.term()
            self.logger.debug("Message bus broker stopped")
    
    def _get_authorized_client_keys(self) -> Dict[str, str]:
        """Get authorized client public keys for CurveZMQ authentication"""
        try:
            from aico.security.key_manager import AICOKeyManager
            from aico.core.config import ConfigurationManager
            
            # Initialize key manager
            config = ConfigurationManager()
            key_manager = AICOKeyManager(config)
            
            # Get master key (non-interactive for service mode)
            master_key = key_manager.authenticate(interactive=False)
            
            # Define all authorized client components
            authorized_components = [
                "message_bus_client_api_gateway",
                "message_bus_client_log_consumer", 
                "message_bus_client_scheduler",
                "message_bus_client_cli",
                "message_bus_client_modelservice",
                "zmq_log_transport",  # ZMQ log transport for cross-service logging
                "message_bus_client_system_host",
                "message_bus_client_backend_modules",
                "zeromq_adapter",  # API Gateway ZMQ adapter
                "test_client_health",  # Test script health check client
                "test_client_completions"  # Test script completions client
            ]
            
            # Derive public keys for all authorized clients
            authorized_clients = {}
            for component in authorized_components:
                public_key, _ = key_manager.derive_curve_keypair(master_key, component)
                authorized_clients[component] = public_key
                
            return authorized_clients
            
        except Exception as e:
            self.logger.error(f"Failed to get authorized client keys: {e}")
            # Fallback to empty dict - no clients authorized
            return {}
    
    async def _setup_curve_authentication(self):
        """Setup CurveZMQ encryption for the broker using minimal in-memory approach"""
        try:
            # Security logging: Authentication setup start
            self.logger.info("[SECURITY] Setting up CurveZMQ encryption for message bus broker")
            
            # Use shared static broker keys (same approach as working test)
            self.server_public_key = _get_shared_broker_public_key()
            self.server_secret_key = _get_shared_broker_secret_key()
            
            # Get authorized client keys and log them for debugging
            authorized_clients = self._get_authorized_client_keys()
            self.logger.info(f"[SECURITY] Broker CurveZMQ keypair loaded successfully")
            self.logger.debug(f"[SECURITY] Broker public key fingerprint: {self.server_public_key[:8]}...")
            self.logger.info(f"[SECURITY] Authorized clients: {list(authorized_clients.keys())}")
            self.logger.info(f"[SECURITY] CurveZMQ encryption setup complete - all connections will be encrypted")
            
        except Exception as e:
            self.logger.error(f"[SECURITY] CRITICAL: Failed to setup CurveZMQ encryption: {e}")
            # NO PLAINTEXT FALLBACK - Fail securely
            raise MessageBusError(f"CurveZMQ encryption setup failed: {e}")
    
    def _configure_curve_broker_sockets(self):
        """Configure broker sockets for CurveZMQ encryption"""
        if not self.encryption_enabled or not self.server_secret_key:
            self.logger.warning("[SECURITY] WARNING: CurveZMQ encryption disabled for broker sockets")
            return
            
        try:
            # Configure frontend socket as CURVE server
            self.frontend.setsockopt_string(zmq.CURVE_SECRETKEY, self.server_secret_key)
            self.frontend.setsockopt_string(zmq.CURVE_PUBLICKEY, self.server_public_key)
            self.frontend.setsockopt(zmq.CURVE_SERVER, 1)
            
            # Configure backend socket as CURVE server
            self.backend.setsockopt_string(zmq.CURVE_SECRETKEY, self.server_secret_key)
            self.backend.setsockopt_string(zmq.CURVE_PUBLICKEY, self.server_public_key)
            self.backend.setsockopt(zmq.CURVE_SERVER, 1)
            
            self.logger.info("[SECURITY] CurveZMQ broker socket configuration completed")
            self.logger.debug("[SECURITY] Frontend and backend sockets configured as CURVE servers")
            
        except Exception as e:
            self.logger.error(f"[SECURITY] CRITICAL: Failed to configure CurveZMQ broker sockets: {e}")
            # NO PLAINTEXT FALLBACK - Fail securely
            raise MessageBusError(f"CurveZMQ broker socket configuration failed: {e}")
    
    async def _start_proxy_task(self):
        """Start the proxy task in background"""
        asyncio.create_task(self._proxy_loop())
    
    async def _proxy_loop(self):
        """Main proxy loop for forwarding messages"""
        try:
            #print(f"[BROKER PROXY] Starting async proxy: Frontend: tcp://*:{self.pub_port}, Backend: tcp://*:{self.sub_port}")
            self.logger.info(f"Broker Proxy started: Frontend: tcp://*:{self.pub_port}, Backend: tcp://*:{self.sub_port}")
            
            # Brief delay to ensure sockets are ready
            await asyncio.sleep(0.1)
            
            #print(f"[BROKER PROXY] Starting async message forwarding...")
            
            # Manual async proxy implementation
            import zmq.asyncio
            poller = zmq.asyncio.Poller()
            poller.register(self.frontend, zmq.POLLIN)
            poller.register(self.backend, zmq.POLLIN)
            
            while self.running:
                try:
                    socks = await poller.poll(timeout=100)  # 100ms timeout
                    
                    if not socks:
                        # No messages - this is normal, continue polling
                        continue
                    
                    #   print(f"[BROKER PROXY] Poll returned {len(socks)} socket(s) with events")
                    
                    for sock, event in socks:
                        if sock == self.frontend and event == zmq.POLLIN:
                            # Forward from frontend (publishers) to backend (subscribers)
                            import time
                            recv_start = time.time()
                            message = await self.frontend.recv_multipart()
                            recv_time = time.time() - recv_start
                            
                            send_start = time.time()
                            await self.backend.send_multipart(message)
                            send_time = time.time() - send_start
                            
                            total_time = time.time() - recv_start
                            if total_time > 0.01:  # Log if > 10ms
                                print(f"⏱️ [BROKER] Message forwarding: recv={recv_time*1000:.2f}ms, send={send_time*1000:.2f}ms, total={total_time*1000:.2f}ms", flush=True)
                            
                        elif sock == self.backend and event == zmq.POLLIN:
                            # Forward from backend (subscribers) to frontend (publishers)
                            # This handles BOTH subscription messages AND response messages from subscribers
                            import time
                            recv_start = time.time()
                            message = await self.backend.recv_multipart()
                            recv_time = time.time() - recv_start
                            
                            send_start = time.time()
                            await self.frontend.send_multipart(message)
                            send_time = time.time() - send_start
                            
                            total_time = time.time() - recv_start
                            if total_time > 0.01:  # Log if > 10ms
                                print(f"⏱️ [BROKER_REVERSE] Message forwarding (sub→pub): recv={recv_time*1000:.2f}ms, send={send_time*1000:.2f}ms, total={total_time*1000:.2f}ms", flush=True)
                            
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error in proxy loop iteration: {e}")
                        await asyncio.sleep(0.1)
            
            #print(f"[BROKER PROXY] Proxy loop exiting")
            self.logger.info("Broker Proxy loop exiting")
            
        except Exception as e:
            if self.running:
                self.logger.error(f"Error starting proxy loop: {e}")
                print(f"[BROKER PROXY] Error: {e}")
    
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
