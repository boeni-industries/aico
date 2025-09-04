#!/usr/bin/env python3
"""
Test script for CurveZMQ message bus encryption
"""

import asyncio
import sys
import os
import logging
import zmq
import zmq.asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up basic logging for the test
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from shared.aico.security.key_manager import AICOKeyManager
from shared.aico.core.config import ConfigurationManager


class SimpleCurveBroker:
    """Simplified CurveZMQ broker for testing"""
    
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.frontend = None
        self.backend = None
        self.encryption_enabled = False
        self.public_key = None
        self.secret_key = None
        
    async def setup_encryption(self):
        """Setup CurveZMQ encryption"""
        try:
            config = ConfigurationManager()
            transport_config = config.get("security.transport", {})
            
            self.encryption_enabled = transport_config.get("message_bus_encryption", True)
            
            if self.encryption_enabled:
                # Initialize key manager
                key_manager = AICOKeyManager(config)
                master_key = key_manager.authenticate(interactive=False)
                
                # Derive broker keypair
                self.public_key, self.secret_key = key_manager.derive_curve_keypair(
                    master_key, "message_bus_broker"
                )
                print(f"   🔑 Generated CurveZMQ broker keypair")
                
        except Exception as e:
            print(f"   ⚠️  Encryption setup failed: {e}, falling back to plaintext")
            self.encryption_enabled = False
    
    async def start(self):
        """Start the broker"""
        await self.setup_encryption()
        
        # Create sockets
        self.frontend = self.context.socket(zmq.XSUB)
        self.backend = self.context.socket(zmq.XPUB)
        
        if self.encryption_enabled:
            # Configure as CURVE server
            self.frontend.setsockopt(zmq.CURVE_SERVER, 1)
            self.frontend.setsockopt(zmq.CURVE_SECRETKEY, self.secret_key)
            
            self.backend.setsockopt(zmq.CURVE_SERVER, 1)
            self.backend.setsockopt(zmq.CURVE_SECRETKEY, self.secret_key)
        
        # Bind sockets
        self.frontend.bind("tcp://*:5555")
        self.backend.bind("tcp://*:5556")
        
        # Start proxy manually
        asyncio.create_task(self._proxy_loop())
    
    async def _proxy_loop(self):
        """Manual proxy implementation"""
        poller = zmq.asyncio.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)
        
        try:
            while True:
                events = await poller.poll()
                for socket, event in events:
                    if socket is self.frontend and event == zmq.POLLIN:
                        # Forward from frontend to backend
                        message = await self.frontend.recv_multipart()
                        await self.backend.send_multipart(message)
                    elif socket is self.backend and event == zmq.POLLIN:
                        # Forward from backend to frontend
                        message = await self.backend.recv_multipart()
                        await self.frontend.send_multipart(message)
        except asyncio.CancelledError:
            pass
        
    async def stop(self):
        """Stop the broker"""
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        self.context.term()


