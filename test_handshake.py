#!/usr/bin/env python3
import base64
import os
import json

# Generate proper 32-byte keys for testing
identity_key = base64.b64encode(os.urandom(32)).decode()
public_key = base64.b64encode(os.urandom(32)).decode()
challenge = base64.b64encode(os.urandom(32)).decode()
signature = base64.b64encode(os.urandom(64)).decode()  # Ed25519 signatures are 64 bytes

payload = {
    "handshake_request": {
        "component": "test_client",
        "identity_key": identity_key,
        "public_key": public_key,
        "challenge": challenge,
        "signature": signature
    }
}

print("Test payload with proper key lengths:")
print(json.dumps(payload, indent=2))

# Also print curl command
curl_data = json.dumps(payload).replace('"', '\\"')
print(f"\nCurl command:")
print(f'curl -X POST http://127.0.0.1:8771/api/v1/handshake -H "Content-Type: application/json" -d "{curl_data}"')
