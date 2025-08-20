#!/usr/bin/env python3
"""
Debug authentication dependency flow
"""

import requests
import json

# Test credentials
USER_UUID = "49188f6e-50c1-4e05-a0b8-292129f8de15"
PIN = "2375"

# Endpoints
REST_BASE = "http://127.0.0.1:8771/api/v1"

def test_dependency_flow():
    """Test if authentication dependency is being called"""
    print("=== DEBUGGING AUTHENTICATION DEPENDENCY FLOW ===")
    
    # Get token
    print("1. Getting fresh token...")
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
    
    # Test different endpoints to see which ones use authentication
    endpoints_to_test = [
        f"/users/{USER_UUID}",
        "/users/",
        "/users/stats",
    ]
    
    print("\n2. Testing endpoints before logout:")
    for endpoint in endpoints_to_test:
        try:
            resp = requests.get(
                f"{REST_BASE}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            print(f"  {endpoint}: {resp.status_code}")
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")
    
    # Logout
    print("\n3. Logging out...")
    logout_response = requests.post(
        f"{REST_BASE}/users/logout",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print(f"Logout status: {logout_response.status_code}")
    
    # Test endpoints after logout
    print("\n4. Testing endpoints after logout:")
    for endpoint in endpoints_to_test:
        try:
            resp = requests.get(
                f"{REST_BASE}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            print(f"  {endpoint}: {resp.status_code}")
            if resp.status_code == 200:
                print(f"    ISSUE: Should be 401, but got 200")
            elif resp.status_code == 401:
                print(f"    GOOD: Correctly rejected")
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")
    
    # Test without Authorization header
    print("\n5. Testing without Authorization header:")
    try:
        resp = requests.get(f"{REST_BASE}/users/{USER_UUID}", timeout=10)
        print(f"  No auth header: {resp.status_code}")
    except Exception as e:
        print(f"  No auth header: ERROR - {e}")

if __name__ == "__main__":
    test_dependency_flow()
