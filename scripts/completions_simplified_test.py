#!/usr/bin/env python3
"""
Completions Test Script

Tests the modelservice completions endpoint directly to verify Ollama integration.
This script sends a simple "hello world" request to test the complete flow.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add shared module to path for encryption
script_dir = Path(__file__).parent
shared_path = script_dir.parent / "shared"
sys.path.insert(0, str(shared_path))

from nacl.public import PrivateKey, PublicKey, Box
import base64


async def perform_handshake(client: httpx.AsyncClient) -> tuple[Box, str]:
    """Perform encryption handshake with modelservice using AICO format."""
    import time
    import os
    from nacl.signing import SigningKey, VerifyKey
    
    # Generate ephemeral keypair
    client_private_key = PrivateKey.generate()
    client_public_key = client_private_key.public_key
    
    # Generate signing keypair for authentication
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    
    # Create handshake request in AICO format
    challenge_bytes = os.urandom(32)
    handshake_request = {
        "component": "test_client",
        "identity_key": base64.b64encode(bytes(verify_key)).decode(),  # Ed25519 for signatures
        "public_key": base64.b64encode(bytes(client_public_key)).decode(),   # X25519 for key exchange
        "timestamp": int(time.time()),
        "challenge": base64.b64encode(challenge_bytes).decode()
    }
    
    # Sign the challenge
    signature = signing_key.sign(challenge_bytes).signature
    handshake_request["signature"] = base64.b64encode(signature).decode()
    
    # Wrap in proper payload format
    handshake_payload = {
        "handshake_request": handshake_request
    }
    
    # Send handshake request
    handshake_response = await client.post(
        "http://127.0.0.1:8773/api/v1/handshake",
        json=handshake_payload
    )
    
    if handshake_response.status_code != 200:
        raise Exception(f"Handshake failed: {handshake_response.text}")
    
    handshake_data = handshake_response.json()
    print(f"Handshake response: {json.dumps(handshake_data, indent=2)}")
    
    # Get server public key from AICO response format
    if "handshake_response" in handshake_data:
        response_data = handshake_data["handshake_response"]
        server_public_key_b64 = response_data["public_key"]
    else:
        # Fallback to direct format
        server_public_key_b64 = handshake_data["public_key"]
    
    # Generate client ID - this should match what the backend generates
    # Backend uses: identity_key_bytes.hex()[:16]
    client_id = bytes(verify_key).hex()[:16]
    
    # Create encryption box
    server_public_key = PublicKey(base64.b64decode(server_public_key_b64))
    box = Box(client_private_key, server_public_key)
    
    return box, client_id


async def test_modelservice_completions():
    """Test the modelservice completions endpoint with encryption."""
    print("Testing modelservice completions endpoint with encryption...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Perform handshake
            print("Performing encryption handshake...")
            box, client_id = await perform_handshake(client)
            print(f"Handshake successful, client_id: {client_id}")
            
            # Test request payload
            test_request = {
                "model": "hermes3:8b",
                "prompt": "Hello! Please respond with a brief greeting.",
                "parameters": {
                    "max_tokens": 50,
                    "temperature": 0.7
                }
            }
            
            print(f"Request payload: {json.dumps(test_request, indent=2)}")
            
            # Encrypt the request
            encrypted_data = box.encrypt(json.dumps(test_request).encode())
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            print("\nSending encrypted request to http://127.0.0.1:8773/api/v1/completions...")
            
            response = await client.post(
                "http://127.0.0.1:8773/api/v1/completions",
                json={
                    "encrypted": True,
                    "payload": encrypted_b64,
                    "client_id": client_id
                },
                headers={"User-Agent": "completions_test_client"}
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 500, 502]:  # 502 might be encrypted error response
                result = response.json()
                
                # Decrypt response if encrypted
                if "encrypted" in result and result.get("encrypted") == True:
                    encrypted_response = base64.b64decode(result["payload"])
                    decrypted_response = box.decrypt(encrypted_response)
                    result = json.loads(decrypted_response.decode())
                
                print(f"\nSuccess! Response:")
                print(json.dumps(result, indent=2))
                
                # Extract and display the completion
                if "completion" in result:
                    completion_text = result["completion"]
                    print(f"\nModel Response: '{completion_text}'")
                else:
                    print("No completion text found in response")
                    
            else:
                print(f"\nError Response:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                    
    except httpx.ConnectError:
        print("❌ Connection failed - is the modelservice running on port 8773?")
    except httpx.TimeoutException:
        print("❌ Request timed out - model may be loading or server overloaded")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def test_ollama_direct():
    """Test Ollama directly to verify it's working."""
    print("\nTesting Ollama directly...")
    
    ollama_request = {
        "model": "hermes3:8b",
        "prompt": "Hello!",
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json=ollama_request
            )
            
            print(f"Ollama Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Ollama Response: '{result.get('response', 'No response field')}'")
            else:
                print(f"Ollama Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting completions test...\n")
    
    # Test Ollama directly first
    await test_ollama_direct()
    
    print("\n" + "="*50)
    
    # Test modelservice completions endpoint
    await test_modelservice_completions()
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
