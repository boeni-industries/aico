#!/usr/bin/env python3
"""
Debug session service integration
"""

import requests
import json

# Test credentials
USER_UUID = "49188f6e-50c1-4e05-a0b8-292129f8de15"
PIN = "2375"

# Endpoints
REST_BASE = "http://127.0.0.1:8771/api/v1"

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
            SELECT uuid, user_uuid, device_uuid, expires_at, is_active, session_type, jwt_token_hash
            FROM auth_sessions 
            WHERE user_uuid = ? 
            ORDER BY created_at DESC
            LIMIT 5
        """, (USER_UUID,))
        
        sessions = cursor.fetchall()
        print(f"Database sessions for user {USER_UUID}:")
        if sessions:
            for session in sessions:
                status = "ACTIVE" if session[4] else "INACTIVE"
                print(f"  - {session[0][:8]}... | Device: {session[2]} | {status} | Type: {session[5]} | Hash: {session[6][:16]}...")
        else:
            print("  - No sessions found")
        
        return sessions
        
    except Exception as e:
        print(f"Database check failed: {e}")
        return None

def test_session_service_directly():
    """Test SessionService directly"""
    try:
        from aico.security.session_service import SessionService
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        # Get database connection
        config = ConfigurationManager()
        db_config = config.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
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
                print("No master key available")
                return
        
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        session_service = SessionService(conn)
        
        # Get a token first
        print("Getting fresh token...")
        response = requests.post(
            f"{REST_BASE}/users/authenticate",
            json={"user_uuid": USER_UUID, "pin": PIN},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"Auth failed: {response.status_code}")
            return
        
        token = response.json().get("jwt_token")
        print(f"Token: {token[:30]}...")
        
        # Test session service methods
        print("\nTesting SessionService.get_session_by_token()...")
        session_info = session_service.get_session_by_token(token)
        if session_info:
            print(f"Session found: {session_info.uuid}, active: {session_info.is_active}")
        else:
            print("Session NOT found in database!")
        
        # Logout via REST
        print("\nLogging out via REST...")
        logout_response = requests.post(
            f"{REST_BASE}/users/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"Logout status: {logout_response.status_code}")
        
        # Test session service after logout
        print("\nTesting SessionService.get_session_by_token() after logout...")
        session_info_after = session_service.get_session_by_token(token)
        if session_info_after:
            print(f"Session found after logout: {session_info_after.uuid}, active: {session_info_after.is_active}")
        else:
            print("Session NOT found after logout (expected)")
        
    except Exception as e:
        print(f"SessionService test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=== DEBUGGING SESSION SERVICE INTEGRATION ===")
    
    print("\n1. Checking database sessions:")
    check_database_sessions()
    
    print("\n2. Testing SessionService directly:")
    test_session_service_directly()
    
    print("\n3. Final database check:")
    check_database_sessions()

if __name__ == "__main__":
    main()
