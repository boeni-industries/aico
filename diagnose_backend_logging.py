#!/usr/bin/env python3
"""
Diagnose why the backend logging system isn't working at all
"""
import asyncio
import aiohttp
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def diagnose_backend_logging():
    """Diagnose backend logging system failure"""
    
    print("=== Diagnosing Backend Logging System ===")
    
    try:
        # Try to make a request that should definitely log something
        print("1. Making request to trigger logging...")
        
        async with aiohttp.ClientSession() as session:
            # Make request to logs endpoint which should definitely log
            try:
                async with session.post('http://127.0.0.1:8771/api/v1/logs/', 
                                      json={
                                          "level": "INFO",
                                          "message": "Test log from external client",
                                          "subsystem": "test",
                                          "module": "external"
                                      }) as response:
                    print(f"   POST /api/v1/logs/: {response.status}")
                    if response.status != 200:
                        text = await response.text()
                        print(f"   Response: {text}")
            except Exception as e:
                print(f"   POST /api/v1/logs/ failed: {e}")
        
        # Check if the logs endpoint even exists
        print("2. Testing logs endpoint availability...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('http://127.0.0.1:8771/api/v1/logs/') as response:
                    print(f"   GET /api/v1/logs/: {response.status}")
            except Exception as e:
                print(f"   GET /api/v1/logs/ failed: {e}")
        
        # Check what endpoints are actually available
        print("3. Checking available endpoints...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('http://127.0.0.1:8771/docs') as response:
                    print(f"   OpenAPI docs: {response.status}")
                    if response.status == 200:
                        print("   ✅ OpenAPI docs available at http://127.0.0.1:8771/docs")
            except Exception as e:
                print(f"   OpenAPI docs failed: {e}")
        
        # Test if the backend is logging startup messages at all
        print("4. Analysis of the logging system failure:")
        print("   The current gateway process started at ~21:09 but has generated ZERO logs")
        print("   This suggests one of the following issues:")
        print("   a) Backend logging system not initialized properly")
        print("   b) ZMQ transport failing silently (no fallback to direct DB)")
        print("   c) Logger factory not created or misconfigured")
        print("   d) Log level filtering blocking all messages")
        print("   e) Backend components not using the logging system at all")
        
        print("\n5. Recommendations:")
        print("   - Check gateway startup console for logging initialization errors")
        print("   - Verify backend components are actually calling logger methods")
        print("   - Check if ZMQ transport has fallback to direct database")
        print("   - Examine log level configuration to ensure messages aren't filtered")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_backend_logging())
