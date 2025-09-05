#!/usr/bin/env python3
"""
Force backend logging by making a request that should definitely generate logs
"""
import asyncio
import aiohttp
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.aico.data.libsql.encrypted import EncryptedLibSQLConnection
from shared.aico.core.paths import AICOPaths

async def force_backend_logging():
    """Force backend logging by triggering error conditions"""
    
    print("=== Forcing Backend Logging ===")
    
    try:
        # Get database connection
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        db_connection = EncryptedLibSQLConnection(db_path)
        
        # Check what the most recent backend log timestamp is
        print("1. Checking most recent backend logs...")
        result = db_connection.execute("""
            SELECT timestamp, level, subsystem, module, message 
            FROM logs 
            WHERE subsystem NOT IN ('cli') 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent_logs = result.fetchall()
        
        if recent_logs:
            print("   Most recent backend logs:")
            for row in recent_logs:
                print(f"     {row[0]} [{row[1]}] {row[2]}.{row[3]}: {row[4][:60]}...")
        else:
            print("   ❌ No backend logs found in database")
        
        # Try to trigger logging by making requests that should generate errors/warnings
        print("2. Making requests to trigger backend logging...")
        
        async with aiohttp.ClientSession() as session:
            # Try requests that should generate logs
            test_requests = [
                ('GET', 'http://127.0.0.1:8771/api/v1/nonexistent', 'Should generate 404 error'),
                ('POST', 'http://127.0.0.1:8771/api/v1/health', 'Should generate method not allowed'),
                ('GET', 'http://127.0.0.1:8771/api/v1/health', 'Should generate success log'),
            ]
            
            for method, url, description in test_requests:
                try:
                    if method == 'GET':
                        async with session.get(url) as response:
                            print(f"   {method} {url}: {response.status} - {description}")
                    elif method == 'POST':
                        async with session.post(url) as response:
                            print(f"   {method} {url}: {response.status} - {description}")
                except Exception as e:
                    print(f"   {method} {url}: ERROR {e} - {description}")
        
        # Wait for logs to be processed
        print("3. Waiting for log processing...")
        await asyncio.sleep(5)
        
        # Check for new logs
        print("4. Checking for new backend logs...")
        result = db_connection.execute("""
            SELECT timestamp, level, subsystem, module, message 
            FROM logs 
            WHERE subsystem NOT IN ('cli') 
            AND timestamp > datetime('now', '-2 minutes')
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        new_logs = result.fetchall()
        
        if new_logs:
            print(f"   ✅ Found {len(new_logs)} new backend logs:")
            for row in new_logs:
                print(f"     {row[0]} [{row[1]}] {row[2]}.{row[3]}: {row[4][:60]}...")
        else:
            print("   ❌ No new backend logs found")
            
            # Check if ANY logs were added (including CLI)
            result = db_connection.execute("""
                SELECT COUNT(*) FROM logs 
                WHERE timestamp > datetime('now', '-2 minutes')
            """)
            any_new = result.fetchone()[0]
            print(f"   Total new logs (any subsystem): {any_new}")
            
            if any_new == 0:
                print("   🔍 No logs at all were added - this suggests a fundamental issue")
            else:
                print("   🔍 CLI logs are working but backend logs are not reaching database")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(force_backend_logging())