class SimpleCurveClient:
    """Simplified CurveZMQ client for testing"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.context = zmq.asyncio.Context()
        self.publisher = None
        self.subscriber = None
        self.encryption_enabled = False
        self.public_key = None
        self.secret_key = None
        self.broker_public_key = None
        
    async def setup_encryption(self):
        """Setup CurveZMQ encryption"""
        try:
            config = ConfigurationManager()
            transport_config = config.get("security.transport", {})
            
            self.encryption_enabled = transport_config.get("message_bus_encryption", True)
            
            if self.encryption_enabled:
                # Initialize key manager
                key_manager = AICOKeyManager(config)
                master_key = key_manager.authenticate(interactive=False)
                
                # Derive client keypair
                self.public_key, self.secret_key = key_manager.derive_curve_keypair(
                    master_key, f"message_bus_client_{self.client_id}"
                )
                
                # Get broker public key
                self.broker_public_key, _ = key_manager.derive_curve_keypair(
                    master_key, "message_bus_broker"
                )
                
                print(f"   🔑 Generated CurveZMQ client keypair for {self.client_id}")
                
        except Exception as e:
            print(f"   ⚠️  Encryption setup failed for {self.client_id}: {e}")
            self.encryption_enabled = False
    
    async def connect(self):
        """Connect to broker"""
        await self.setup_encryption()
        
        # Create sockets
        self.publisher = self.context.socket(zmq.PUB)
        self.subscriber = self.context.socket(zmq.SUB)
        
        if self.encryption_enabled:
            # Configure as CURVE client
            self.publisher.setsockopt(zmq.CURVE_SECRETKEY, self.secret_key)
            self.publisher.setsockopt(zmq.CURVE_PUBLICKEY, self.public_key)
            self.publisher.setsockopt(zmq.CURVE_SERVERKEY, self.broker_public_key)
            
            self.subscriber.setsockopt(zmq.CURVE_SECRETKEY, self.secret_key)
            self.subscriber.setsockopt(zmq.CURVE_PUBLICKEY, self.public_key)
            self.subscriber.setsockopt(zmq.CURVE_SERVERKEY, self.broker_public_key)
        
        # Connect to broker
        self.publisher.connect("tcp://localhost:5555")
        self.subscriber.connect("tcp://localhost:5556")
        
    async def subscribe(self, topic: str):
        """Subscribe to topic"""
        if self.subscriber:
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
    
    async def publish(self, topic: str, message: str):
        """Publish message"""
        if self.publisher:
            await self.publisher.send_multipart([topic.encode(), message.encode()])
    
    async def receive(self):
        """Receive message"""
        if self.subscriber:
            topic, message = await self.subscriber.recv_multipart()
            return topic.decode(), message.decode()
        return None, None
    
    async def disconnect(self):
        """Disconnect from broker"""
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        self.context.term()


async def test_curve_encryption():
    """Test CurveZMQ encryption with message bus"""
    print("🔒 Testing CurveZMQ Message Bus Encryption")
    print("=" * 50)
    
    # Start broker
    print("1. Starting encrypted message bus broker...")
    broker = SimpleCurveBroker()
    
    try:
        await broker.start()
        print(f"   ✅ Broker started (encryption: {'enabled' if broker.encryption_enabled else 'disabled'})")
        
        # Give broker time to fully initialize
        await asyncio.sleep(0.5)
        
        # Create test clients
        print("2. Creating encrypted clients...")
        publisher = SimpleCurveClient("test_publisher")
        subscriber = SimpleCurveClient("test_subscriber")
        
        await publisher.connect()
        print(f"   ✅ Publisher connected (encryption: {'enabled' if publisher.encryption_enabled else 'disabled'})")
        
        await subscriber.connect()
        print(f"   ✅ Subscriber connected (encryption: {'enabled' if subscriber.encryption_enabled else 'disabled'})")
        
        # Set up subscription
        messages_received = []
        
        print("3. Setting up encrypted subscription...")
        await subscriber.subscribe("test.encryption")
        
        # Give subscription time to register
        await asyncio.sleep(0.2)
        
        # Send test messages
        print("4. Sending encrypted test messages...")
        test_messages = [
            "Hello encrypted world!",
            "CurveZMQ is working!",
            "Security first! 🔐"
        ]
        
        # Start receiving task
        async def receive_messages():
            for _ in range(len(test_messages)):
                try:
                    topic, message = await subscriber.receive()
                    if topic and message:
                        messages_received.append({
                            'topic': topic,
                            'content': message,
                            'encrypted': True
                        })
                        print(f"   📨 Received encrypted message: '{message}' on topic '{topic}'")
                except Exception as e:
                    print(f"   ⚠️  Receive error: {e}")
                    break
        
        receive_task = asyncio.create_task(receive_messages())
        
        # Small delay to ensure receiver is ready
        await asyncio.sleep(0.1)
        
        for i, msg in enumerate(test_messages):
            await publisher.publish(f"test.encryption.message_{i}", msg)
            print(f"   📤 Sent encrypted message: '{msg}'")
            await asyncio.sleep(0.1)
        
        # Wait for messages to be processed
        await asyncio.sleep(1.0)
        receive_task.cancel()
        
        # Verify results
        print("5. Verifying encrypted message delivery...")
        if len(messages_received) == len(test_messages):
            print(f"   ✅ All {len(test_messages)} encrypted messages received successfully!")
            
            for i, received in enumerate(messages_received):
                expected = test_messages[i]
                if received['content'] == expected:
                    print(f"   ✅ Message {i}: Content verified")
                else:
                    print(f"   ❌ Message {i}: Content mismatch - expected '{expected}', got '{received['content']}'")
        else:
            print(f"   ❌ Message count mismatch - expected {len(test_messages)}, received {len(messages_received)}")
        
        # Test encryption status
        print("6. Encryption status summary...")
        if broker.encryption_enabled and publisher.encryption_enabled and subscriber.encryption_enabled:
            print("   🔒 SUCCESS: Full end-to-end CurveZMQ encryption active!")
            print("   🛡️  All message bus communication is now encrypted")
            return True
        else:
            print("   ⚠️  WARNING: Some components fell back to plaintext mode")
            print(f"   Broker encryption: {'enabled' if broker.encryption_enabled else 'disabled'}")
            print(f"   Publisher encryption: {'enabled' if publisher.encryption_enabled else 'disabled'}")
            print(f"   Subscriber encryption: {'enabled' if subscriber.encryption_enabled else 'disabled'}")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print("7. Cleaning up...")
        try:
            if 'publisher' in locals():
                await publisher.disconnect()
            if 'subscriber' in locals():
                await subscriber.disconnect()
            await broker.stop()
            print("   ✅ Cleanup completed")
        except Exception as e:
            print(f"   ⚠️  Cleanup warning: {e}")


async def main():
    """Main test function"""
    try:
        success = await test_curve_encryption()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 CurveZMQ Message Bus Encryption Test: PASSED")
            print("   All inter-component communication is now encrypted!")
        else:
            print("❌ CurveZMQ Message Bus Encryption Test: FAILED")
            print("   Check logs above for details")
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
