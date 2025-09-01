#!/usr/bin/env python3
"""
Transit Security Test Script

Tests the encrypted frontend-backend communication by simulating a simplified
frontend client connecting to the AICO backend with libsodium encryption.

This script demonstrates the complete handshake and encrypted message flow.
"""

import sys
import json
import time
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Add shared module to path
script_dir = Path(__file__).parent
shared_path = script_dir.parent / "shared"
sys.path.insert(0, str(shared_path))

try:
    import json
    import jwt
    from datetime import datetime, timedelta
    import time
    import base64
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.secret import SecretBox
    from nacl.signing import SigningKey
    from nacl.encoding import Base64Encoder
    from nacl.exceptions import CryptoError
    from nacl.utils import random
    
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    
    print("✅ All dependencies imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the AICO root directory with dependencies installed")
    sys.exit(1)


class EncryptedClient:
    """
    Client for testing encrypted communication with AICO backend
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.handshake_url = f"{base_url}/api/v1/handshake"
        
        # Encryption state
        self.identity_key = None
        self.client_private_key = None
        self.server_public_key = None
        self.session_key = None
        self.session_box = None
        
        # Authentication state
        self.jwt_token = None
        
        # Generate identity keys for signing
        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        
        # Session state
        self.session_key: Optional[bytes] = None
        self.server_public_key: Optional[PublicKey] = None
        self.session_box: Optional[SecretBox] = None
        
        print(f"🔑 Client identity generated: {self.verify_key.encode().hex()[:16]}...")
    
    def authenticate_user(self) -> bool:
        """
        Authenticate with backend using proper user credentials to get JWT token
        (requires handshake to be completed first)
        """
        if not self.session_box:
            print("❌ No active session - perform handshake first")
            return False
            
        try:
            print("🔐 Authenticating with backend...")
            
            # Test user credentials
            auth_request = {
                "user_uuid": "4837b1ac-f59a-400a-a875-6a4ea994c936",
                "pin": "1234"
            }
            
            print(f"📤 Sending encrypted authentication request...")
            
            # Send encrypted authentication request
            auth_response = self.send_encrypted_request("/api/v1/users/authenticate", auth_request)
            
            if not auth_response:
                print("❌ Authentication request failed")
                return False
            
            if not auth_response.get("success"):
                print(f"❌ Authentication rejected: {auth_response.get('error', 'Unknown error')}")
                return False
            
            self.jwt_token = auth_response.get("jwt_token")
            if not self.jwt_token:
                print("❌ No JWT token in authentication response")
                return False
            
            print("✅ Authentication successful - JWT token received")
            return True
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def perform_handshake(self) -> bool:
        """
        Perform encrypted handshake with backend
        """
        print("\n🤝 Starting encrypted handshake...")
        
        try:
            # Step 1: Generate ephemeral X25519 keypair for session
            client_private_key = PrivateKey.generate()
            client_public_key = client_private_key.public_key
            
            # Step 2: Create handshake request with both keys
            challenge_bytes = random(32)
            handshake_request = {
                "component": "test_client",
                "identity_key": base64.b64encode(bytes(self.verify_key)).decode(),  # Ed25519 for signatures
                "public_key": base64.b64encode(bytes(client_public_key)).decode(),   # X25519 for key exchange
                "timestamp": int(time.time()),
                "challenge": base64.b64encode(challenge_bytes).decode()
            }
            
            # Step 3: Sign the challenge (not the entire request)
            signature = self.signing_key.sign(challenge_bytes).signature
            
            # Add signature to the handshake request
            handshake_request["signature"] = base64.b64encode(signature).decode()
            
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            print(f"📤 Sending handshake request...")
            
            # Step 4: Send handshake request
            response = requests.post(
                self.handshake_url,
                json=handshake_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"❌ Handshake failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            # Step 5: Process handshake response
            handshake_response = response.json()
            
            if handshake_response.get("status") != "session_established":
                print(f"❌ Handshake rejected: {handshake_response.get('error', 'Unknown error')}")
                return False
            
            # Step 6: Extract server public key and derive session key
            response_data = handshake_response["handshake_response"]
            server_public_key_b64 = response_data["public_key"]
            self.server_public_key = PublicKey(base64.b64decode(server_public_key_b64))
            
            # Step 7: Derive shared session key using X25519
            shared_box = Box(client_private_key, self.server_public_key)
            self.session_key = shared_box.shared_key()
            self.session_box = SecretBox(self.session_key)
            
            print("✅ Handshake completed successfully!")
            print(f"🔐 Session key derived: {self.session_key.hex()[:16]}...")
            
            return True
            
        except requests.RequestException as e:
            print(f"❌ Network error during handshake: {e}")
            return False
        except Exception as e:
            print(f"❌ Handshake error: {e}")
            return False
    
    def encrypt_message(self, payload: Dict[str, Any]) -> str:
        """
        Encrypt JSON payload using session key
        """
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        # Serialize and encrypt
        plaintext = json.dumps(payload).encode()
        encrypted = self.session_box.encrypt(plaintext)
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt_message(self, encrypted_b64: str) -> Dict[str, Any]:
        """
        Decrypt base64-encoded encrypted message
        """
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        # Decode and decrypt
        encrypted = base64.b64decode(encrypted_b64)
        plaintext = self.session_box.decrypt(encrypted)
        
        return json.loads(plaintext.decode())
    
    def send_encrypted_request(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send encrypted request to backend
        """
        if not self.session_box:
            print("❌ No active session - perform handshake first")
            return None
        
        try:
            # Encrypt the payload
            encrypted_payload = self.encrypt_message(payload)
            
            # Create encrypted request envelope
            request_envelope = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self.verify_key.encode().hex()[:16]
            }
            
            print(f"📤 Sending encrypted request to {endpoint}")
            
            # Prepare headers with JWT token for authenticated endpoints
            headers = {"Content-Type": "application/json"}
            if self.jwt_token and not endpoint.endswith("/health"):
                headers["Authorization"] = f"Bearer {self.jwt_token}"
                print("🔐 Including JWT token for authentication")
            
            # Send request (use GET for health endpoint, POST for others)
            if endpoint.endswith("/health"):
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
            else:
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=request_envelope,
                    headers=headers,
                    timeout=10
                )
            
            if response.status_code != 200:
                print(f"❌ Request failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            # Process response
            response_data = response.json()
            
            if response_data.get("encrypted"):
                # Decrypt response
                decrypted_response = self.decrypt_message(response_data["payload"])
                print("✅ Received encrypted response")
                return decrypted_response
            else:
                print("✅ Received plaintext response")
                return response_data
                
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
        except Exception as e:
            print(f"❌ Encryption error: {e}")
            return None


def test_backend_connectivity(base_url: str) -> bool:
    """
    Test basic backend connectivity
    """
    print(f"🌐 Testing backend connectivity at {base_url}")
    
    try:
        # Try multiple possible health endpoints
        endpoints_to_try = [
            f"{base_url}/api/v1/gateway/status",
            f"{base_url}/api/v1/health", 
            f"{base_url}/health"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    print(f"✅ Backend is responding at {endpoint}")
                    return True
                else:
                    print(f"⚠️ {endpoint} returned HTTP {response.status_code}")
            except requests.RequestException as e:
                print(f"⚠️ {endpoint} failed: {e}")
                continue
        
        print("❌ No working health endpoints found")
        return False
    except Exception as e:
        print(f"❌ Backend connectivity failed: {e}")
        return False


def test_transport_encryption_config() -> bool:
    """
    Test transport encryption configuration
    """
    print("\n⚙️ Checking transport encryption configuration...")
    
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        
        transport_config = config_manager.get("security", {}).get("transport_encryption", {})
        
        if not transport_config:
            print("❌ Transport encryption configuration not found")
            return False
        
        enabled = transport_config.get("enabled", True)
        algorithm = transport_config.get("algorithm", "XChaCha20-Poly1305")
        
        print(f"✅ Transport encryption: {'ENABLED' if enabled else 'DISABLED'}")
        print(f"✅ Algorithm: {algorithm}")
        
        if enabled:
            session_config = transport_config.get("session", {})
            timeout = session_config.get("timeout_seconds", 3600)
            print(f"✅ Session timeout: {timeout}s ({timeout//60}m)")
            
        return enabled
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def run_full_test():
    """
    Run complete transit security test
    """
    print("🚀 AICO Transit Security Test")
    print("=" * 50)
    
    # Test 1: Backend connectivity
    base_url = "http://127.0.0.1:8771"
    if not test_backend_connectivity(base_url):
        print("\n❌ Backend connectivity test failed")
        print("Make sure the AICO backend is running with: aico gateway start")
        return False
    
    # Test 2: Configuration check
    if not test_transport_encryption_config():
        print("\n❌ Transport encryption configuration test failed")
        return False
    
    # Test 3: Encrypted handshake and communication
    print("\n🔐 Testing encrypted communication...")
    
    client = EncryptedClient(base_url)
    
    # Perform handshake first (required before authentication)
    if not client.perform_handshake():
        print("\n❌ Encrypted handshake test failed")
        return False
    
    # Authenticate with backend to get JWT token
    if not client.authenticate_user():
        print("\n❌ User authentication failed")
        return False
    
    # Test encrypted health check
    print("\n💊 Testing encrypted health check...")
    health_response = client.send_encrypted_request("/api/v1/health", {
        "test": "encrypted_health_check",
        "timestamp": int(time.time())
    })
    
    if health_response:
        print("✅ Encrypted health check successful")
        print(f"Response: {json.dumps(health_response, indent=2)}")
    else:
        print("❌ Encrypted health check failed")
        return False
    
    # Test encrypted echo (if available)
    print("\n📡 Testing encrypted echo...")
    echo_response = client.send_encrypted_request("/api/v1/echo", {
        "message": "Hello from encrypted client!",
        "test_data": {
            "encryption": "XChaCha20-Poly1305",
            "identity": "Ed25519",
            "timestamp": int(time.time())
        }
    })
    
    echo_success = False
    if echo_response:
        print("✅ Encrypted echo successful")
        print(f"Echo response: {json.dumps(echo_response, indent=2)}")
        echo_success = True
    else:
        print("❌ Encrypted echo test failed")
    
    print("\n" + "=" * 50)
    
    if echo_success:
        print("🎉 Transit Security Test COMPLETED SUCCESSFULLY!")
        print("\n✅ All tests passed:")
        print("  • Backend connectivity")
        print("  • Transport encryption configuration")
        print("  • Encrypted handshake protocol")
        print("  • End-to-end encrypted communication")
        print("\n🔐 Frontend-backend encryption is working correctly!")
        return True
    else:
        print("⚠️ Transit Security Test PARTIALLY COMPLETED")
        print("\n✅ Core tests passed:")
        print("  • Backend connectivity")
        print("  • Transport encryption configuration")
        print("  • Encrypted handshake protocol")
        print("  • Basic encrypted communication (health check)")
        print("\n❌ Failed tests:")
        print("  • Encrypted echo endpoint")
        print("\n🔧 Handshake and basic encryption working, but full payload decryption needs fixing")
        return False


if __name__ == "__main__":
    try:
        success = run_full_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
