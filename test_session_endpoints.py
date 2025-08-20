#!/usr/bin/env python3
"""
End-to-end session management testing for AICO REST and WebSocket endpoints
"""

import requests
import json
import asyncio
import websockets
import sqlite3
from pathlib import Path

# Test credentials
USER_UUID = "49188f6e-50c1-4e05-a0b8-292129f8de15"
PIN = "2375"

# Endpoints
REST_BASE = "http://127.0.0.1:8771/api/v1"
WS_URL = "ws://127.0.0.1:8772/ws"

def check_database_sessions():
    """Check auth_sessions table in database"""
    try:
        # Use proper AICO path resolution like CLI commands
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        
        config = ConfigurationManager()
        db_config = config.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        if not db_path.exists():
            print(f"Database file not found at: {db_path}")
            return
        
        # Use encrypted connection like CLI commands
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        key_manager = AICOKeyManager()
        
        # Try session-based authentication first
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        else:
            # Try stored key from keyring
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            else:
                print("No master key available for database access")
                return
        
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # Query sessions
        cursor = conn.execute("""
            SELECT uuid, user_uuid, device_uuid, expires_at, is_active, session_type 
            FROM auth_sessions 
            WHERE user_uuid = ? 
            ORDER BY created_at DESC
        """, (USER_UUID,))
        
        sessions = cursor.fetchall()
        print(f"\nDatabase sessions for user {USER_UUID}:")
        if sessions:
            for session in sessions:
                print(f"  - Session: {session[0][:8]}... | Device: {session[2]} | Active: {session[4]} | Type: {session[5]}")
        else:
            print("  - No sessions found")
        
        # No close() method needed for EncryptedLibSQLConnection
        return len([s for s in sessions if s[4]])  # Count active sessions
        
    except Exception as e:
        print(f"Database check failed: {e}")
        return None

def test_rest_flow():
    """Test REST authentication flow"""
    print("\nTesting REST Flow...")
    
    # Step 1: Authenticate
    print("1. Authenticating via REST...")
    try:
        response = requests.post(
            f"{REST_BASE}/users/authenticate",
            json={"user_uuid": USER_UUID, "pin": PIN},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                token = data.get("jwt_token")
                print(f"Authentication successful, token: {token[:20]}...")
                
                # Step 2: Check database
                print("2. Checking database for session...")
                active_sessions = check_database_sessions()
                
                # Step 3: Validate token works
                print("3. Testing token validation...")
                user_response = requests.get(
                    f"{REST_BASE}/users/{USER_UUID}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                
                if user_response.status_code == 200:
                    print("Token validation successful")
                else:
                    print(f"Token validation failed: {user_response.status_code}")
                
                # Step 4: Logout
                print("4. Logging out...")
                logout_response = requests.post(
                    f"{REST_BASE}/users/logout",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                
                if logout_response.status_code == 204:
                    print("Logout successful")
                    
                    # Step 5: Check database after logout
                    print("5. Checking database after logout...")
                    check_database_sessions()
                    
                    # Step 6: Try to use revoked token
                    print("6. Testing revoked token...")
                    revoked_response = requests.get(
                        f"{REST_BASE}/users/{USER_UUID}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                    
                    if revoked_response.status_code == 401:
                        print("Revoked token correctly rejected")
                    else:
                        print(f"Revoked token still works: {revoked_response.status_code}")
                        
                else:
                    print(f"Logout failed: {logout_response.status_code}")
                    
                return token
            else:
                print(f"Authentication failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"Authentication request failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"REST flow failed: {e}")
    
    return None

async def test_websocket_flow(token=None):
    """Test WebSocket authentication flow"""
    print("\nTesting WebSocket Flow...")
    
    try:
        # Connect to WebSocket
        print("1. Connecting to WebSocket...")
        async with websockets.connect(WS_URL) as websocket:
            
            # Receive welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"Connected, received: {welcome_data.get('type', 'unknown')}")
            
            # Authenticate
            print("2. Authenticating via WebSocket...")
            if token:
                # Get a fresh token for WebSocket auth
                print("   Getting fresh token for WebSocket...")
                response = requests.post(
                    f"{REST_BASE}/users/authenticate",
                    json={"user_uuid": USER_UUID, "pin": PIN},
                    timeout=10
                )
                if response.status_code == 200:
                    fresh_token = response.json().get("jwt_token")
                    print(f"   Fresh token obtained: {fresh_token[:20]}...")
                    
                    # Authenticate via WebSocket with fresh token
                    await websocket.send(json.dumps({
                        "type": "auth",
                        "token": fresh_token,
                        "device_uuid": "websocket_test"
                    }))
                else:
                    print(f"   Failed to get fresh token: {response.status_code}")
                    # Try direct auth
                    await websocket.send(json.dumps({
                        "type": "auth",
                        "user_uuid": USER_UUID,
                        "pin": PIN,
                        "device_uuid": "websocket_test"
                    }))
            else:
                # Direct auth (if supported)
                await websocket.send(json.dumps({
                    "type": "auth",
                    "user_uuid": USER_UUID,
                    "pin": PIN,
                    "device_uuid": "websocket_test"
                }))
            
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("type") == "auth_success":
                print(f"WebSocket authentication successful")
                session_id = auth_data.get("session_id")
                if session_id:
                    print(f"   Session ID: {session_id}")
                
                # Check database
                print("3. Checking database for WebSocket session...")
                check_database_sessions()
                
                # Test a protected operation
                print("4. Testing protected operation (subscribe)...")
                subscribe_msg = {
                    "type": "subscribe",
                    "topic": "test_topic"
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                try:
                    sub_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    sub_data = json.loads(sub_response)
                    if sub_data.get("type") == "subscribed":
                        print("Protected operation successful")
                    else:
                        print(f"Protected operation failed: {sub_data}")
                except asyncio.TimeoutError:
                    print("Protected operation timed out")
                
            else:
                print(f"WebSocket authentication failed: {auth_data}")
            
            print("5. Closing WebSocket connection...")
            
        # Check database after disconnect
        print("6. Checking database after WebSocket disconnect...")
        check_database_sessions()
            
    except Exception as e:
        print(f"WebSocket flow failed: {e}")

async def main():
    """Run all tests"""
    print("Starting AICO Session Management End-to-End Tests")
    print("=" * 60)
    
    # Initial database check
    print("Initial database state:")
    check_database_sessions()
    
    # Test REST flow
    token = test_rest_flow()
    
    # Test WebSocket flow
    await test_websocket_flow(token)
    
    print("\n" + "=" * 60)
    print("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
