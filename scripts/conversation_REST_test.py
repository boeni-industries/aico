#!/usr/bin/env python3
"""
AICO Conversation REST API Test Script

Simple test focusing on /messages endpoint with auto-thread creation.
Sends user input and displays the AI response.
"""

import sys
import json
import time
import base64
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Add shared module to path
script_dir = Path(__file__).parent
shared_path = script_dir.parent / "shared"
sys.path.insert(0, str(shared_path))

from nacl.public import PrivateKey, PublicKey, Box
from nacl.secret import SecretBox
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import CryptoError
from nacl.utils import random

class ConversationTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8771"):
        self.base_url = base_url
        self.handshake_url = f"{base_url}/api/v1/handshake"
        
        # Encryption state
        self.session_key = None
        self.session_box = None
        self.server_public_key = None
        
        # Authentication state
        self.jwt_token = None
        self.test_user_uuid = None
        
        # Generate identity keys for signing
        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key

    def perform_handshake(self) -> bool:
        """Perform encrypted handshake with backend"""
        try:
            print("🤝 Performing encrypted handshake...")
            
            # Generate ephemeral X25519 keypair for session
            client_private_key = PrivateKey.generate()
            client_public_key = client_private_key.public_key
            
            # Create handshake request with both keys
            challenge_bytes = random(32)
            handshake_request = {
                "component": "conversation_test_client",
                "identity_key": base64.b64encode(bytes(self.verify_key)).decode(),
                "public_key": base64.b64encode(bytes(client_public_key)).decode(),
                "timestamp": int(time.time()),
                "challenge": base64.b64encode(challenge_bytes).decode()
            }
            
            # Sign the challenge (not the entire request)
            signature = self.signing_key.sign(challenge_bytes).signature
            handshake_request["signature"] = base64.b64encode(signature).decode()
            
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            # Send handshake request
            response = requests.post(
                self.handshake_url,
                json=handshake_payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ Handshake failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            # Process handshake response
            handshake_response = response.json()
            
            if handshake_response.get("status") != "session_established":
                print(f"❌ Handshake rejected: {handshake_response.get('error', 'Unknown error')}")
                return False
            
            # Extract server public key and derive session key
            response_data = handshake_response["handshake_response"]
            server_public_key_b64 = response_data["public_key"]
            self.server_public_key = PublicKey(base64.b64decode(server_public_key_b64))
            
            # Derive shared session key using X25519
            shared_box = Box(client_private_key, self.server_public_key)
            self.session_key = shared_box.shared_key()
            self.session_box = SecretBox(self.session_key)
            
            print("✅ Handshake successful")
            return True
            
        except Exception as e:
            print(f"❌ Handshake error: {e}")
            return False

    def ensure_test_user(self) -> Optional[str]:
        """Ensure a test user exists for authentication testing"""
        try:
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main", 
                "security", "user-create", 
                "ConvTestUser",
                "--nickname", "TestUser",
                "--pin", "1234"
            ], 
            cwd=Path(__file__).parent.parent,
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30,
            env=env
            )
            
            if result.returncode == 0:
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if line.startswith('UUID: '):
                        test_uuid = line.replace('UUID: ', '').strip()
                        self.test_user_uuid = test_uuid
                        return test_uuid
                        
                return self._generate_deterministic_uuid("conv_test_user")
            else:
                return self._generate_deterministic_uuid("conv_test_user")
                
        except Exception as e:
            return self._generate_deterministic_uuid("conv_test_user")
    
    def _generate_deterministic_uuid(self, seed: str) -> str:
        """Generate deterministic UUID from seed"""
        import hashlib
        hash_object = hashlib.md5(seed.encode())
        hex_dig = hash_object.hexdigest()
        return f"{hex_dig[:8]}-{hex_dig[8:12]}-{hex_dig[12:16]}-{hex_dig[16:20]}-{hex_dig[20:32]}"
    
    def authenticate_user(self) -> bool:
        """Authenticate with test user"""
        test_uuid = self.ensure_test_user()
        if not test_uuid:
            print("❌ Could not create or determine test user")
            return False
        
        print(f"🔐 Authenticating user: {test_uuid}")
        
        auth_request = {
            "user_uuid": test_uuid,
            "pin": "1234",
            "timestamp": int(time.time())
        }
        
        response = self.send_encrypted_request("/api/v1/users/authenticate", auth_request)
        
        if response and response.get("success", False):
            self.jwt_token = response.get("jwt_token", "")
            print("✅ Authentication successful")
            return True
        else:
            error_msg = response.get('message', 'Unknown error') if response else 'No response'
            print(f"❌ Authentication failed: {error_msg}")
            return False

    def encrypt_message(self, payload: Dict[str, Any]) -> str:
        """Encrypt JSON payload using session key"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        plaintext = json.dumps(payload).encode()
        encrypted = self.session_box.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_message(self, encrypted_b64: str) -> Dict[str, Any]:
        """Decrypt base64-encoded encrypted message"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        encrypted = base64.b64decode(encrypted_b64)
        plaintext = self.session_box.decrypt(encrypted)
        return json.loads(plaintext.decode())
    
    def send_encrypted_request(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send encrypted request to backend"""
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
            
            # Prepare headers with JWT token for authenticated endpoints
            headers = {"Content-Type": "application/json"}
            if self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=request_envelope,
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                # Try to parse and decrypt the response even if status code is not 200
                try:
                    response_data = response.json()
                    if response_data.get("encrypted"):
                        decrypted = self.decrypt_message(response_data["payload"])
                        print(f"❌ Request failed - HTTP {response.status_code}: {decrypted.get('message', 'Unknown error')}")
                        return decrypted
                except:
                    print(f"❌ Request failed - HTTP {response.status_code}: {response.text}")
                return None
            
            # Parse successful response
            response_data = response.json()
            if response_data.get("encrypted"):
                return self.decrypt_message(response_data["payload"])
            else:
                return response_data
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None

    def test_health_check(self) -> bool:
        """Test conversation health endpoint"""
        print("🏥 Health check...")
        try:
            response = self.send_encrypted_request("/api/v1/conversation/health", {})
            if response and response.get("status") == "healthy":
                print("✅ Service healthy")
                return True
            else:
                print("❌ Health check failed")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def send_unified_message(self, message: str) -> bool:
        """Send message using unified endpoint with auto-thread resolution"""
        request_data = {
            "message": message,
            "context": {"test_mode": True}
        }
        response = self.send_encrypted_request("/api/v1/conversation/messages", request_data)
        if response and response.get("success", False):
            # Use correct field names from UnifiedMessageResponse schema
            thread_id = response.get("thread_id")
            thread_action = response.get("thread_action", "unknown")
            thread_reasoning = response.get("thread_reasoning", "No reasoning provided")
            
            print(f"✅ Message sent to thread: {thread_id[:8] if thread_id else 'unknown'}...")
            print(f"🔄 Action: {thread_action}")
            print(f"💭 {thread_reasoning}")
            
            # Display AI response and status
            ai_response = response.get("ai_response", "No response available")
            print(f"🤖 AI Response: {ai_response}")
            print(f"📊 Status: {response.get('status', 'unknown')}")
            return True
        else:
            error_msg = response.get('error', response.get('message', 'Unknown error')) if response else 'No response'
            print(f"❌ Message failed: {error_msg}")
            return False

    def cleanup_test_user(self):
        """Clean up the test user created during testing"""
        if not self.test_user_uuid:
            return
            
        print(f"🧹 Cleaning up test user: {self.test_user_uuid}")
        
        try:
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main", 
                "security", "user-delete", 
                self.test_user_uuid,
                "--hard",
                "--confirm"
            ], 
            cwd=Path(__file__).parent.parent,
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30,
            env=env
            )
            
            if result.returncode == 0:
                print("✅ Test user cleaned up successfully")
            else:
                print(f"⚠️ Test user cleanup failed (exit code {result.returncode})")
                
        except Exception as e:
            print(f"⚠️ Test user cleanup error: {e}")
        finally:
            self.test_user_uuid = None

    def run_conversation_test(self) -> bool:
        """Run simple conversation test with /messages endpoint"""
        print("🚀 AICO Conversation Test - Auto-Thread Management")
        print("=" * 50)
        
        if not self.perform_handshake():
            return False
        if not self.authenticate_user():
            return False
        if not self.test_health_check():
            return False
            
        messages = [
            "Hello! How are you today?"
        ]
        
        success_count = 0
        for i, message in enumerate(messages, 1):
            print(f"\n💬 Message {i}: {message}")
            if self.send_unified_message(message):
                success_count += 1
            time.sleep(1)
            
        print(f"\n🎯 Results: {success_count}/{len(messages)} messages processed successfully")
        self.cleanup_test_user()
        return success_count == len(messages)


def main():
    """Main test execution"""
    print("AICO Conversation Test")
    print("Testing /messages endpoint with auto-thread creation\n")
    try:
        response = requests.get("http://127.0.0.1:8771/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend responding (status: 200)")
        else:
            print(f"⚠️ Backend responding but status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not responding: {e}")
        print("Please start the backend server first.")
        return False
    tester = ConversationTester()
    print(f"🔧 Initialized tester for {tester.base_url}")
    success = tester.run_conversation_test()
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
