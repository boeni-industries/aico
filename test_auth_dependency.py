#!/usr/bin/env python3
"""
Test authentication dependency directly
"""

import requests

# Test credentials
USER_UUID = "49188f6e-50c1-4e05-a0b8-292129f8de15"
PIN = "2375"

# Endpoints
REST_BASE = "http://127.0.0.1:8771/api/v1"

def test_auth_dependency():
    """Test authentication dependency behavior"""
    print("=== TESTING AUTHENTICATION DEPENDENCY ===")
    
    # Test 1: No Authorization header
    print("1. Testing without Authorization header:")
    try:
        resp = requests.get(f"{REST_BASE}/users/{USER_UUID}", timeout=10)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            print("   ERROR: Should require authentication!")
        elif resp.status_code == 401:
            print("   GOOD: Correctly requires authentication")
        elif resp.status_code == 422:
            print("   INFO: FastAPI validation error (dependency not applied)")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Invalid token
    print("\n2. Testing with invalid token:")
    try:
        resp = requests.get(
            f"{REST_BASE}/users/{USER_UUID}",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=10
        )
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 401:
            print("   GOOD: Invalid token rejected")
        else:
            print("   ERROR: Invalid token should be rejected")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 3: Valid token
    print("\n3. Testing with valid token:")
    auth_resp = requests.post(
        f"{REST_BASE}/users/authenticate",
        json={"user_uuid": USER_UUID, "pin": PIN},
        timeout=10
    )
    
    if auth_resp.status_code == 200:
        token = auth_resp.json().get("jwt_token")
        print(f"   Got token: {token[:30]}...")
        
        try:
            resp = requests.get(
                f"{REST_BASE}/users/{USER_UUID}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print("   GOOD: Valid token accepted")
            else:
                print("   ERROR: Valid token should be accepted")
        except Exception as e:
            print(f"   ERROR: {e}")
    else:
        print(f"   Failed to get token: {auth_resp.status_code}")

if __name__ == "__main__":
    test_auth_dependency()
