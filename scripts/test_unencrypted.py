#!/usr/bin/env python3
"""
Test unencrypted XSUB/XPUB broker - Stage 1 (matches AICO architecture)
"""

import asyncio
import sys
import zmq
import zmq.asyncio


class UnencryptedBroker:
    """Simple XSUB/XPUB broker matching AICO architecture"""
    
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.frontend = None  # XSUB - publishers connect here
        self.backend = None   # XPUB - subscribers connect here
        self.running = False
        
    async def start(self):
        """Start broker"""
        self.frontend = self.context.socket(zmq.XSUB)
        self.backend = self.context.socket(zmq.XPUB)
        
        self.frontend.bind("tcp://*:7001")  # Publishers connect here
        self.backend.bind("tcp://*:7002")   # Subscribers connect here
        
        self.running = True
        print("🔄 Broker started: Publishers->7001, Subscribers->7002")
        
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
    """Test XSUB/XPUB broker like AICO"""
    print("🧪 Stage 1: Unencrypted XSUB/XPUB Broker Test")
    print("=" * 50)
    
    broker = UnencryptedBroker()
    context = zmq.asyncio.Context()
    
    try:
        # Start broker
        await broker.start()
        
        # Create client sockets
        pub = context.socket(zmq.PUB)
        sub = context.socket(zmq.SUB)
        
        # Connect like AICO clients
        pub.connect("tcp://localhost:7001")  # To XSUB frontend
        sub.connect("tcp://localhost:7002")  # To XPUB backend
        sub.setsockopt_string(zmq.SUBSCRIBE, "test")
        
        # Wait for connections
        await asyncio.sleep(0.3)
        
        # Test messages
        messages = ["Hello", "World", "Done"]
        received = []
        
        # Receiver
        async def receive():
            while len(received) < 3:
                try:
                    topic, msg = await asyncio.wait_for(sub.recv_multipart(), timeout=3.0)
                    received.append(msg.decode())
                    print(f"📨 Received: {msg.decode()}")
                except asyncio.TimeoutError:
                    break
        
        # Start receiver
        recv_task = asyncio.create_task(receive())
        
        # Send messages
        await asyncio.sleep(0.2)
        for msg in messages:
            await pub.send_multipart([b"test", msg.encode()])
            print(f"📤 Sent: {msg}")
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
