#!/usr/bin/env python3
"""
Debug script to trace authentication flow
"""
import sys
import os
sys.path.insert(0, '/Users/mbo/Documents/dev/aico/shared')

from aico.security.key_manager import AICOKeyManager
import json

def debug_authentication():
    print("🔧 Debugging Authentication Flow")
    print("=" * 50)
    
    key_manager = AICOKeyManager()
    
    # Check session cache file directly
    print(f"1. Session cache file: {key_manager._session_cache_file}")
    print(f"   File exists: {key_manager._session_cache_file.exists()}")
    
    if key_manager._session_cache_file.exists():
        with open(key_manager._session_cache_file, 'r') as f:
            cache_content = json.load(f)
        print(f"   Cache content: {cache_content}")
    
    # Check in-memory cache
    print(f"2. In-memory cache: {key_manager._session_cache}")
    
    # Test session retrieval
    print("3. Testing _get_cached_session()...")
    try:
        cached_session = key_manager._get_cached_session()
        print(f"   Result: {'Found' if cached_session else 'None'}")
        if cached_session:
            print(f"   Key length: {len(cached_session)} bytes")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test session info
    print("4. Testing get_session_info()...")
    try:
        session_info = key_manager.get_session_info()
        print(f"   Active: {session_info['active']}")
        if session_info['active']:
            print(f"   Time remaining: {session_info['time_remaining_minutes']} minutes")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test authenticate with debugging
    print("5. Testing authenticate() flow...")
    try:
        # First check if it would use session
        cached_key = key_manager._get_cached_session()
        print(f"   Cached session available: {'Yes' if cached_key else 'No'}")
        
        if not cached_key:
            # Check stored key
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            print(f"   Stored key available: {'Yes' if stored_key else 'No'}")
            
    except Exception as e:
        print(f"   Error during authenticate flow: {e}")

if __name__ == "__main__":
    debug_authentication()
