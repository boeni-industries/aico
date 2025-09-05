#!/usr/bin/env python3
"""
Debug script to check if log consumer is running and receiving messages
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.core.config import ConfigurationManager
from shared.aico.core.logging import initialize_logging, get_logger
from shared.aico.data.libsql.encrypted import EncryptedLibSQLConnection
from shared.aico.core.paths import AICOPaths

async def debug_log_consumer():
    """Debug the log consumer service status"""
    
    print("=== Debugging Log Consumer Service ===")
    
    try:
        # Initialize configuration and logging
        config_manager = ConfigurationManager()
        initialize_logging(config_manager)
        
        # Check if we can access the gateway's service container
        print("1. Checking gateway service container...")
        
        # Try to connect to the running gateway via HTTP API
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check gateway health endpoint
                async with session.get('http://127.0.0.1:8771/api/v1/health') as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"   ✅ Gateway is running: {health_data}")
                    else:
                        print(f"   ❌ Gateway health check failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Cannot connect to gateway: {e}")
        
        # Check ZMQ broker status by trying to connect directly
        print("2. Testing ZMQ broker connectivity...")
        
        try:
            from shared.aico.core.bus import MessageBusClient
            
            # Create a test client
            test_client = MessageBusClient("debug_client")
            
            # Try to connect
            await test_client.connect()
            
            if test_client.connected:
                print("   ✅ ZMQ broker is reachable")
                
                # Subscribe to logs topic to see if messages are flowing
                messages_received = []
                
                def test_callback(message):
                    messages_received.append(message)
                    print(f"   📨 Received message: {type(message)}")
                
                await test_client.subscribe("logs/", test_callback)
                print("   📡 Subscribed to logs/ topic")
                
                # Send a test log message
                logger = get_logger('debug', 'test')
                logger.info("Debug test message for ZMQ broker")
                
                # Wait for message
                await asyncio.sleep(2)
                
                print(f"   Messages received: {len(messages_received)}")
                
                await test_client.disconnect()
            else:
                print("   ❌ ZMQ broker connection failed")
                
        except Exception as e:
            print(f"   ❌ ZMQ broker test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Check if log consumer service is in the gateway process
        print("3. Checking log consumer service status...")
        
        # Look for log consumer debug output in recent logs
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        # Check for recent log consumer messages
        result = db_connection.execute("""
            SELECT timestamp, level, message 
            FROM logs 
            WHERE (subsystem = 'service' AND module LIKE '%log_consumer%')
               OR message LIKE '%LOG CONSUMER%'
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        log_consumer_logs = result.fetchall()
        if log_consumer_logs:
            print(f"   Found {len(log_consumer_logs)} recent log consumer messages:")
            for row in log_consumer_logs:
                print(f"     {row[0]} [{row[1]}] {row[2]}")
        else:
            print("   ❌ No recent log consumer messages found")
        
        # Check for any ZMQ-related logs
        result = db_connection.execute("""
            SELECT timestamp, level, message 
            FROM logs 
            WHERE message LIKE '%ZMQ%' OR message LIKE '%zmq%'
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        
        zmq_logs = result.fetchall()
        if zmq_logs:
            print(f"   Found {len(zmq_logs)} recent ZMQ-related messages:")
            for row in zmq_logs:
                print(f"     {row[0]} [{row[1]}] {row[2]}")
        else:
            print("   No recent ZMQ-related messages found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_log_consumer())
