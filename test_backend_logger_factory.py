#!/usr/bin/env python3
"""
Test if the backend logger factory is working by making HTTP requests
that should trigger middleware logging
"""
import asyncio
import aiohttp
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.data.libsql.encrypted import EncryptedLibSQLConnection
from shared.aico.core.paths import AICOPaths

async def test_backend_logger_factory():
    """Test backend logger factory by triggering middleware that should log"""
    
    print("=== Testing Backend Logger Factory ===")
    
    try:
        # Get database connection
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        # Check current log count
        result = db_connection.execute("SELECT COUNT(*) FROM logs WHERE timestamp > datetime('now', '-5 minutes')")
        initial_count = result.fetchone()[0]
        print(f"1. Initial recent log count: {initial_count}")
        
        # Make requests that should trigger encryption middleware logging
        print("2. Making requests to trigger encryption middleware...")
        
        async with aiohttp.ClientSession() as session:
            # The encryption middleware should log every request
            for i in range(3):
                try:
                    async with session.get('http://127.0.0.1:8771/api/v1/health') as response:
                        print(f"   Request {i+1}: {response.status}")
                except Exception as e:
                    print(f"   Request {i+1} failed: {e}")
        
        # Wait for logs
        await asyncio.sleep(3)
        
        # Check for new logs
        result = db_connection.execute("SELECT COUNT(*) FROM logs WHERE timestamp > datetime('now', '-5 minutes')")
        final_count = result.fetchone()[0]
        new_logs = final_count - initial_count
        
        print(f"3. New logs after requests: {new_logs}")
        
        if new_logs > 0:
            print("   ✅ Backend logging system is working!")
            
            # Show recent logs
            result = db_connection.execute("""
                SELECT timestamp, level, subsystem, module, message 
                FROM logs 
                WHERE timestamp > datetime('now', '-2 minutes')
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            
            print("   Recent logs:")
            for row in result.fetchall():
                print(f"     {row[0]} [{row[1]}] {row[2]}.{row[3]}: {row[4][:60]}...")
        else:
            print("   ❌ Backend logging system is NOT working")
            
            # Check if the issue is that middleware isn't logging
            print("4. Checking if this is a middleware logging issue...")
            
            # Look for any logs with 'encryption' or 'middleware' in the message
            result = db_connection.execute("""
                SELECT COUNT(*) FROM logs 
                WHERE (message LIKE '%encryption%' OR message LIKE '%middleware%')
                AND timestamp > datetime('now', '-1 hour')
            """)
            middleware_logs = result.fetchone()[0]
            
            print(f"   Recent middleware/encryption logs: {middleware_logs}")
            
            if middleware_logs == 0:
                print("   🔍 No middleware logs found - middleware may not be logging")
                print("   This suggests the backend logger factory is not working")
            else:
                print("   🔍 Middleware logs exist but not recent - timing issue?")
        
        return new_logs > 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_backend_logger_factory())
    sys.exit(0 if success else 1)
