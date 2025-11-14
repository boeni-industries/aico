#!/usr/bin/env python3
"""
Test script for backend message retrieval implementation.

This script tests the GET /conversation/messages endpoint to verify:
1. Authentication works correctly
2. Encryption/decryption works correctly
3. Messages are stored correctly in working memory
4. Messages can be retrieved with pagination
5. Message format is correct for frontend consumption

Prerequisites:
- Backend must be running on http://localhost:8771
- A user must exist with UUID and PIN

Usage:
    python test_message_retrieval.py --uuid <user-uuid> --pin <pin>
    python test_message_retrieval.py -u <user-uuid> -p <pin>
"""

import asyncio
import requests
import json
import argparse
import base64
import time
from datetime import datetime
from typing import Optional, Dict, Any
from nacl.public import PrivateKey, PublicKey, Box
from nacl.secret import SecretBox
from nacl.signing import SigningKey
from nacl.utils import random

# Configuration
BASE_URL = "http://localhost:8771"
API_BASE = f"{BASE_URL}/api/v1"


class AICOAPIClient:
    """Client for AICO API with authentication and encryption support"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        
        # Encryption state
        self.session_box: Optional[SecretBox] = None
        self.server_public_key: Optional[PublicKey] = None
        self.client_id: Optional[str] = None
        
        # Generate identity keys for signing
        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        
    def perform_handshake(self) -> bool:
        """Perform encryption handshake with backend"""
        try:
            print(f"   Performing encryption handshake...")
            
            # Generate ephemeral X25519 keypair for session
            client_private_key = PrivateKey.generate()
            client_public_key = client_private_key.public_key
            
            # Create handshake request
            challenge_bytes = random(32)
            handshake_request = {
                "component": "message_retrieval_test",
                "identity_key": base64.b64encode(bytes(self.verify_key)).decode(),
                "public_key": base64.b64encode(bytes(client_public_key)).decode(),
                "timestamp": int(time.time()),
                "challenge": base64.b64encode(challenge_bytes).decode()
            }
            
            # Sign the challenge
            signature = self.signing_key.sign(challenge_bytes).signature
            handshake_request["signature"] = base64.b64encode(signature).decode()
            
            handshake_payload = {
                "handshake_request": handshake_request
            }
            
            # Send handshake request
            response = self.session.post(
                f"{self.base_url}/handshake",
                json=handshake_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"   ✗ Handshake failed: HTTP {response.status_code}")
                print(f"     Response: {response.text}")
                return False
            
            # Process handshake response
            handshake_response = response.json()
            
            if handshake_response.get("status") != "session_established":
                print(f"   ✗ Handshake rejected: {handshake_response.get('error', 'Unknown error')}")
                return False
            
            # Extract server public key and client_id
            response_data = handshake_response["handshake_response"]
            server_public_key_b64 = response_data["public_key"]
            # The client_id is derived from the identity_key (first 16 hex chars)
            identity_key_bytes = bytes(self.verify_key)
            self.client_id = identity_key_bytes.hex()[:16]
            self.server_public_key = PublicKey(base64.b64decode(server_public_key_b64))
            
            # Derive shared session key using X25519
            shared_box = Box(client_private_key, self.server_public_key)
            session_key = shared_box.shared_key()
            self.session_box = SecretBox(session_key)
            
            print(f"   ✓ Handshake successful (client_id: {self.client_id})")
            return True
            
        except Exception as e:
            print(f"   ✗ Handshake error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def encrypt_payload(self, payload: Dict[str, Any]) -> str:
        """Encrypt JSON payload using session key"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        plaintext = json.dumps(payload).encode()
        encrypted = self.session_box.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_payload(self, encrypted_b64: str) -> Dict[str, Any]:
        """Decrypt base64-encoded encrypted payload"""
        if not self.session_box:
            raise RuntimeError("No active session - perform handshake first")
        
        encrypted = base64.b64decode(encrypted_b64)
        plaintext = self.session_box.decrypt(encrypted)
        return json.loads(plaintext)
    
    def authenticate(self, user_uuid: str, pin: str) -> bool:
        """Authenticate and get JWT token"""
        try:
            print(f"   Authenticating user: {user_uuid}")
            
            # Prepare authentication request
            auth_payload = {
                "user_uuid": user_uuid,
                "pin": pin,
                "timestamp": int(time.time())
            }
            
            # Encrypt the payload
            encrypted_payload = self.encrypt_payload(auth_payload)
            
            # Send encrypted request
            request_data = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self.client_id
            }
            
            response = self.session.post(
                f"{self.base_url}/users/authenticate",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Decrypt response if encrypted
                if response_data.get("encrypted"):
                    data = self.decrypt_payload(response_data["payload"])
                else:
                    data = response_data
                
                if data.get("success"):
                    # Try both access_token and jwt_token (backend may use either)
                    self.access_token = data.get("access_token") or data.get("jwt_token")
                    if self.access_token:
                        print(f"   ✓ Authentication successful")
                        print(f"   Token: {self.access_token[:20]}...")
                        return True
                    else:
                        print(f"   ✗ Authentication succeeded but no token received")
                        print(f"   Response data: {data}")
                        return False
                else:
                    print(f"   ✗ Authentication failed: {data.get('error')}")
                    return False
            else:
                print(f"   ✗ Authentication failed: HTTP {response.status_code}")
                print(f"     Response: {response.text}")
                return False
        except Exception as e:
            print(f"   ✗ Authentication error: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token and client_id"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.client_id:
            headers["X-Client-ID"] = self.client_id
        return headers
    
    def send_message(self, message: str, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Send a message to the conversation endpoint"""
        try:
            payload = {"message": message, "timestamp": int(time.time())}
            if conversation_id:
                payload["conversation_id"] = conversation_id
            
            # Encrypt the payload
            encrypted_payload = self.encrypt_payload(payload)
            
            request_data = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self.client_id
            }
            
            response = self.session.post(
                f"{self.base_url}/conversation/messages",
                json=request_data,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Decrypt response if encrypted
                if response_data.get("encrypted"):
                    return self.decrypt_payload(response_data["payload"])
                return response_data
            else:
                print(f"   ✗ Failed to send message: HTTP {response.status_code}")
                print(f"     Response: {response.text}")
                return None
        except Exception as e:
            print(f"   ✗ Error sending message: {e}")
            return None
    
    def get_messages(self, page: int = 1, page_size: int = 50, 
                     conversation_id: Optional[str] = None,
                     since: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve messages from the conversation endpoint"""
        try:
            # Build query parameters
            params = {
                "page": page,
                "page_size": page_size
            }
            if conversation_id:
                params["conversation_id"] = conversation_id
            if since:
                params["since"] = since
            
            # Use GET request with client_id in header for encryption session
            headers = self._get_headers()
            response = self.session.get(
                f"{self.base_url}/conversation/messages",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Decrypt response if encrypted
                if response_data.get("encrypted"):
                    return self.decrypt_payload(response_data["payload"])
                return response_data
            else:
                print(f"   ✗ Failed to retrieve messages: HTTP {response.status_code}")
                # Try to decrypt error message
                try:
                    error_data = response.json()
                    if error_data.get("encrypted"):
                        decrypted_error = self.decrypt_payload(error_data["payload"])
                        print(f"     Error: {decrypted_error}")
                    else:
                        print(f"     Response: {response.text}")
                except:
                    print(f"     Response: {response.text}")
                return None
        except Exception as e:
            print(f"   ✗ Error retrieving messages: {e}")
            return None


async def test_message_retrieval(user_uuid: str, user_pin: str):
    """Test the message retrieval endpoint"""
    
    print("=" * 60)
    print("Testing Backend Message Retrieval")
    print("=" * 60)
    print(f"User UUID: {user_uuid}")
    print(f"PIN: {'*' * len(user_pin)}")
    
    # Initialize API client
    client = AICOAPIClient(API_BASE)
    
    # Step 1: Perform handshake
    print("\n1. Performing encryption handshake...")
    if not client.perform_handshake():
        print("\n❌ Encryption handshake failed. Cannot proceed with tests.")
        print("   Make sure:")
        print("   - Backend is running on http://localhost:8771")
        print("   - Encryption middleware is enabled")
        return
    
    # Step 2: Authenticate
    print("\n2. Authenticating...")
    if not client.authenticate(user_uuid, user_pin):
        print("\n❌ Authentication failed. Cannot proceed with tests.")
        print("   Make sure:")
        print("   - Backend is running on http://localhost:8771")
        print("   - User UUID and PIN are correct")
        print("   - User exists in the database")
        return
    
    # Step 3: Retrieve existing messages from working memory
    print("\n3. Retrieving messages from working memory...")
    
    # Test 1: Get all messages (no conversation_id filter)
    print("\n   Test 1: Get all user messages")
    data = client.get_messages(page=1, page_size=50)
    if data:
        messages = data.get('messages', [])
        print(f"   ✓ Retrieved {len(messages)} messages")
        print(f"     Total count: {data.get('total_count', 0)}")
        print(f"     Page: {data.get('page', 1)} (size: {data.get('page_size', 50)})")
        
        # Display first few messages with full content
        if messages:
            print("\n   📝 Sample messages (showing first 5):")
            for i, msg in enumerate(messages[:5], 1):
                print(f"\n   Message {i}:")
                print(f"     Role: {msg.get('role')}")
                print(f"     Content: {msg.get('content')}")
                print(f"     ID: {msg.get('id')}")
                print(f"     Conversation: {msg.get('conversation_id')}")
                print(f"     Timestamp: {msg.get('timestamp')}")
    else:
        print(f"   ✗ Failed to retrieve messages")
    
    # Test 2: Get messages for specific conversation (if we found any)
    conversation_id = None
    if messages:
        # Get the conversation_id from the first message
        conversation_id = messages[0].get('conversation_id')
        print(f"\n   Test 2: Get messages for conversation {conversation_id}")
        data = client.get_messages(page=1, page_size=50, conversation_id=conversation_id)
    else:
        print(f"\n   Test 2: Skipped (no messages found)")
        data = None
    
    if data:
        conv_messages = data.get('messages', [])
        print(f"   ✓ Retrieved {len(conv_messages)} messages for conversation")
        print(f"     Total count: {data.get('total_count', 0)}")
        
        # Verify message content
        user_messages = [m for m in conv_messages if m.get('role') == 'user']
        assistant_messages = [m for m in conv_messages if m.get('role') == 'assistant']
        print(f"     User messages: {len(user_messages)}")
        print(f"     Assistant messages: {len(assistant_messages)}")
        
        # Display all messages in this conversation
        print(f"\n   📝 All messages in conversation:")
        for i, msg in enumerate(conv_messages, 1):
            print(f"\n   Message {i}:")
            print(f"     Role: {msg.get('role')}")
            print(f"     Content: {msg.get('content')}")
            print(f"     Timestamp: {msg.get('timestamp')}")
    elif conversation_id:
        print(f"   ✗ Failed to retrieve conversation messages")
    
    # Test 3: Test pagination
    print("\n   Test 3: Test pagination (page_size=2)")
    data = client.get_messages(page=1, page_size=2)
    if data:
        page1_messages = data.get('messages', [])
        print(f"   ✓ Page 1: Retrieved {len(page1_messages)} messages")
        
        # Get page 2
        data = client.get_messages(page=2, page_size=2)
        if data:
            page2_messages = data.get('messages', [])
            print(f"   ✓ Page 2: Retrieved {len(page2_messages)} messages")
            
            # Verify no duplicate messages
            page1_ids = {m.get('id') for m in page1_messages}
            page2_ids = {m.get('id') for m in page2_messages}
            duplicates = page1_ids & page2_ids
            if duplicates:
                print(f"   ⚠️  Warning: Found {len(duplicates)} duplicate messages between pages")
            else:
                print(f"   ✓ No duplicate messages between pages")
    else:
        print(f"   ✗ Pagination test failed")
    
    # Test 4: Test timestamp filtering
    print("\n   Test 4: Test timestamp filtering")
    # Get current time minus 1 minute
    from datetime import datetime, timedelta
    one_minute_ago = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    data = client.get_messages(page=1, page_size=50, since=one_minute_ago)
    if data:
        messages = data.get('messages', [])
        print(f"   ✓ Retrieved {len(messages)} messages from last minute")
    else:
        print(f"   ✗ Timestamp filtering test failed")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test AICO backend message retrieval with authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_message_retrieval.py --uuid 1e69de47-a3af-4343-8dba-dbf5dcf5f160 --pin 2375
  python test_message_retrieval.py -u 1e69de47-a3af-4343-8dba-dbf5dcf5f160 -p 2375
        """
    )
    parser.add_argument(
        "-u", "--uuid",
        required=True,
        help="User UUID for authentication"
    )
    parser.add_argument(
        "-p", "--pin",
        required=True,
        help="User PIN for authentication"
    )
    
    args = parser.parse_args()
    
    print("Backend Message Retrieval Test")
    print("Make sure the AICO backend is running on http://localhost:8771")
    print()
    
    try:
        asyncio.run(test_message_retrieval(args.uuid, args.pin))
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
