#!/usr/bin/env python3
"""
Test encrypted XSUB/XPUB broker - Stage 2 (matches AICO architecture)
"""

import asyncio
import sys
import zmq
import zmq.asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.aico.security.key_manager import AICOKeyManager
from shared.aico.core.config import ConfigurationManager


class EncryptedBroker:
    """CurveZMQ XSUB/XPUB broker matching AICO architecture"""
    
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.frontend = None  # XSUB - publishers connect here
        self.backend = None   # XPUB - subscribers connect here
        self.running = False
        self.server_public_key = None
        self.server_secret_key = None
        
    async def start(self):
        """Start encrypted broker"""
        # Setup keys
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        master_key = key_manager.authenticate(interactive=False)
        
        # Derive broker keypair like AICO
        self.server_public_key, self.server_secret_key = key_manager.derive_curve_keypair(
            master_key, "message_bus_broker"
        )
        print(f"🔑 Broker keys derived")
        
        # Create sockets
        self.frontend = self.context.socket(zmq.XSUB)
        self.backend = self.context.socket(zmq.XPUB)
        
        # Configure CurveZMQ like AICO broker
        for socket in [self.frontend, self.backend]:
            socket.setsockopt(zmq.CURVE_SERVER, 1)
            socket.setsockopt_string(zmq.CURVE_SECRETKEY, self.server_secret_key)
            socket.setsockopt_string(zmq.CURVE_PUBLICKEY, self.server_public_key)
        
        self.frontend.bind("tcp://*:8001")  # Publishers connect here
        self.backend.bind("tcp://*:8002")   # Subscribers connect here
        
        self.running = True
        print("🔒 Encrypted broker started: Publishers->8001, Subscribers->8002")
        
        # Start proxy task
        asyncio.create_task(self._proxy_loop())
        await asyncio.sleep(0.1)  # Let broker start
        
    async def stop(self):
        """Stop broker"""
        self.running = False
        await asyncio.sleep(0.1)
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        self.context.term()
        
    async def _proxy_loop(self):
        """Manual proxy loop like AICO broker"""
        poller = zmq.asyncio.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)
        
        while self.running:
            try:
                socks = await poller.poll(timeout=100)
                for sock, event in socks:
                    if sock == self.frontend and event == zmq.POLLIN:
                        # Forward from publishers to subscribers
                        message = await self.frontend.recv_multipart()
                        await self.backend.send_multipart(message)
                    elif sock == self.backend and event == zmq.POLLIN:
                        # Forward subscriptions from subscribers to publishers
                        message = await self.backend.recv_multipart()
                        await self.frontend.send_multipart(message)
            except Exception as e:
                if self.running:
                    print(f"Proxy error: {e}")
                    await asyncio.sleep(0.1)


async def main():
    """Test encrypted XSUB/XPUB broker like AICO"""
    print("🔒 Stage 2: Encrypted XSUB/XPUB Broker Test")
    print("=" * 50)
    
    broker = EncryptedBroker()
    context = zmq.asyncio.Context()
    
    try:
        # Start broker
        await broker.start()
        
        # Setup client keys like AICO
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        master_key = key_manager.authenticate(interactive=False)
        
        client_pub, client_sec = key_manager.derive_curve_keypair(master_key, "test_client")
        
        # Create client sockets
        pub = context.socket(zmq.PUB)
        sub = context.socket(zmq.SUB)
        
        # Configure CurveZMQ like AICO clients
        for socket in [pub, sub]:
            socket.setsockopt_string(zmq.CURVE_SECRETKEY, client_sec)
            socket.setsockopt_string(zmq.CURVE_PUBLICKEY, client_pub)
            socket.setsockopt_string(zmq.CURVE_SERVERKEY, broker.server_public_key)
        
        # Connect like AICO clients
        pub.connect("tcp://localhost:8001")  # To XSUB frontend
        sub.connect("tcp://localhost:8002")  # To XPUB backend
        sub.setsockopt_string(zmq.SUBSCRIBE, "test")
        
        # Wait for connections
        await asyncio.sleep(0.5)
        
        # Test messages
        messages = ["Encrypted1", "Encrypted2", "Encrypted3"]
        received = []
        
        # Receiver
        async def receive():
            while len(received) < 3:
                try:
                    topic, msg = await asyncio.wait_for(sub.recv_multipart(), timeout=4.0)
                    received.append(msg.decode())
                    print(f"🔐 Received: {msg.decode()}")
                except asyncio.TimeoutError:
                    break
        
        # Start receiver
        recv_task = asyncio.create_task(receive())
        
        # Send messages
        await asyncio.sleep(0.3)
        for msg in messages:
            await pub.send_multipart([b"test", msg.encode()])
            print(f"🔒 Sent: {msg}")
            await asyncio.sleep(0.1)
        
        # Wait for completion
        await recv_task
        
        # Results
        success = len(received) == len(messages)
        print(f"\nResult: {'✅ PASS' if success else '❌ FAIL'} ({len(received)}/{len(messages)})")
        
        return 0 if success else 1
        
    finally:
        pub.close()
        sub.close()
        context.term()
        await broker.stop()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
