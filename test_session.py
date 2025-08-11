#!/usr/bin/env python3
"""
Test script to verify session management functionality
"""
import sys
import os
sys.path.insert(0, '/Users/mbo/Documents/dev/aico/shared')

from aico.security.key_manager import AICOKeyManager
from datetime import datetime
import time

def test_session_management():
    print("🔧 Testing Session Management")
    print("=" * 50)
    
    # Create key manager instance
    key_manager = AICOKeyManager()
    
    # Test 1: Check if master key is set up
    print(f"1. Master key setup: {'✅' if key_manager.has_stored_key() else '❌'}")
    
    if not key_manager.has_stored_key():
        print("   Please run 'aico security setup' first")
        return
    
    # Test 2: Check initial session status
    session_info = key_manager.get_session_info()
    print(f"2. Initial session active: {'✅' if session_info['active'] else '❌'}")
    
    # Test 3: Authenticate (should use session if available)
    print("3. Testing authentication...")
    try:
        master_key = key_manager.authenticate(interactive=False)
        print("   ✅ Authentication successful (using session or stored key)")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return
    
    # Test 4: Check session status after authentication
    session_info = key_manager.get_session_info()
    print(f"4. Session active after auth: {'✅' if session_info['active'] else '❌'}")
    
    if session_info['active']:
        print(f"   Created: {session_info['created_at']}")
        print(f"   Last accessed: {session_info['last_accessed']}")
        print(f"   Time remaining: {session_info['time_remaining_minutes']} minutes")
    
    # Test 5: Create new key manager instance (simulates new CLI command)
    print("5. Testing session persistence across instances...")
    key_manager2 = AICOKeyManager()
    session_info2 = key_manager2.get_session_info()
    print(f"   Session persists: {'✅' if session_info2['active'] else '❌'}")
    
    # Test 6: Test session extension
    if session_info2['active']:
        print("6. Testing session extension...")
        old_last_accessed = session_info2['last_accessed']
        time.sleep(1)  # Wait a second
        key_manager2._extend_session()
        session_info3 = key_manager2.get_session_info()
        new_last_accessed = session_info3['last_accessed']
        print(f"   Session extended: {'✅' if new_last_accessed > old_last_accessed else '❌'}")
    
    print("\n🎉 Session management test completed!")

if __name__ == "__main__":
    test_session_management()
