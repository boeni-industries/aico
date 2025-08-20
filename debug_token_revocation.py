#!/usr/bin/env python3
"""
Debug token revocation issue
"""

import requests
import json

# Test credentials
USER_UUID = "49188f6e-50c1-4e05-a0b8-292129f8de15"
PIN = "2375"

# Endpoints
REST_BASE = "http://127.0.0.1:8771/api/v1"

def debug_token_revocation():
    """Debug token revocation step by step"""
    print("=== DEBUGGING TOKEN REVOCATION ===")
    
    # Step 1: Authenticate and get token
    print("1. Getting fresh token...")
    response = requests.post(
        f"{REST_BASE}/users/authenticate",
        json={"user_uuid": USER_UUID, "pin": PIN},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"Auth failed: {response.status_code}")
        return
    
    data = response.json()
    token = data.get("jwt_token")
    print(f"Token: {token[:30]}...")
    
    # Step 2: Test access before logout
    print("\n2. Testing access before logout...")
    user_response = requests.get(
        f"{REST_BASE}/users/{USER_UUID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Before logout - Status: {user_response.status_code}")
    
    # Step 3: Logout
    print("\n3. Logging out...")
    logout_response = requests.post(
        f"{REST_BASE}/users/logout",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Logout - Status: {logout_response.status_code}")
    
    # Step 4: Test access immediately after logout
    print("\n4. Testing access immediately after logout...")
    immediate_response = requests.get(
        f"{REST_BASE}/users/{USER_UUID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Immediate after logout - Status: {immediate_response.status_code}")
    if immediate_response.status_code != 401:
        print(f"Response: {immediate_response.text[:200]}...")
    
    # Step 5: Wait a moment and test again
    import time
    print("\n5. Waiting 2 seconds and testing again...")
    time.sleep(2)
    delayed_response = requests.get(
        f"{REST_BASE}/users/{USER_UUID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Delayed after logout - Status: {delayed_response.status_code}")
    if delayed_response.status_code != 401:
        print(f"Response: {delayed_response.text[:200]}...")
    
    # Step 6: Test with a different endpoint to rule out caching
    print("\n6. Testing with different endpoint...")
    stats_response = requests.get(
        f"{REST_BASE}/users/stats",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Stats endpoint - Status: {stats_response.status_code}")

if __name__ == "__main__":
    debug_token_revocation()
