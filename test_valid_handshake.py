#!/usr/bin/env python3
"""
Generate a valid handshake request with proper Ed25519 signatures
"""
import base64
import json
import time
import requests
from nacl.signing import SigningKey
from nacl.public import PrivateKey

def create_valid_handshake():
    # Generate Ed25519 signing key for identity
    identity_signing_key = SigningKey.generate()
    identity_public_key = identity_signing_key.verify_key.encode()
    
    # Generate X25519 key for session encryption
    session_private_key = PrivateKey.generate()
    session_public_key = session_private_key.public_key.encode()
    
    # Create challenge
    challenge = b"test_challenge_" + str(int(time.time())).encode()
    
    # Sign the challenge with identity key
    signature = identity_signing_key.sign(challenge).signature
    
    # Create handshake request
    handshake_request = {
        "component": "test_client",
        "identity_key": base64.b64encode(identity_public_key).decode(),
        "public_key": base64.b64encode(session_public_key).decode(),
        "challenge": base64.b64encode(challenge).decode(),
        "signature": base64.b64encode(signature).decode()
    }
    
    return {"handshake_request": handshake_request}

def test_handshake():
    payload = create_valid_handshake()
    
    print("Generated valid handshake payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(
            "http://127.0.0.1:8771/api/v1/handshake",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Handshake successful!")
        else:
            print("❌ Handshake failed")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_handshake()
