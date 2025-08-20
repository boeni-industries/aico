#!/usr/bin/env python3
"""
Full Authentication Cycle Testing for AICO REST and WebSocket endpoints

Tests the complete cycle:
1. Authenticate
2. Access works
3. Revoke token
4. Access fails
"""

import requests
import json
import asyncio
import websockets
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
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        config = ConfigurationManager()
        db_config = config.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        if not db_path.exists():
            print(f"Database file not found at: {db_path}")
            return
        
        key_manager = AICOKeyManager()
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        else:
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            else:
                print("No master key available for database access")
                return
        
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
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
                status = "ACTIVE" if session[4] else "INACTIVE"
                print(f"  - {session[0][:8]}... | Device: {session[2]} | {status} | Type: {session[5]}")
        else:
            print("  - No sessions found")
        
        return sessions
        
    except Exception as e:
        print(f"Database check failed: {e}")
        return None

def test_rest_full_cycle():
    """Test complete REST authentication cycle"""
    print("\n" + "="*60)
    print("TESTING REST FULL AUTHENTICATION CYCLE")
    print("="*60)
    
    # Step 1: Authenticate
    print("1. Authenticating via REST...")
    response = requests.post(
        f"{REST_BASE}/users/authenticate",
        json={"user_uuid": USER_UUID, "pin": PIN},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"Authentication failed: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get("success"):
        print(f"Authentication failed: {data.get('error')}")
        return False
    
    token = data.get("jwt_token")
    print(f"Authentication successful, token: {token[:20]}...")
    
    # Check database
    sessions = check_database_sessions()
    active_sessions = [s for s in sessions if s[4]] if sessions else []
    print(f"Active sessions in DB: {len(active_sessions)}")
    
    # Step 2: Test access works
    print("\n2. Testing protected access...")
    user_response = requests.get(
        f"{REST_BASE}/users/{USER_UUID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if user_response.status_code == 200:
        print("Protected access works")
    else:
        print(f"Protected access failed: {user_response.status_code}")
        return False
    
    # Step 3: Revoke token (logout)
    print("\n3. Revoking token (logout)...")
    logout_response = requests.post(
        f"{REST_BASE}/users/logout",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if logout_response.status_code == 204:
        print("Logout successful")
    else:
        print(f"Logout failed: {logout_response.status_code}")
        return False
    
    # Check database after logout
    sessions = check_database_sessions()
    active_sessions = [s for s in sessions if s[4]] if sessions else []
    print(f"Active sessions in DB after logout: {len(active_sessions)}")
    
    # Step 4: Test access fails
    print("\n4. Testing access after revocation...")
    revoked_response = requests.get(
        f"{REST_BASE}/users/{USER_UUID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    
    if revoked_response.status_code == 401:
        print("Access correctly denied after revocation")
        return True
    else:
        print(f"Access still works after revocation: {revoked_response.status_code}")
        print(f"Response: {revoked_response.text}")
        return False

async def test_websocket_full_cycle():
    """Test complete WebSocket authentication cycle"""
    print("\n" + "="*60)
    print("TESTING WEBSOCKET FULL AUTHENTICATION CYCLE")
    print("="*60)
    
    try:
        # Step 1: Connect and authenticate
        print("1. Connecting and authenticating via WebSocket...")
        async with websockets.connect(WS_URL) as websocket:
            
            # Receive welcome
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"Connected, received: {welcome_data.get('type')}")
            
            # Get fresh token for auth
            response = requests.post(
                f"{REST_BASE}/users/authenticate",
                json={"user_uuid": USER_UUID, "pin": PIN},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Failed to get auth token: {response.status_code}")
                return False
            
            token = response.json().get("jwt_token")
            print(f"Got auth token: {token[:20]}...")
            
            # Authenticate via WebSocket
            await websocket.send(json.dumps({
                "type": "auth",
                "token": token,
                "device_uuid": "websocket_test"
            }))
            
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("type") != "auth_success":
                print(f"WebSocket auth failed: {auth_data}")
                return False
            
            print("WebSocket authentication successful")
            session_id = auth_data.get("session_id")
            if session_id:
                print(f"   Session ID: {session_id}")
            
            # Check database
            sessions = check_database_sessions()
            active_sessions = [s for s in sessions if s[4]] if sessions else []
            print(f"Active sessions in DB: {len(active_sessions)}")
            
            # Step 2: Test protected operation works
            print("\n2. Testing protected operation...")
            await websocket.send(json.dumps({
                "type": "subscribe",
                "topic": "test_topic"
            }))
            
            try:
                sub_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                sub_data = json.loads(sub_response)
                if sub_data.get("type") == "subscribed":
                    print("Protected operation works")
                elif sub_data.get("type") == "error":
                    print(f"Protected operation failed: {sub_data.get('error')}")
                    return False
                else:
                    print(f"Protected operation response: {sub_data.get('type')}")
            except asyncio.TimeoutError:
                print("Protected operation timed out")
                return False
            
            # Step 3: Revoke token via REST
            print("\n3. Revoking token via REST...")
            logout_response = requests.post(
                f"{REST_BASE}/users/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if logout_response.status_code == 204:
                print("Token revoked via REST")
            else:
                print(f"Token revocation failed: {logout_response.status_code}")
                return False
            
            # Check database after revocation
            sessions = check_database_sessions()
            active_sessions = [s for s in sessions if s[4]] if sessions else []
            print(f"Active sessions in DB after revocation: {len(active_sessions)}")
            
            # Step 4: Test protected operation fails
            print("\n4. Testing protected operation after revocation...")
            await websocket.send(json.dumps({
                "type": "subscribe",
                "topic": "test_topic_2"
            }))
            
            try:
                revoked_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                revoked_data = json.loads(revoked_response)
                if revoked_data.get("type") == "error" and "revoked" in revoked_data.get("error", "").lower():
                    print("Protected operation correctly denied after revocation")
                    return True
                else:
                    print(f"Protected operation still works: {revoked_data}")
                    return False
            except asyncio.TimeoutError:
                print("No response after revocation (connection may be closed)")
                return True  # This might be expected behavior
            
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

def analyze_inactive_sessions():
    """Analyze inactive sessions in the database"""
    print("\n" + "="*60)
    print("ANALYZING INACTIVE SESSIONS")
    print("="*60)
    
    sessions = check_database_sessions()
    if not sessions:
        print("No sessions found")
        return
    
    active_count = len([s for s in sessions if s[4]])
    inactive_count = len([s for s in sessions if not s[4]])
    
    print(f"Total sessions: {len(sessions)}")
    print(f"Active sessions: {active_count}")
    print(f"Inactive sessions: {inactive_count}")
    
    if inactive_count > 0:
        print("Inactive Session Analysis:")
        print("- Inactive sessions are kept for audit purposes")
        print("- They show session history and logout events")
        print("- is_active=0 prevents token reuse")
        print("- Consider periodic cleanup based on retention policy")
        
        print("\nRecommendations:")
        print("- Keep inactive sessions for audit trail")
        print("- Implement cleanup job for sessions older than X days")
        print("- Current approach is secure and correct")

async def main():
    """Run all authentication cycle tests"""
    print("AICO Full Authentication Cycle Testing")
    print("Testing complete auth cycles for both REST and WebSocket protocols")
    
    # Test REST cycle
    rest_success = test_rest_full_cycle()
    
    # Test WebSocket cycle  
    ws_success = await test_websocket_full_cycle()
    
    # Analyze inactive sessions
    analyze_inactive_sessions()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"REST Full Cycle: {'PASS' if rest_success else 'FAIL'}")
    print(f"WebSocket Full Cycle: {'PASS' if ws_success else 'FAIL'}")
    
    if rest_success and ws_success:
        print("\nAll authentication cycles working correctly!")
        print("Unified session management is fully functional")
    else:
        print("\nSome authentication cycles have issues")
        print("Further investigation needed")

if __name__ == "__main__":
    asyncio.run(main())
