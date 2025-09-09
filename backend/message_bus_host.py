"""
Message Bus Host for AICO Backend

Runs the central message bus broker and provides integration with backend modules.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.any_pb2 import Any as ProtoAny

from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusBroker, MessageBusClient
from aico.core.logging import get_logger
from aico.core.topics import AICOTopics
from aico.proto.aico_core_api_gateway_pb2 import ApiEvent
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security.key_manager import AICOKeyManager
from aico.core.paths import AICOPaths

class AICOMessageBusHost:
    """Central message bus host for AICO backend"""
    
    def __init__(self, bind_address: str = "tcp://*:5555"):
        self.bind_address = bind_address
        self.logger = get_logger("backend", "message_bus_host")
        
        # Core components
        self.broker = MessageBusBroker(bind_address)
        self.internal_client = None
        
        # Database integration
        self.db_connection: Optional[EncryptedLibSQLConnection] = None
        
        # Module registry
        self.modules: Dict[str, MessageBusClient] = {}
        self.running = False
        
        # Shutdown coordination
        self.shutdown_initiated = False
        self.pending_messages = []
        self.shutdown_timeout = 3.0  # Max time to wait for message draining
    
    async def start(self, db_connection: Optional[EncryptedLibSQLConnection] = None):
        """Start the message bus host"""
        try:
            # Start the broker
            await self.broker.start()
            
            # Create internal client for system messages
            self.internal_client = MessageBusClient("system.message_bus_host")
            await self.internal_client.connect()
            
            # Enable persistence if database provided
            if db_connection:
                self.db_connection = db_connection
                persistence_handler = self._create_persistence_handler(db_connection)
                self.internal_client.enable_persistence(persistence_handler)
                self.logger.info("Message persistence enabled")
            
            # Set up system topic permissions
            self._setup_system_permissions()
            
            self.running = True
            self.logger.info(f"Message bus host started on {self.bind_address}")
            
            # Publish system startup event with proper protobuf message
            startup_event = ApiEvent()
            startup_event.event_id = str(uuid.uuid4())
            startup_event.event_type = AICOTopics.SYSTEM_BUS_STARTED
            startup_event.client_id = "system.message_bus_host"
            startup_event.session_id = "system"
            
            # Set timestamp
            now = datetime.utcnow()
            startup_event.timestamp.seconds = int(now.timestamp())
            startup_event.timestamp.nanos = int((now.timestamp() % 1) * 1e9)
            
            # Set metadata
            startup_event.metadata["broker_address"] = self.bind_address
            startup_event.metadata["status"] = "started"
            
            await self.internal_client.publish(
                AICOTopics.SYSTEM_BUS_STARTED,
                startup_event
            )
            
            self.logger.info("Message bus host started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start message bus host: {e}")
            raise
    
    async def stop(self):
        """Stop the message bus host with graceful message draining"""
        if not self.running:
            return
        
        try:
            # PHASE 1: Signal shutdown but keep persistence active
            self.shutdown_initiated = True
            
            # Publish system shutdown event
            if self.internal_client:
                shutdown_event = ApiEvent()
                shutdown_event.event_id = str(uuid.uuid4())
                shutdown_event.event_type = AICOTopics.SYSTEM_BUS_STOPPING
                shutdown_event.client_id = "system.message_bus_host"
                shutdown_event.session_id = "system"
                
                # Set timestamp
                now = datetime.utcnow()
                shutdown_event.timestamp.seconds = int(now.timestamp())
                shutdown_event.timestamp.nanos = int((now.timestamp() % 1) * 1e9)
                
                # Set metadata
                shutdown_event.metadata["reason"] = "shutdown"
                shutdown_event.metadata["status"] = "stopping"
                
                await self.internal_client.publish(
                    AICOTopics.SYSTEM_BUS_STOPPING,
                    shutdown_event
                )
            
            # PHASE 2: Drain pending messages with timeout
            await self._drain_pending_messages()
            
            # PHASE 3: Now safe to stop persistence and continue shutdown
            self.running = False
            self.logger.info("Message bus host stopping")
            
            # Stop all module clients
            for module_name, client in self.modules.items():
                try:
                    await client.disconnect()
                    self.logger.info(f"Disconnected module: {module_name}")
                except Exception as e:
                    self.logger.error(f"Error disconnecting module {module_name}: {e}")
            
            # Stop internal client
            if self.internal_client:
                await self.internal_client.disconnect()
            
            # Stop broker
            await self.broker.stop()
            
            self.logger.info("Message bus host stopped")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def register_module(self, module_name: str, topic_permissions: List[str] = None) -> MessageBusClient:
        """Register a backend module with the message bus"""
        if module_name in self.modules:
            self.logger.warning(f"Module {module_name} already registered")
            return self.modules[module_name]
        
        try:
            # Create client for the module
            client = MessageBusClient(f"backend.{module_name}")
            await client.connect()
            
            # Enable persistence if available
            if self.db_connection:
                persistence_handler = self._create_persistence_handler(self.db_connection)
                client.enable_persistence(persistence_handler)
            
            # Set up topic permissions
            if topic_permissions:
                for topic in topic_permissions:
                    self.broker.add_topic_permission(f"backend.{module_name}", topic)
            
            self.modules[module_name] = client
            self.logger.info(f"Registered module: {module_name}")
            
            # Publish module registration event
            registration_event = ApiEvent()
            registration_event.event_id = str(uuid.uuid4())
            registration_event.event_type = AICOTopics.SYSTEM_MODULE_REGISTERED
            registration_event.client_id = f"backend.{module_name}"
            registration_event.session_id = "system"
            
            # Set timestamp
            now = datetime.utcnow()
            registration_event.timestamp.seconds = int(now.timestamp())
            registration_event.timestamp.nanos = int((now.timestamp() % 1) * 1e9)
            
            # Set metadata
            registration_event.metadata["module_name"] = module_name
            registration_event.metadata["permissions"] = ",".join(topic_permissions or [])
            registration_event.metadata["status"] = "registered"
            
            await self.internal_client.publish(
                AICOTopics.SYSTEM_MODULE_REGISTERED,
                registration_event
            )
            
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to register module {module_name}: {e}")
            raise
    
    async def unregister_module(self, module_name: str):
        """Unregister a backend module"""
        if module_name not in self.modules:
            self.logger.warning(f"Module {module_name} not registered")
            return
        
        try:
            client = self.modules[module_name]
            await client.disconnect()
            del self.modules[module_name]
            
            self.logger.info(f"Unregistered module: {module_name}")
            
            # Module unregistration logged above - no need for message bus event
            
        except Exception as e:
            self.logger.error(f"Error unregistering module {module_name}: {e}")
    
    def _setup_system_permissions(self):
        """Set up default topic permissions for system components"""
        # System components get access to all topics
        system_topics = ["*"]
        
        # API Gateway permissions
        api_gateway_topics = [
            AICOTopics.ALL_CONVERSATION,
            AICOTopics.ALL_EMOTION,
            AICOTopics.ALL_PERSONALITY,
            "system/status/*",
            "admin/*"
        ]
        
        for topic in system_topics:
            self.broker.add_topic_permission("system.message_bus_host", topic)
        
        for topic in api_gateway_topics:
            self.broker.add_topic_permission("backend.api_gateway", topic)
    
    async def get_message_stats(self) -> Dict[str, any]:
        """Get message bus statistics"""
        if not self.db_connection:
            return {"persistence_enabled": False}
        
        try:
            # Query message statistics from database
            cursor = await self.db_connection.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT topic) as unique_topics,
                    COUNT(DISTINCT source) as unique_sources,
                    MIN(timestamp) as earliest_message,
                    MAX(timestamp) as latest_message
                FROM events
            """)
            
            row = await cursor.fetchone()
            
            return {
                "persistence_enabled": True,
                "total_messages": row[0] if row else 0,
                "unique_topics": row[1] if row else 0,
                "unique_sources": row[2] if row else 0,
                "earliest_message": row[3] if row else None,
                "latest_message": row[4] if row else None,
                "registered_modules": list(self.modules.keys()),
                "broker_address": self.bind_address
            }
            
        except Exception as e:
            self.logger.error(f"Error getting message stats: {e}")
            return {"error": str(e)}
    
    def _create_persistence_handler(self, db_connection):
        """Create a persistence handler function for the given database connection"""
        import json
        from google.protobuf.message import Message as ProtobufMessage
        
        async def persist_message(message):
            """Persist a message to the database"""
            # During shutdown, queue messages for draining instead of skipping
            if self.shutdown_initiated and not self.running:
                return  # Shutdown complete, no more persistence
            elif self.shutdown_initiated:
                # Queue message for draining phase
                self.pending_messages.append(message)
                return
                
            try:
                # Handle AicoMessage protobuf structure
                if hasattr(message, 'any_payload'):
                    # This is an AicoMessage protobuf
                    payload = message.any_payload
                elif hasattr(message, 'payload'):
                    payload = message.payload
                else:
                    payload = message
                
                # Serialize payload for storage
                if isinstance(payload, ProtobufMessage):
                    payload_data = payload.SerializeToString()
                elif isinstance(payload, bytes):
                    payload_data = payload
                elif payload is None:
                    payload_data = b''
                else:
                    try:
                        payload_data = json.dumps(payload).encode('utf-8')
                    except (TypeError, ValueError):
                        payload_data = str(payload).encode('utf-8')
                
                # Handle protobuf timestamp conversion
                from datetime import datetime
                if hasattr(message.metadata.timestamp, 'ToDatetime'):
                    timestamp = message.metadata.timestamp.ToDatetime().isoformat()
                else:
                    timestamp = datetime.utcnow().isoformat()
                
                # Extract actual protobuf fields (based on aico_core_envelope.proto)
                message_id = message.metadata.message_id
                source = message.metadata.source  
                message_type = message.metadata.message_type
                version = message.metadata.version
                
                # Convert attributes map to dict for JSON storage
                attributes_dict = dict(message.metadata.attributes) if message.metadata.attributes else {}
                metadata_json = json.dumps({
                    'version': version,
                    'attributes': attributes_dict
                })
                
                # Insert message into database (using actual protobuf fields)
                db_connection.execute("""
                    INSERT INTO events (
                        timestamp, topic, source, message_type, message_id,
                        priority, correlation_id, payload, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    message_type,  # topic field
                    source,
                    message_type,
                    message_id,
                    0,  # priority - not in protobuf, use default
                    '',  # correlation_id - not in protobuf, use empty
                    payload_data,
                    metadata_json
                ))
                
            except Exception as e:
                self.logger.error(f"Failed to persist message {message.metadata.message_id}: {e}")
        
        return persist_message
    
    async def _drain_pending_messages(self):
        """Drain all pending messages with timeout to ensure zero loss"""
        if not self.pending_messages:
            return
        
        self.logger.info(f"Draining {len(self.pending_messages)} pending messages...")
        
        try:
            # Process all pending messages with timeout
            await asyncio.wait_for(
                self._process_pending_messages(),
                timeout=self.shutdown_timeout
            )
            self.logger.info("All pending messages processed successfully")
        except asyncio.TimeoutError:
            self.logger.warning(f"Message draining timed out after {self.shutdown_timeout}s, "
                              f"{len(self.pending_messages)} messages may be lost")
        except Exception as e:
            self.logger.error(f"Error during message draining: {e}")
    
    async def _process_pending_messages(self):
        """Process all messages in the pending queue"""
        import json
        from google.protobuf.message import Message as ProtobufMessage
        
        for message in self.pending_messages:
            try:
                # Debug: Check message structure
                # self.logger.info(f"Processing pending message: {type(message)}")
                # self.logger.info(f"Message attributes: {dir(message)}")
                
                # Handle different message structures - AicoMessage protobuf
                if hasattr(message, 'any_payload'):
                    # This is an AicoMessage protobuf with any_payload field
                    payload = message.any_payload
                elif hasattr(message, 'payload'):
                    payload = message.payload
                else:
                    payload = message  # Message might be the payload itself
                
                # Serialize payload for storage
                if isinstance(payload, ProtobufMessage):
                    payload_data = payload.SerializeToString()
                elif isinstance(payload, bytes):
                    payload_data = payload
                elif payload is None:
                    payload_data = b''
                else:
                    try:
                        payload_data = json.dumps(payload).encode('utf-8')
                    except (TypeError, ValueError):
                        # Fallback: convert to string
                        payload_data = str(payload).encode('utf-8')
                
                # Handle metadata safely
                if hasattr(message, 'metadata') and message.metadata:
                    metadata = message.metadata
                    metadata_json = json.dumps({
                        'attributes': getattr(metadata, 'attributes', {}) or {},
                        'version': getattr(metadata, 'version', '1.0')
                    })
                    
                    # Extract metadata fields safely
                    timestamp = getattr(metadata, 'timestamp', None)
                    if timestamp and hasattr(timestamp, 'isoformat'):
                        timestamp_str = timestamp.isoformat()
                    else:
                        from datetime import datetime
                        timestamp_str = datetime.utcnow().isoformat()
                    
                    message_type = getattr(metadata, 'message_type', 'unknown')
                    source = getattr(metadata, 'source', 'unknown')
                    message_id = getattr(metadata, 'message_id', str(uuid.uuid4()))
                    priority = getattr(metadata, 'priority', None)
                    priority_value = priority.value if priority and hasattr(priority, 'value') else 1
                    correlation_id = getattr(metadata, 'correlation_id', None)
                else:
                    # Fallback metadata
                    from datetime import datetime
                    timestamp_str = datetime.utcnow().isoformat()
                    message_type = 'shutdown_event'
                    source = 'message_bus_host'
                    message_id = str(uuid.uuid4())
                    priority_value = 1
                    correlation_id = None
                    metadata_json = json.dumps({'attributes': {}, 'version': '1.0'})
                
                # Insert message into database synchronously for reliability
                self.db_connection.execute("""
                    INSERT INTO events (
                        timestamp, topic, source, message_type, message_id,
                        priority, correlation_id, payload, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_str,
                    message_type,
                    source,
                    message_type,
                    message_id,
                    priority_value,
                    correlation_id,
                    payload_data,
                    metadata_json
                ))
                
                # Commit immediately for each message during shutdown
                self.db_connection.commit()
                
            except Exception as e:
                # Use safe message ID extraction for error logging
                msg_id = getattr(getattr(message, 'metadata', None), 'message_id', 'unknown')
                self.logger.error(f"Failed to persist pending message {msg_id}: {e}")
                import traceback
                self.logger.error(f"Full error traceback: {traceback.format_exc()}")
        
        # Clear the pending messages queue
        self.pending_messages.clear()


