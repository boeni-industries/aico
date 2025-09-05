#!/usr/bin/env python3
"""
Test ZMQ logging by making HTTP requests to the running gateway
This will test the actual gateway's logging pipeline
"""
import asyncio
import aiohttp
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.data.libsql.encrypted import EncryptedLibSQLConnection
from shared.aico.core.paths import AICOPaths

async def test_gateway_logging():
    """Test logging by making requests to the running gateway"""
    
    print("=== Testing Gateway ZMQ Logging Pipeline ===")
    
    try:
        # Get database connection to check logs
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        # Count initial logs from gateway
        print("1. Counting initial gateway logs...")
        result = db_connection.execute("""
            SELECT COUNT(*) FROM logs 
            WHERE subsystem NOT IN ('cli') 
            AND timestamp > datetime('now', '-5 minutes')
        """)
        initial_count = result.fetchone()[0]
        print(f"   Initial recent gateway log count: {initial_count}")
        
        # Make HTTP requests to generate backend logs
        print("2. Making HTTP requests to generate backend logs...")
        
        async with aiohttp.ClientSession() as session:
            # Make multiple requests to different endpoints
            endpoints = [
                'http://127.0.0.1:8771/api/v1/health',
                'http://127.0.0.1:8771/api/v1/health',
                'http://127.0.0.1:8771/api/v1/health'
            ]
            
            for i, endpoint in enumerate(endpoints):
                try:
                    async with session.get(endpoint) as response:
                        print(f"   Request {i+1}: {response.status} from {endpoint}")
                        await response.text()  # Consume response
                except Exception as e:
                    print(f"   Request {i+1} failed: {e}")
        
        # Wait for logs to be processed
        print("3. Waiting for log processing...")
        await asyncio.sleep(3)
        
        # Count logs after requests
        print("4. Counting logs after requests...")
        result = db_connection.execute("""
            SELECT COUNT(*) FROM logs 
            WHERE subsystem NOT IN ('cli') 
            AND timestamp > datetime('now', '-5 minutes')
        """)
        final_count = result.fetchone()[0]
        print(f"   Final recent gateway log count: {final_count}")
        
        new_logs = final_count - initial_count
        print(f"5. New logs generated: {new_logs}")
        
        if new_logs > 0:
            print("   ✅ SUCCESS: Gateway is generating logs via ZMQ transport!")
            
            # Show recent gateway logs
            print("6. Recent gateway log entries:")
            result = db_connection.execute("""
                SELECT timestamp, level, subsystem, module, message 
                FROM logs 
                WHERE subsystem NOT IN ('cli') 
                AND timestamp > datetime('now', '-2 minutes')
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            for row in result.fetchall():
                print(f"    {row[0]} [{row[1]}] {row[2]}.{row[3]}: {row[4][:80]}...")
                
        else:
            print("   ❌ FAILURE: No new logs generated")
            print("   This suggests the ZMQ logging pipeline is still not working")
            
            # Check if there are any recent logs at all
            result = db_connection.execute("""
                SELECT COUNT(*) FROM logs 
                WHERE timestamp > datetime('now', '-2 minutes')
            """)
            any_recent = result.fetchone()[0]
            print(f"   Any recent logs (including CLI): {any_recent}")
        
        return new_logs > 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gateway_logging())
    sys.exit(0 if success else 1)
