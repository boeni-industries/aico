import asyncio
import zmq
import zmq.asyncio

# Generate proper Z85-encoded CurveZMQ keypairs
import zmq.auth

# Generate server keypair
server_public, server_secret = zmq.curve_keypair()
# Generate client keypair  
client_public, client_secret = zmq.curve_keypair()

SERVER_PUBLIC = server_public.decode('ascii')
SERVER_SECRET = server_secret.decode('ascii')
CLIENT_PUBLIC = client_public.decode('ascii')
CLIENT_SECRET = client_secret.decode('ascii')

PROXY_PUB_PORT = 9001
PROXY_SUB_PORT = 9002

async def broker():
    """XPUB/XSUB proxy with CurveZMQ - allows any client with correct keys"""
    ctx = zmq.asyncio.Context.instance()
    xsub = ctx.socket(zmq.XSUB)
    xpub = ctx.socket(zmq.XPUB)
    
    # CurveZMQ server setup - minimal auth (CURVE_ALLOW_ANY style)
    xsub.setsockopt_string(zmq.CURVE_SECRETKEY, SERVER_SECRET)
    xsub.setsockopt_string(zmq.CURVE_PUBLICKEY, SERVER_PUBLIC)
    xsub.setsockopt(zmq.CURVE_SERVER, 1)
    xsub.bind(f"tcp://*:{PROXY_PUB_PORT}")
    
    xpub.setsockopt_string(zmq.CURVE_SECRETKEY, SERVER_SECRET)
    xpub.setsockopt_string(zmq.CURVE_PUBLICKEY, SERVER_PUBLIC)
    xpub.setsockopt(zmq.CURVE_SERVER, 1)
    xpub.bind(f"tcp://*:{PROXY_SUB_PORT}")
    
    # Proxy loop
    poller = zmq.asyncio.Poller()
    poller.register(xsub, zmq.POLLIN)
    poller.register(xpub, zmq.POLLIN)
    
    while True:
        events = dict(await poller.poll())
        if xsub in events:
            msg = await xsub.recv_multipart()
            await xpub.send_multipart(msg)
        if xpub in events:
            msg = await xpub.recv_multipart()
            await xsub.send_multipart(msg)

async def publisher():
    """Publisher with CurveZMQ encryption"""
    ctx = zmq.asyncio.Context.instance()
    pub = ctx.socket(zmq.PUB)
    
    pub.setsockopt_string(zmq.CURVE_SECRETKEY, CLIENT_SECRET)
    pub.setsockopt_string(zmq.CURVE_PUBLICKEY, CLIENT_PUBLIC)
    pub.setsockopt_string(zmq.CURVE_SERVERKEY, SERVER_PUBLIC)
    pub.connect(f"tcp://localhost:{PROXY_PUB_PORT}")
    
    await asyncio.sleep(1)  # Allow subscriber to connect and subscribe
    await pub.send_multipart([b"test", b"hello encrypted world"])
    print("📤 Published encrypted message")

async def subscriber():
    """Subscriber with CurveZMQ encryption"""
    ctx = zmq.asyncio.Context.instance()
    sub = ctx.socket(zmq.SUB)
    
    sub.setsockopt_string(zmq.CURVE_SECRETKEY, CLIENT_SECRET)
    sub.setsockopt_string(zmq.CURVE_PUBLICKEY, CLIENT_PUBLIC)
    sub.setsockopt_string(zmq.CURVE_SERVERKEY, SERVER_PUBLIC)
    sub.connect(f"tcp://localhost:{PROXY_SUB_PORT}")
    sub.setsockopt(zmq.SUBSCRIBE, b"test")
    
    print("📡 Subscriber connected and subscribed to 'test'")
    
    try:
        topic, msg = await asyncio.wait_for(sub.recv_multipart(), timeout=5.0)
        print(f"📥 Received encrypted message: {msg.decode()} (topic: {topic.decode()})")
    except asyncio.TimeoutError:
        print("⏰ Subscriber timeout - no message received")

async def main():
    """Run minimal AICO-style encrypted message bus test"""
    print("🔐 Minimal CurveZMQ Test: Broker + Publisher + Subscriber")
    print("=" * 55)
    
    # Start broker first
    broker_task = asyncio.create_task(broker())
    await asyncio.sleep(0.1)  # Let broker start
    
    # Start subscriber and publisher concurrently
    sub_task = asyncio.create_task(subscriber())
    pub_task = asyncio.create_task(publisher())
    
    # Wait for both client tasks to complete
    await asyncio.gather(sub_task, pub_task)

if __name__ == "__main__":
    asyncio.run(main())
