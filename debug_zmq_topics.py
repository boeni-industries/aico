#!/usr/bin/env python3
"""
Debug ZMQ topic routing between log transport and log consumer
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.core.config import ConfigurationManager
from shared.aico.core.logging import initialize_logging, get_logger
from shared.aico.core.bus import MessageBusClient

async def debug_zmq_topics():
    """Debug ZMQ topic routing and message flow"""
    
    print("=== Debugging ZMQ Topic Routing ===")
    
    try:
        # Initialize configuration and logging
        config_manager = ConfigurationManager()
        initialize_logging(config_manager)
        
        # Create two clients - one to send, one to receive
        print("1. Creating ZMQ clients...")
        sender_client = MessageBusClient("debug_sender")
        receiver_client = MessageBusClient("debug_receiver")
        
        # Connect both clients
        await sender_client.connect()
        await receiver_client.connect()
        
        if not sender_client.connected or not receiver_client.connected:
            print("   ❌ Failed to connect clients")
            return
        
        print("   ✅ Both clients connected")
        
        # Set up message capture
        received_messages = []
        
        def capture_message(message):
            received_messages.append(message)
            print(f"   📨 Received message: {type(message)} on topic")
        
        # Subscribe to logs/ topic (same as log consumer)
        print("2. Subscribing to logs/ topic...")
        await receiver_client.subscribe("logs/", capture_message)
        
        # Wait a moment for subscription to be active
        await asyncio.sleep(1)
        
        # Get a logger and send test messages
        print("3. Sending test log messages...")
        logger = get_logger('debug', 'topic_test')
        
        # Send multiple test messages
        logger.info("Debug message 1 - testing topic routing")
        logger.warning("Debug message 2 - testing topic routing")
        logger.error("Debug message 3 - testing topic routing")
        
        print("   ✅ Test messages sent via logger")
        
        # Wait for messages to be processed
        print("4. Waiting for message reception...")
        await asyncio.sleep(3)
        
        print(f"5. Messages received by debug client: {len(received_messages)}")
        
        if received_messages:
            print("   ✅ Messages are flowing through ZMQ broker")
            for i, msg in enumerate(received_messages):
                print(f"     Message {i+1}: {type(msg)}")
        else:
            print("   ❌ No messages received - ZMQ transport may not be sending")
            
            # Check if ZMQ transport is actually initialized
            print("6. Checking ZMQ transport status...")
            from shared.aico.core.logging import _get_zmq_transport
            
            zmq_transport = _get_zmq_transport()
            if zmq_transport:
                print(f"   ZMQ transport found: {type(zmq_transport)}")
                print(f"   Transport initialized: {getattr(zmq_transport, '_initialized', 'unknown')}")
                print(f"   Broker available: {getattr(zmq_transport, '_broker_available', 'unknown')}")
                if hasattr(zmq_transport, '_message_bus_client'):
                    client = zmq_transport._message_bus_client
                    print(f"   Transport client connected: {getattr(client, 'connected', 'unknown') if client else 'No client'}")
            else:
                print("   ❌ No ZMQ transport found")
        
        # Cleanup
        await sender_client.disconnect()
        await receiver_client.disconnect()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_zmq_topics())
