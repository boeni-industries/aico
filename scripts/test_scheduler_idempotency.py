#!/usr/bin/env python3
"""Test scheduler idempotency with encrypted transport."""
import asyncio
import sys
import uuid
from pathlib import Path

# Add shared and scripts to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "shared"))
sys.path.insert(0, str(repo_root / "scripts"))

from memory_benchmark.api_client import EncryptedBenchmarkClient


async def test_scheduler_idempotency():
    """Send 5 rapid requests with same Idempotency-Key to test deduplication."""
    
    print('\n' + '='*60)
    print('Testing Scheduler Idempotency')
    print('='*60)
    
    client = EncryptedBenchmarkClient('http://localhost:8771')
    
    # Get JWT token from environment or use the one provided by user
    import os
    jwt_token = os.getenv('AICO_JWT_TOKEN') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTY5ZGU0Ny1hM2FmLTQzNDMtOGRiYS1kYmY1ZGNmNWYxNjAiLCJ1c2VyX3V1aWQiOiIxZTY5ZGU0Ny1hM2FmLTQzNDMtOGRiYS1kYmY1ZGNmNWYxNjAiLCJ0ZW5hbnRfaWQiOiIwM2UzNGM5MS03NjA1LTQ5ODQtOTUwZi01ZGViMWE5NDdhMzYiLCJ1c2VybmFtZSI6Ik1pY2hhZWwgQlx1MDBmNm5pIiwicm9sZXMiOlsiYWRtaW4iXSwicGVybWlzc2lvbnMiOltdLCJpYXQiOjE3NzI1NDc4ODQsImV4cCI6MTc3MjYzNDI4NCwiaXNzIjoiYWljby1hcGktZ2F0ZXdheSIsInR5cGUiOiJhY2Nlc3MifQ.p5g9r369WySKgzIyaOraC18GtVfZ_iJmqZVgNZnjXus'
    
    print('\n1. Setting JWT token...')
    client._jwt_token = jwt_token
    print('   ✓ JWT token set')
    
    idempotency_key = str(uuid.uuid4())
    domain = 'agency'
    
    print(f'\n2. Testing idempotency:')
    print(f'   Endpoint: POST /api/v1/system/config/domain/{domain}')
    print(f'   Idempotency-Key: {idempotency_key}')
    print(f'   Sending 5 rapid requests...\n')
    
    # First, get current config to get etag
    await client.ensure_handshake()
    import httpx
    
    get_url = f'{client.base_url}/api/v1/system/config/domain/{domain}'
    headers_get = {
        'X-Client-ID': client._client_id,
        'Content-Type': 'application/json',
    }
    if client._jwt_token:
        headers_get['Authorization'] = f'Bearer {client._jwt_token}'
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        resp = await http_client.get(get_url, headers=headers_get)
    
    data = resp.json() if resp.content else {}
    if isinstance(data, dict) and data.get('encrypted') and 'payload' in data:
        data = client._secure_channel.decrypt_json_payload(data['payload'])
    
    current_etag = data.get('etag', 'test-etag')
    current_content = data.get('content', {})
    
    print(f'   Current etag: {current_etag}')
    
    results = []
    for i in range(5):
        try:
            import time
            
            start = time.time()
            
            # Prepare request with Idempotency-Key header
            await client.ensure_handshake()
            url = f'{client.base_url}/api/v1/system/config/domain/{domain}'
            
            headers = {
                'X-Client-ID': client._client_id,
                'Content-Type': 'application/json',
                'Idempotency-Key': idempotency_key,
            }
            if client._jwt_token:
                headers['Authorization'] = f'Bearer {client._jwt_token}'
            
            # Prepare config save payload
            save_payload = {
                'etag': current_etag,
                'content': current_content,
                'format': 'yaml',
            }
            encrypted_payload = client._secure_channel.encrypt_json_payload(save_payload)
            request_data = {
                'encrypted': True,
                'payload': encrypted_payload,
                'client_id': client._client_id,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.put(url, headers=headers, json=request_data)
            
            elapsed_ms = int((time.time() - start) * 1000)
            status = resp.status_code
            
            data = resp.json() if resp.content else {}
            if isinstance(data, dict) and data.get('encrypted') and 'payload' in data:
                data = client._secure_channel.decrypt_json_payload(data['payload'])
            
            print(f'   Request {i+1}: HTTP {status} ({elapsed_ms}ms)')
            
            results.append({'request': i+1, 'status': status, 'elapsed_ms': elapsed_ms, 'data': data})
            
            await asyncio.sleep(0.05)
            
        except Exception as e:
            print(f'   Request {i+1}: ERROR - {e}')
            results.append({'request': i+1, 'error': str(e)})
    
    print('\n' + '='*60)
    print('Results Summary:')
    print('='*60)
    
    status_counts = {}
    for r in results:
        status = r.get('status', 'ERROR')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f'  HTTP {status}: {count} requests')
    
    print('\n' + '='*60)
    print('Detailed Results:')
    print('='*60)
    for r in results:
        print(f'\nRequest {r["request"]}:')
        print(f'  Status: {r.get("status", "ERROR")}')
        print(f'  Time: {r.get("elapsed_ms", "N/A")}ms')
        if 'data' in r:
            print(f'  Response: {r["data"]}')
        if 'error' in r:
            print(f'  Error: {r["error"]}')
    
    print('\n' + '='*60)
    print('Expected Idempotent Behavior:')
    print('='*60)
    print('  ✓ First request: HTTP 200 (task triggered)')
    print('  ✓ Subsequent: HTTP 409 (conflict) or cached 200')
    print('  ✓ Task executes ONLY ONCE despite 5 requests')
    print('='*60 + '\n')
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_scheduler_idempotency())
