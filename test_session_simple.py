#!/usr/bin/env python3
"""
Simple test to verify session management without CLI complexity
"""
import sys
sys.path.insert(0, '/Users/mbo/Documents/dev/aico/shared')

from aico.security.key_manager import AICOKeyManager

def test_session():
    print("Testing session management...")
    
    key_manager = AICOKeyManager()
    
    # Check if session exists
    session_info = key_manager.get_session_info()
    print(f"Session active: {session_info['active']}")
    
    if session_info['active']:
        print(f"Time remaining: {session_info['time_remaining_minutes']} minutes")
        
        # Test getting cached session directly
        cached_key = key_manager._get_cached_session()
        print(f"Cached key available: {'Yes' if cached_key else 'No'}")
        
        if cached_key:
            print(f"Key length: {len(cached_key)} bytes")
            
            # Test authentication without interactive prompt
            try:
                master_key = key_manager.authenticate(interactive=False)
                print("✅ Authentication successful using session!")
                return True
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
    else:
        print("No active session")
        return False

if __name__ == "__main__":
    success = test_session()
    sys.exit(0 if success else 1)
