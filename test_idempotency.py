#!/usr/bin/env python3
"""
Quick script to test idempotency by sending multiple rapid requests.
"""
import httpx
import time
import uuid
from datetime import datetime

# Configuration
GATEWAY_URL = "http://localhost:3002"  # Studio proxy (no encryption required)
TASK_ID = "agency.arbiter"

# You'll need to get a valid JWT token from Studio
# Open Studio dev tools, go to Application > Local Storage, and copy the 'token' value
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTY5ZGU0Ny1hM2FmLTQzNDMtOGRiYS1kYmY1ZGNmNWYxNjAiLCJ1c2VyX3V1aWQiOiIxZTY5ZGU0Ny1hM2FmLTQzNDMtOGRiYS1kYmY1ZGNmNWYxNjAiLCJ0ZW5hbnRfaWQiOiIwM2UzNGM5MS03NjA1LTQ5ODQtOTUwZi01ZGViMWE5NDdhMzYiLCJ1c2VybmFtZSI6Ik1pY2hhZWwgQlx1MDBmNm5pIiwicm9sZXMiOlsiYWRtaW4iXSwicGVybWlzc2lvbnMiOltdLCJpYXQiOjE3NzI1NDc4ODQsImV4cCI6MTc3MjYzNDI4NCwiaXNzIjoiYWljby1hcGktZ2F0ZXdheSIsInR5cGUiOiJhY2Nlc3MifQ.p5g9r369WySKgzIyaOraC18GtVfZ_iJmqZVgNZnjXus"

def test_scheduler_idempotency():
    """Send multiple rapid requests with the same Idempotency-Key"""
    
    # Generate a single idempotency key for all requests
    idempotency_key = str(uuid.uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
    }
    
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    url = f"{GATEWAY_URL}/api/v1/scheduler/tasks/{TASK_ID}/trigger"
    
    print(f"\n{'='*60}")
    print(f"Testing Scheduler Idempotency")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Idempotency-Key: {idempotency_key}")
    print(f"{'='*60}\n")
    
    results = []
    
    # Send 5 rapid requests with the SAME idempotency key
    for i in range(5):
        try:
            start = time.time()
            response = httpx.post(url, headers=headers, timeout=10.0)
            elapsed = time.time() - start
            
            result = {
                "request": i + 1,
                "status": response.status_code,
                "elapsed_ms": int(elapsed * 1000),
                "timestamp": datetime.now().isoformat(),
            }
            
            if response.status_code == 200:
                result["body"] = response.json()
            elif response.status_code == 409:
                result["conflict"] = "Idempotency conflict (expected)"
            else:
                result["error"] = response.text[:200]
            
            results.append(result)
            
            print(f"Request {i+1}: HTTP {response.status_code} ({elapsed*1000:.0f}ms)")
            
            # Small delay to ensure requests are sequential but rapid
            time.sleep(0.05)
            
        except Exception as e:
            print(f"Request {i+1}: ERROR - {e}")
            results.append({
                "request": i + 1,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
    
    print(f"\n{'='*60}")
    print("Results Summary:")
    print(f"{'='*60}")
    
    status_counts = {}
    for r in results:
        status = r.get("status", "ERROR")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"  HTTP {status}: {count} requests")
    
    print(f"\n{'='*60}")
    print("Expected Idempotent Behavior:")
    print(f"{'='*60}")
    print("  - First request: HTTP 200 (task triggered)")
    print("  - Subsequent requests: HTTP 409 (conflict) or cached 200")
    print("  - Task should execute ONLY ONCE despite 5 requests")
    print(f"{'='*60}\n")
    
    # Detailed results
    print("\nDetailed Results:")
    for r in results:
        print(f"\n  Request {r['request']}:")
        print(f"    Status: {r.get('status', 'ERROR')}")
        print(f"    Time: {r.get('elapsed_ms', 'N/A')}ms")
        if 'body' in r:
            print(f"    Response: {r['body']}")
        if 'conflict' in r:
            print(f"    Note: {r['conflict']}")
        if 'error' in r:
            print(f"    Error: {r['error']}")

if __name__ == "__main__":
    test_scheduler_idempotency()
