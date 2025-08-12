#!/usr/bin/env python3
"""
Quick authentication test for admin endpoints
"""
import requests
import jwt
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aico.security import AICOKeyManager

def create_admin_token():
    """Create a valid admin JWT token"""
    try:
        # Initialize key manager
        key_manager = AICOKeyManager()
        
        # Get JWT secret (same as auth manager uses)
        jwt_secret = key_manager.get_jwt_secret()
        
        # Create admin token payload
        payload = {
            "sub": "test_admin",
            "username": "test_admin", 
            "roles": ["admin"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Generate token
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return token
        
    except Exception as e:
        print(f"Failed to create admin token: {e}")
        return None

def test_endpoint_without_auth():
    """Test endpoint without authentication"""
    print("🔒 Testing WITHOUT authentication...")
    try:
        response = requests.get("http://localhost:8771/admin/auth/sessions", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 403
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_endpoint_with_auth(token):
    """Test endpoint with authentication"""
    print("\n🔑 Testing WITH authentication...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8771/admin/auth/sessions", headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Admin Endpoint Authentication Test")
    print("=" * 40)
    
    # Test 1: Without auth (should fail)
    no_auth_works = test_endpoint_without_auth()
    
    # Test 2: With auth (should work)  
    print("\n📝 Creating admin JWT token...")
    token = create_admin_token()
    
    if not token:
        print("❌ Failed to create token")
        sys.exit(1)
    
    print(f"✅ Token created: {token[:50]}...")
    
    auth_works = test_endpoint_with_auth(token)
    
    # Results
    print("\n📊 Test Results:")
    print("=" * 40)
    print(f"❌ No auth (should fail): {'✅ PASS' if no_auth_works else '❌ FAIL'}")
    print(f"🔑 With auth (should work): {'✅ PASS' if auth_works else '❌ FAIL'}")
    
    if no_auth_works and auth_works:
        print("\n🎉 All tests passed! Authentication is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")