# Example usage and integration patterns

async def example_emotion_module(bus_host: AICOMessageBusHost):
    """Example of how an emotion module would integrate with the message bus"""
    
    # Register the module with appropriate permissions
    client = await bus_host.register_module("emotion_simulation", [
        AICOTopics.ALL_EMOTION,
        AICOTopics.CONVERSATION_CONTEXT_CURRENT
    ])
    
    # Subscribe to relevant topics
    async def handle_conversation_event(message):
        # Process conversation event and update emotional state
        print(f"Emotion module received: {message.metadata.message_type}")
        
        # Publish emotional state update
        await client.publish(
            AICOTopics.EMOTION_STATE_CURRENT,
            {
                "valence": 0.7,
                "arousal": 0.5,
                "dominance": 0.6,
                "primary_emotion": "contentment"
            },
            
        )
    
    await client.subscribe(AICOTopics.ALL_CONVERSATION, handle_conversation_event)
    
    return client


async def example_personality_module(bus_host: AICOMessageBusHost):
    """Example of how a personality module would integrate"""
    
    client = await bus_host.register_module("personality_simulation", [
        AICOTopics.ALL_PERSONALITY,
        "emotion/state/*",
        AICOTopics.CONVERSATION_CONTEXT_CURRENT
    ])
    
    # Subscribe to emotional state changes
    async def handle_emotion_update(message):
        print(f"Personality module received: {message.metadata.message_type}")
        
        # Publish personality expression parameters
        await client.publish(
            AICOTopics.PERSONALITY_EXPRESSION_COMMUNICATION,
            {
                "warmth": 0.8,
                "formality": 0.3,
                "curiosity": 0.9
            }
        )
    
    await client.subscribe("emotion/state/*", handle_emotion_update)
    
    return client


# Main function for testing
async def main():
    """Example of setting up the message bus host with modules"""
    
    # Initialize message bus host
    bus_host = AICOMessageBusHost()
    
    try:
        # Start the message bus (without database for this example)
        await bus_host.start()
        
        # Register example modules (disabled for log pipeline test)
        # emotion_client = await example_emotion_module(bus_host)
        # personality_client = await example_personality_module(bus_host)
        # Simulate some message traffic
        # await emotion_client.publish(
        #     "conversation.user_input",
        #     {"text": "Hello AICO!", "timestamp": "now"},
        # )
        # Let messages flow for a bit
        # await asyncio.sleep(2)
        
        # Get statistics
        stats = await bus_host.get_message_stats()
        print(f"Message bus stats: {stats}")
        
    finally:
        # Clean shutdown
        await bus_host.stop()


if __name__ == "__main__":
    asyncio.run(main())
