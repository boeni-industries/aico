#!/usr/bin/env python3
"""
Fix the ZMQ transport connection issue in the backend logging system
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.core.config import ConfigurationManager
from shared.aico.core.logging import initialize_logging, get_logger, _get_zmq_transport

async def fix_zmq_transport():
    """Fix the ZMQ transport connection issue"""
    
    print("=== Fixing ZMQ Transport Connection ===")
    
    try:
        # Initialize backend logging
        config_manager = ConfigurationManager()
        initialize_logging(config_manager)
        
        # Get the ZMQ transport
        zmq_transport = _get_zmq_transport()
        if not zmq_transport:
            print("❌ No ZMQ transport found")
            return False
        
        print("1. Current ZMQ transport status:")
        print(f"   Transport initialized: {getattr(zmq_transport, '_initialized', 'unknown')}")
        print(f"   Broker available: {getattr(zmq_transport, '_broker_available', 'unknown')}")
        
        client = getattr(zmq_transport, '_message_bus_client', None)
        if client:
            print(f"   Client exists: True")
            print(f"   Client connected: {getattr(client, 'connected', 'unknown')}")
        else:
            print(f"   Client exists: False")
        
        # Manually trigger broker ready notification and connection
        print("2. Manually triggering broker ready notification...")
        zmq_transport.mark_broker_ready()
        
        # Wait for connection
        print("3. Waiting for client connection...")
        await asyncio.sleep(2)
        
        # Check status after fix
        print("4. ZMQ transport status after fix:")
        print(f"   Broker available: {getattr(zmq_transport, '_broker_available', 'unknown')}")
        if client:
            print(f"   Client connected: {getattr(client, 'connected', 'unknown')}")
        
        # Test logging
        print("5. Testing logging after fix...")
        logger = get_logger('test', 'transport_fix')
        logger.info("Test message after ZMQ transport fix")
        logger.warning("Another test message to verify transport")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check if logs were persisted
        from shared.aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from shared.aico.core.paths import AICOPaths
        
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        result = db_connection.execute("""
            SELECT COUNT(*) FROM logs 
            WHERE subsystem = 'test' AND module = 'transport_fix'
            AND timestamp > datetime('now', '-1 minute')
        """)
        new_logs = result.fetchone()[0]
        
        print(f"6. New test logs persisted: {new_logs}")
        
        if new_logs >= 2:
            print("   ✅ SUCCESS: ZMQ transport is now working!")
            return True
        else:
            print("   ❌ FAILURE: ZMQ transport still not working")
            
            # Check if direct database fallback worked
            result = db_connection.execute("""
                SELECT message FROM logs 
                WHERE message LIKE '%direct database fallback%'
                AND timestamp > datetime('now', '-1 minute')
            """)
            fallback_logs = result.fetchall()
            
            if fallback_logs:
                print(f"   Found {len(fallback_logs)} direct database fallback messages")
                print("   This suggests ZMQ transport is failing but fallback is working")
            else:
                print("   No fallback messages found - logging system completely broken")
            
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_zmq_transport())
    sys.exit(0 if success else 1)
