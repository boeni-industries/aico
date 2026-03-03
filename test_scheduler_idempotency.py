#!/usr/bin/env python3
"""
Test scheduler idempotency by sending multiple rapid requests with encrypted transport.
Based on scripts/memory_benchmark/api_client.py pattern.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional

import httpx

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError


class EncryptedClient:
    """Encrypted API client following AICO's transport security requirements."""

    def __init__(self, base_url: str = "http://localhost:8771", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._config = ConfigurationManager()
        self._config.initialize()
        self._key_manager = AICOKeyManager(self._config)
        self._identity_manager = TransportIdentityManager(self._key_manager)

        self._secure_channel: SecureTransportChannel = self._identity_manager.create_secure_channel("backend")
        identity = self._identity_manager.get_component_identity("backend")
        self._client_id = bytes(identity.verify_key).hex()[:16]

        self._jwt_token: Optional[str] = None
        self._session_established = False

    async def ensure_handshake(self) -> None:
        """Perform encryption handshake if not already done."""
        if self._session_established and self._secure_channel.is_session_valid():
            return

        handshake_payload = {"handshake_request": self._secure_channel.create_handshake_request()}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/v1/handshake", json=handshake_payload)

        if response.status_code != 200:
            raise EncryptionError(f"Handshake failed: HTTP {response.status_code} - {response.text}")

        data = response.json()
        if data.get("status") != "session_established" or "handshake_response" not in data:
            raise EncryptionError(f"Handshake failed: {data}")

        self._secure_channel.process_handshake_response(data["handshake_response"])
        self._session_established = True

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "X-Client-ID": self._client_id,
            "Content-Type": "application/json",
        }
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make encrypted request to backend."""
        await self.ensure_handshake()

        url = f"{self.base_url}{path}"

        if json_body is None:
            request_data = {"encrypted": True, "client_id": self._client_id}
        else:
            encrypted_payload = self._secure_channel.encrypt_json_payload(json_body)
            request_data = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self._client_id,
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(
                method.upper(),
                url,
                headers=self._headers(idempotency_key),
                json=request_data,
            )

        data = resp.json() if resp.content else {}
        if isinstance(data, dict) and data.get("encrypted") and "payload" in data:
            data = self._secure_channel.decrypt_json_payload(data["payload"])

        return {"status_code": resp.status_code, "data": data}

    async def authenticate(self, user_uuid: str, pin: str) -> None:
        """Authenticate and store JWT token."""
        result = await self.request(
            "POST",
            "/api/v1/users/authenticate",
            json_body={"user_uuid": user_uuid, "pin": pin},
        )

        data = result["data"]
        if not data.get("success"):
            raise PermissionError(data.get("error") or "Authentication failed")

        jwt_token = data.get("jwt_token")
        if not jwt_token:
            raise PermissionError("No JWT token returned")

        self._jwt_token = jwt_token


async def test_scheduler_idempotency():
    """Test scheduler idempotency with multiple rapid requests."""
    
    print("\n" + "="*60)
    print("Testing Scheduler Idempotency (Encrypted Transport)")
    print("="*60)
    
    # Initialize client
    client = EncryptedClient()
    
    # Authenticate (using default test user)
    print("\n1. Authenticating...")
    try:
        await client.authenticate(
            user_uuid="1e69de47-a3af-4343-8dba-dbf5dcf5f160",  # Michael's UUID from token
            pin="1234"  # Default test PIN
        )
        print("   ✓ Authenticated successfully")
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        print("\nNote: Update user_uuid and pin in the script if needed")
        return
    
    # Generate single idempotency key for all requests
    idempotency_key = str(uuid.uuid4())
    task_id = "agency.arbiter"
    
    print(f"\n2. Testing idempotency:")
    print(f"   Task: {task_id}")
    print(f"   Idempotency-Key: {idempotency_key}")
    print(f"   Sending 5 rapid requests...\n")
    
    results = []
    
    for i in range(5):
        try:
            import time
            start = time.time()
            
            result = await client.request(
                "POST",
                f"/api/v1/scheduler/tasks/{task_id}/trigger",
                json_body={},
                idempotency_key=idempotency_key,
            )
            
            elapsed_ms = int((time.time() - start) * 1000)
            status = result["status_code"]
            data = result["data"]
            
            print(f"   Request {i+1}: HTTP {status} ({elapsed_ms}ms)")
            
            results.append({
                "request": i + 1,
                "status": status,
                "elapsed_ms": elapsed_ms,
                "data": data,
            })
            
            # Small delay between requests
            await asyncio.sleep(0.05)
            
        except Exception as e:
            print(f"   Request {i+1}: ERROR - {e}")
            results.append({"request": i + 1, "error": str(e)})
    
    # Analyze results
    print("\n" + "="*60)
    print("Results Summary:")
    print("="*60)
    
    status_counts = {}
    for r in results:
        status = r.get("status", "ERROR")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"  HTTP {status}: {count} requests")
    
    print("\n" + "="*60)
    print("Detailed Results:")
    print("="*60)
    
    for r in results:
        print(f"\nRequest {r['request']}:")
        print(f"  Status: {r.get('status', 'ERROR')}")
        print(f"  Time: {r.get('elapsed_ms', 'N/A')}ms")
        if 'data' in r:
            print(f"  Response: {r['data']}")
        if 'error' in r:
            print(f"  Error: {r['error']}")
    
    print("\n" + "="*60)
    print("Expected Idempotent Behavior:")
    print("="*60)
    print("  ✓ First request: HTTP 200 (task triggered)")
    print("  ✓ Subsequent requests: HTTP 409 (conflict) or cached 200")
    print("  ✓ Task executes ONLY ONCE despite 5 requests")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_scheduler_idempotency())
