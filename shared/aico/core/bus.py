"""
Core Message Bus Implementation for AICO

Provides a hybrid broker pattern with ZeroMQ for internal communication
and protocol adapters for external subsystems.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, asdict

import zmq
import zmq.asyncio
from google.protobuf.message import Message as ProtobufMessage
from google.protobuf.any_pb2 import Any as ProtobufAny
from google.protobuf.timestamp_pb2 import Timestamp

from aico.core.logging import get_logger


class TransportType(Enum):
    """Message bus transport types"""
    INPROC = "inproc"      # Same process
    IPC = "ipc"            # Inter-process communication
    TCP = "tcp"            # Network communication


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class MessageMetadata:
    """Message metadata structure"""
    message_id: str
    timestamp: datetime
    source: str
    message_type: str
    version: str
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None


@dataclass
class AICOMessage:
    """AICO message envelope"""
    metadata: MessageMetadata
    payload: Union[Dict[str, Any], ProtobufMessage, bytes]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization"""
        return {
            'metadata': {
                'message_id': self.metadata.message_id,
                'timestamp': self.metadata.timestamp.isoformat(),
                'source': self.metadata.source,
                'message_type': self.metadata.message_type,
                'version': self.metadata.version,
                'priority': self.metadata.priority.value,
                'correlation_id': self.metadata.correlation_id,
                'attributes': self.metadata.attributes or {}
            },
            'payload': self._serialize_payload()
        }
    
    def _serialize_payload(self) -> Any:
        """Serialize payload based on type"""
        if isinstance(self.payload, ProtobufMessage):
            return self.payload.SerializeToString().hex()
        elif isinstance(self.payload, bytes):
            return self.payload.hex()
        else:
            return self.payload


class MessageBusError(Exception):
    """Base exception for message bus errors"""
    pass


class TopicAccessError(MessageBusError):
    """Raised when access to a topic is denied"""
    pass


class MessageBusClient:
    """Client interface for connecting to the message bus"""
    
    def __init__(self, client_id: str, broker_address: str = "tcp://localhost:5555"):
        self.client_id = client_id
        self.broker_address = broker_address
        self.logger = get_logger(f"bus.client.{client_id}")
        
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
            # Publisher socket for sending messages
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.connect(f"{self.broker_address}/pub")
            
            # Subscriber socket for receiving messages
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(f"{self.broker_address}/sub")
            
            self.running = True
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
    
    async def publish(self, topic: str, payload: Any, priority: MessagePriority = MessagePriority.NORMAL,
                     correlation_id: Optional[str] = None, attributes: Optional[Dict[str, str]] = None):
        """Publish a message to a topic"""
        if not self.running:
            raise MessageBusError("Client not connected")
        
        # Create message metadata
        metadata = MessageMetadata(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source=self.client_id,
            message_type=topic,
            version="1.0",
            priority=priority,
            correlation_id=correlation_id,
            attributes=attributes
        )
        
        # Create AICO message
        message = AICOMessage(metadata=metadata, payload=payload)
        
        # Serialize message
        message_data = json.dumps(message.to_dict()).encode('utf-8')
        
        # Send message with topic as routing key
        await self.publisher.send_multipart([topic.encode('utf-8'), message_data])
        
        self.logger.debug(f"Published message to topic '{topic}': {metadata.message_id}")
        
        # Persist message if enabled
        if self.persistence_enabled:
            await self._persist_message(message)
    
    async def subscribe(self, topic_pattern: str, callback: Callable[[AICOMessage], None]):
        """Subscribe to messages matching a topic pattern"""
        if not self.running:
            raise MessageBusError("Client not connected")
        
        # Add subscription
        self.subscriptions[topic_pattern] = callback
        
        # Subscribe to topic pattern
        self.subscriber.setsockopt(zmq.SUBSCRIBE, topic_pattern.encode('utf-8'))
        
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
                
                # Deserialize message
                message_dict = json.loads(message_data.decode('utf-8'))
                message = self._deserialize_message(message_dict)
                
                # Find matching subscriptions
                for pattern, callback in self.subscriptions.items():
                    if self._topic_matches_pattern(topic, pattern):
                        try:
                            await self._invoke_callback(callback, message)
                        except Exception as e:
                            self.logger.error(f"Error in callback for topic '{topic}': {e}")
                
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    self.logger.error(f"Error in message loop: {e}")
                    await asyncio.sleep(0.1)  # Brief pause before retrying
    
    def _deserialize_message(self, message_dict: Dict[str, Any]) -> AICOMessage:
        """Deserialize message from dictionary"""
        metadata_dict = message_dict['metadata']
        metadata = MessageMetadata(
            message_id=metadata_dict['message_id'],
            timestamp=datetime.fromisoformat(metadata_dict['timestamp']),
            source=metadata_dict['source'],
            message_type=metadata_dict['message_type'],
            version=metadata_dict['version'],
            priority=MessagePriority(metadata_dict['priority']),
            correlation_id=metadata_dict.get('correlation_id'),
            attributes=metadata_dict.get('attributes')
        )
        
        return AICOMessage(metadata=metadata, payload=message_dict['payload'])
    
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
    
    async def _invoke_callback(self, callback: Callable, message: AICOMessage):
        """Invoke callback, handling both sync and async functions"""
        if asyncio.iscoroutinefunction(callback):
            await callback(message)
        else:
            callback(message)
    
    async def _persist_message(self, message: AICOMessage):
        """Persist message using the provided handler (if persistence enabled)"""
        if not self.message_log:
            return
        
        try:
            # Call the persistence handler function
            await self.message_log(message)
            
        except Exception as e:
            self.logger.error(f"Failed to persist message {message.metadata.message_id}: {e}")
    
    def enable_persistence(self, persistence_handler: Callable):
        """Enable message persistence with a handler function
        
        Args:
            persistence_handler: Async function that takes (message: AICOMessage) -> None
        """
        self.persistence_enabled = True
        self.message_log = persistence_handler
        self.logger.info("Message persistence enabled")


class MessageBusBroker:
    """Central message bus broker running in the backend service"""
    
    def __init__(self, bind_address: str = "tcp://*:5555"):
        self.bind_address = bind_address
        self.logger = get_logger("bus.broker")
        
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
            self.frontend.bind(f"{self.bind_address}/pub")
            
            # Backend socket for subscribers
            self.backend = self.context.socket(zmq.XPUB)
            self.backend.bind(f"{self.bind_address}/sub")
            
            self.running = True
            self.logger.info(f"Message bus broker started on {self.bind_address}")
            
            # Start proxy loop
            asyncio.create_task(self._proxy_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to start message bus broker: {e}")
            raise MessageBusError(f"Broker startup failed: {e}")
    
    async def stop(self):
        """Stop the message bus broker"""
        self.running = False
        
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        
        self.context.term()
        self.logger.info("Message bus broker stopped")
    
    async def _proxy_loop(self):
        """Main proxy loop for forwarding messages"""
        try:
            # Use ZeroMQ proxy for efficient message forwarding
            zmq.proxy(self.frontend, self.backend)
        except Exception as e:
            if self.running:
                self.logger.error(f"Error in proxy loop: {e}")
    
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


async def publish_message(client: MessageBusClient, topic: str, payload: Any, 
                         priority: MessagePriority = MessagePriority.NORMAL):
    """Convenience function to publish a message"""
    await client.publish(topic, payload, priority)


def create_broker(bind_address: str = "tcp://*:5555") -> MessageBusBroker:
    """Create a message bus broker"""
    return MessageBusBroker(bind_address)
