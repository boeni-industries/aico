#!/usr/bin/env python3
"""
Test script to verify ZMQ logging pipeline is working
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

async def test_zmq_logging_pipeline():
    """Test the ZMQ logging pipeline end-to-end"""
    
    print("=== Testing ZMQ Logging Pipeline ===")
    
    try:
        # Initialize configuration
        print("1. Initializing configuration...")
        config_manager = ConfigurationManager()
        
        # Get database path
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        print(f"2. Database path: {db_path}")
        
        # Create database connection
        print("3. Creating database connection...")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        # Initialize backend logging system (with ZMQ transport)
        print("4. Initializing backend logging system...")
        initialize_logging(config_manager)
        print("   ✅ Backend logging initialized")
        
        # Get a logger instance
        print("5. Getting logger instance...")
        logger = get_logger('test', 'zmq_pipeline')
        print("   ✅ Logger obtained")
        
        # Count logs before sending test messages
        print("6. Counting existing logs...")
        result = db_connection.execute("SELECT COUNT(*) FROM logs WHERE subsystem = 'test' AND module = 'zmq_pipeline'")
        initial_count = result.fetchone()[0]
        print(f"   Initial log count: {initial_count}")
        
        # Send test log messages
        print("7. Sending test log messages via ZMQ transport...")
        logger.info("ZMQ Pipeline Test - INFO message")
        logger.warning("ZMQ Pipeline Test - WARNING message") 
        logger.error("ZMQ Pipeline Test - ERROR message")
        print("   ✅ Test messages sent")
        
        # Wait for async processing
        print("8. Waiting for ZMQ processing...")
        await asyncio.sleep(3)
        
        # Count logs after sending test messages
        print("9. Counting logs after test...")
        result = db_connection.execute("SELECT COUNT(*) FROM logs WHERE subsystem = 'test' AND module = 'zmq_pipeline'")
        final_count = result.fetchone()[0]
        print(f"   Final log count: {final_count}")
        
        # Check if logs were persisted
        new_logs = final_count - initial_count
        print(f"10. New logs persisted: {new_logs}")
        
        if new_logs >= 3:
            print("   ✅ SUCCESS: ZMQ logging pipeline is working!")
            
            # Show the actual log entries
            print("11. Recent test log entries:")
            result = db_connection.execute("""
                SELECT timestamp, level, message 
                FROM logs 
                WHERE subsystem = 'test' AND module = 'zmq_pipeline'
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            for row in result.fetchall():
                print(f"    {row[0]} [{row[1]}] {row[2]}")
        else:
            print("   ❌ FAILURE: Logs not persisted via ZMQ transport")
            print("   This indicates the ZMQ logging pipeline is not working")
            
            # Check if logs are using direct database fallback
            result = db_connection.execute("""
                SELECT COUNT(*) FROM logs 
                WHERE message LIKE '%direct database fallback%'
                AND timestamp > datetime('now', '-1 minute')
            """)
            fallback_count = result.fetchone()[0]
            if fallback_count > 0:
                print(f"   Found {fallback_count} recent fallback messages - ZMQ transport failing")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return new_logs >= 3

if __name__ == "__main__":
    success = asyncio.run(test_zmq_logging_pipeline())
    sys.exit(0 if success else 1)
