#!/usr/bin/env python3
"""
AICO Conversation REST API Test Script

Tests the conversation endpoints using proper authentication and encryption.
Leverages existing AICO security infrastructure for DRY compliance.
"""

import sys
import json
import time
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, Optional

# Add shared module to path
script_dir = Path(__file__).parent
shared_path = script_dir.parent / "shared"
sys.path.insert(0, str(shared_path))

try:
    import requests
    from aico.core.config import ConfigurationManager
    from aico.security.key_manager import AICOKeyManager
    from aico.security.transport import SecureTransportChannel, ComponentIdentity
    from aico.core.logging import AICOLoggerFactory
    
    # Initialize config manager
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=False)
    config_manager.set("logging.levels.default", "INFO")
    
    # Create logger factory
    logger_factory = AICOLoggerFactory(config_manager)
    logger = logger_factory.create_logger("test", "conversation_rest")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required dependencies are installed")
    sys.exit(1)


class ConversationRESTTester:
    """Test AICO conversation REST API using existing security infrastructure"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8771"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Use existing AICO security infrastructure
        self.identity = ComponentIdentity.generate("conversation_test_client")
        self.key_manager = AICOKeyManager(config_manager)
        self.transport = SecureTransportChannel(self.identity, self.key_manager)
        
        # Authentication
        self.jwt_token = None
        self.test_user_uuid = None
        
        # Conversation state
        self.current_thread_id = None
        
        print(f"🔧 Initialized conversation tester for {base_url}")
    
    def perform_handshake(self) -> bool:
        """Perform encrypted handshake using existing transport layer"""
        try:
            print("🤝 Performing encrypted handshake...")
            
            handshake_request = self.transport.create_handshake_request()
            
            # Wrap in envelope like transit_security_test.py does
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/handshake",
                json=handshake_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "session_established":
                    # Extract the actual handshake response from the envelope
                    handshake_response = response_data.get("handshake_response", {})
                    if self.transport.process_handshake_response(handshake_response):
                        print("✅ Handshake successful")
                        return True
                    else:
                        print("❌ Handshake processing failed")
                        return False
                else:
                    print(f"❌ Handshake rejected: {response_data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Handshake failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Handshake error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_encrypted_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send encrypted request using existing transport layer"""
        if not self.transport.is_session_valid():
            print("❌ No valid session established")
            return None
        
        try:
            # Encrypt using existing transport
            encrypted_payload = self.transport.encrypt_json_payload(data)
            
            # Create request envelope like transit_security_test.py
            request_envelope = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self.identity.verify_key.encode().hex()[:16]
            }
            
            # Send encrypted request
            headers = {"Content-Type": "application/json"}
            if self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
            
            # All encrypted requests are sent as POST with the envelope
            # The backend will handle the actual method based on the endpoint
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=request_envelope,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("encrypted"):
                    # Decrypt response
                    return self.transport.decrypt_json_payload(response_data["payload"])
                else:
                    return response_data
            else:
                print(f"❌ Request failed - HTTP {response.status_code}: {response.text}")
                # Try to decrypt error response if it's encrypted
                try:
                    response_data = response.json()
                    if response_data.get("encrypted") and "payload" in response_data:
                        return self.transport.decrypt_json_payload(response_data["payload"])
                except Exception:
                    pass
                return None
                
        except Exception as e:
            print(f"❌ Encrypted request error: {e}")
            return None
    
    def ensure_test_user(self) -> Optional[str]:
        """Create test user using CLI - reuse existing pattern"""
        return self._create_test_user_via_cli("Conversation Test User", "ConvTestUser")
    
    def _create_test_user_via_cli(self, full_name: str, nickname: str) -> Optional[str]:
        """Create test user via CLI - extracted from existing scripts"""
        try:
            print(f"👤 Creating test user: {nickname}...")
            
            import os
            
            # Handle Windows encoding issues
            encoding = 'utf-8'
            if platform.system() == 'Windows':
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
            else:
                env = None
            
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main",
                "security", "user-create", 
                full_name,
                "--nickname", nickname, 
                "--pin", "1234"
            ],
            cwd=script_dir.parent, capture_output=True, text=True,
            encoding=encoding, errors='replace', timeout=30, env=env
            )
            
            if result.returncode == 0:
                # Extract UUID from output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if line.startswith('UUID: '):
                        test_uuid = line.replace('UUID: ', '').strip()
                        print(f"✅ Test user created: {test_uuid}")
                        self.test_user_uuid = test_uuid
                        return test_uuid
                        
                print("⚠️ Test user created but UUID not found in output")
                return self._generate_deterministic_uuid("conv_test_user")
            else:
                # User might already exist, try deterministic UUID
                print(f"⚠️ User creation failed (exit code {result.returncode}), trying existing user")
                return self._generate_deterministic_uuid("conv_test_user")
                
        except Exception as e:
            print(f"⚠️ CLI user creation failed: {e}")
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
        
        response = self.send_encrypted_request("POST", "/api/v1/users/authenticate", auth_request)
        
        if response and response.get("success", False):
            self.jwt_token = response.get("jwt_token", "")
            print("✅ Authentication successful")
            return True
        else:
            error_msg = response.get('message', 'Unknown error') if response else 'No response'
            print(f"❌ Authentication failed: {error_msg}")
            return False
    
    def start_conversation(self, initial_message: str = None) -> bool:
        """Start a new conversation thread"""
        print("💬 Starting new conversation...")
        
        request_data = {}
        if initial_message:
            request_data["initial_message"] = initial_message
            request_data["response_mode"] = "text"
        
        response = self.send_encrypted_request("POST", "/api/v1/conversation/start", request_data)
        
        if response and response.get("success", False):
            self.current_thread_id = response.get("thread_id")
            print(f"✅ Conversation started - Thread ID: {self.current_thread_id}")
            if initial_message:
                print(f"📝 Initial message: {initial_message}")
                print(f"🤖 Response: {response.get('response', 'No response')}")
            return True
        else:
            error_msg = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Failed to start conversation: {error_msg}")
            return False
    
    def send_message(self, message: str) -> bool:
        """Send a message to the current conversation thread"""
        if not self.current_thread_id:
            print("❌ No active conversation thread")
            return False
        
        print(f"📤 {message}")
        
        request_data = {"message": message, "response_mode": "text"}
        response = self.send_encrypted_request("POST", f"/api/v1/conversation/message/{self.current_thread_id}", request_data)
        
        if response and response.get("success", False):
            print(f"🤖 {response.get('response', 'No response')}")
            return True
        else:
            error_msg = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Message failed: {error_msg}")
            return False
    
    def get_conversation_status(self) -> bool:
        """Get status of the current conversation"""
        if not self.current_thread_id:
            print("❌ No active conversation thread")
            return False
        
        print("📊 Checking status...")
        response = self.send_encrypted_request("POST", f"/api/v1/conversation/status/{self.current_thread_id}", {})
        
        if response and response.get("success", False):
            status = response.get("status", {})
            print(f"✅ State: {status.get('state', 'unknown')}, Messages: {status.get('message_count', 0)}")
            return True
        else:
            error_msg = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Status failed: {error_msg}")
            return False
    
    def test_conversation_health(self) -> bool:
        """Test conversation health endpoint"""
        print("🏥 Health check...")
        
        # The conversation health endpoint is now POST and encrypted
        try:
            response = self.send_encrypted_request("POST", "/api/v1/conversation/health", {})
            
            if response and response.get("status") == "healthy":
                print("✅ Service healthy")
                return True
            else:
                print("❌ Health check failed")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def cleanup_test_user(self):
        """Clean up test user"""
        if not self.test_user_uuid:
            return
            
        print(f"🧹 Cleaning up test user: {self.test_user_uuid}")
        
        try:
            import os
            
            # Handle Windows encoding issues
            encoding = 'utf-8'
            if platform.system() == 'Windows':
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
            else:
                env = None
            
            result = subprocess.run([
                "uv", "run", "python", "-m", "cli.aico_main", 
                "security", "user-delete", 
                self.test_user_uuid,
                "--hard",  # Permanent deletion for test cleanup
                "--confirm"  # Skip confirmation prompt
            ], 
            cwd=script_dir.parent,
            capture_output=True, 
            text=True,
            encoding=encoding,
            errors='replace',
            timeout=30,
            env=env
            )
            
            if result.returncode == 0:
                print("✅ Test user cleaned up successfully")
            else:
                print(f"⚠️ Test user cleanup failed (exit code {result.returncode})")
                if result.stdout:
                    print(f"   stdout: {result.stdout.strip()}")
                if result.stderr:
                    print(f"   stderr: {result.stderr.strip()}")
                    
        except Exception as e:
            print(f"⚠️ Test user cleanup error: {e}")
        finally:
            self.test_user_uuid = None
    
    def run_conversation_tests(self):
        """Run complete conversation test suite - simplified and focused"""
        print("🚀 AICO Conversation REST API Tests")
        print("=" * 50)
        
        tests = [
            ("Handshake", self.perform_handshake),
            ("Authentication", self.authenticate_user),
            ("Health Check", self.test_conversation_health),
            ("Start Conversation", lambda: self.start_conversation("Hello! Testing conversation system.")),
            ("Send Messages", lambda: self.send_message("How are you today?")),
            ("Get Status", self.get_conversation_status),
            ("New Thread", lambda: self.start_conversation())
        ]
        
        passed = 0
        total = len(tests)
        
        for i, (test_name, test_func) in enumerate(tests, 1):
            print(f"\n{i}️⃣ {test_name}...")
            try:
                if test_func():
                    passed += 1
                else:
                    # Skip dependent tests if core functionality fails
                    if test_name == "Start Conversation" and passed < 3:
                        print("⚠️ Skipping remaining conversation tests due to start failure")
                        break
            except Exception as e:
                print(f"❌ {test_name} error: {e}")
                if test_name in ["Handshake", "Authentication"]:
                    print("⚠️ Core functionality failed, stopping tests")
                    break
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        if passed < total:
            print(f"❌ {total - passed} tests failed")
        
        # Cleanup
        self.cleanup_test_user()
        return passed == total
    
    def _test_message_sequence(self) -> bool:
        """Test sending multiple messages in sequence"""
        messages = ["How are you?", "Tell me about yourself", "What can you help with?"]
        for msg in messages:
            if not self.send_message(msg):
                return False
            time.sleep(0.5)
        return True


def main():
    """Main test function"""
    print("AICO Conversation REST API Test")
    print("Testing encrypted conversation flow")
    print()
    
    # Quick backend check - use unencrypted health endpoint
    try:
        import requests
        response = requests.get("http://127.0.0.1:8771/api/v1/health", timeout=5)
        print(f"✅ Backend responding (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        print("Make sure the AICO backend is running on port 8771")
        return False
    
    return ConversationRESTTester().run_conversation_tests()


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
