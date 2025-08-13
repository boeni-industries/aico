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
from aico.core.logging import initialize_logging
initialize_logging(ConfigurationManager())

from aico.core.bus import MessageBusBroker, MessageBusClient
from aico.core.logging import get_logger
from aico.proto.core import ApiEvent
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
            startup_event.event_type = "system.bus.started"
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
                "system.bus.started",
                startup_event
            )
            
            self.logger.info("Message bus host started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start message bus host: {e}")
            raise
    
    async def stop(self):
        """Stop the message bus host"""
        if not self.running:
            return
        
        self.running = False
        
        try:
            # Publish system shutdown event
            # Publish system shutdown event with proper protobuf message
            if self.internal_client:
                shutdown_event = ApiEvent()
                shutdown_event.event_id = str(uuid.uuid4())
                shutdown_event.event_type = "system.bus.stopping"
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
                    "system.bus.stopping",
                    shutdown_event
                )
            
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
            
            # Publish module registration event (must be protobuf, not dict)
            # await self.internal_client.publish(
            #     "system.module.registered",
            #     {
            #         "module_name": module_name,
            #         "client_id": f"backend.{module_name}",
            #         "permissions": topic_permissions or []
            #     },
            # )
            
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
            
            # Publish module unregistration event
            await self.internal_client.publish(
                "system.module.unregistered",
                {"module_name": module_name},
                
            )
            
        except Exception as e:
            self.logger.error(f"Error unregistering module {module_name}: {e}")
    
    def _setup_system_permissions(self):
        """Set up default topic permissions for system components"""
        # System components get access to all topics
        system_topics = ["*"]
        
        # API Gateway permissions
        api_gateway_topics = [
            "conversation.*",
            "emotion.*", 
            "personality.*",
            "system.status.*",
            "admin.*"
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
            try:
                # Serialize payload for storage
                if isinstance(message.payload, ProtobufMessage):
                    payload_data = message.payload.SerializeToString()
                elif isinstance(message.payload, bytes):
                    payload_data = message.payload
                else:
                    payload_data = json.dumps(message.payload).encode('utf-8')
                
                # Prepare metadata as JSON
                metadata_json = json.dumps({
                    'attributes': message.metadata.attributes or {},
                    'version': message.metadata.version
                })
                
                # Insert message into database
                await db_connection.execute("""
                    INSERT INTO events (
                        timestamp, topic, source, message_type, message_id,
                        priority, correlation_id, payload, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.metadata.timestamp.isoformat(),
                    message.metadata.message_type,
                    message.metadata.source,
                    message.metadata.message_type,
                    message.metadata.message_id,
                    message.metadata.priority.value,
                    message.metadata.correlation_id,
                    payload_data,
                    metadata_json
                ))
                
            except Exception as e:
                self.logger.error(f"Failed to persist message {message.metadata.message_id}: {e}")
        
        return persist_message


# Example usage and integration patterns

async def example_emotion_module(bus_host: AICOMessageBusHost):
    """Example of how an emotion module would integrate with the message bus"""
    
    # Register the module with appropriate permissions
    client = await bus_host.register_module("emotion_simulation", [
        "emotion.*",
        "personality.expression.*",
        "conversation.context"
    ])
    
    # Subscribe to relevant topics
    async def handle_conversation_event(message):
        # Process conversation event and update emotional state
        print(f"Emotion module received: {message.metadata.message_type}")
        
        # Publish emotional state update
        await client.publish(
            "emotion.state.current",
            {
                "valence": 0.7,
                "arousal": 0.5,
                "dominance": 0.6,
                "primary_emotion": "contentment"
            },
            
        )
    
    await client.subscribe("conversation.*", handle_conversation_event)
    
    return client


async def example_personality_module(bus_host: AICOMessageBusHost):
    """Example of how a personality module would integrate"""
    
    client = await bus_host.register_module("personality_simulation", [
        "personality.*",
        "emotion.state.*",
        "conversation.context"
    ])
    
    # Subscribe to emotional state changes
    async def handle_emotion_update(message):
        print(f"Personality module received: {message.metadata.message_type}")
        
        # Publish personality expression parameters
        await client.publish(
            "personality.expression.communication",
            {
                "warmth": 0.8,
                "formality": 0.3,
                "curiosity": 0.9
            }
        )
    
    await client.subscribe("emotion.state.*", handle_emotion_update)
    
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
