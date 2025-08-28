#!/usr/bin/env python3
"""
Test script for AICO logs API endpoint
"""

import requests
import json
from datetime import datetime

def test_logs_endpoint():
    """Test the logs API endpoint with a properly formatted frontend log entry"""
    
    # Test data matching frontend log schema
    log_data = {
        "timestamp": "2025-08-23T21:19:54.000Z",
        "level": "INFO",
        "subsystem": "frontend", 
        "module": "logging_service",
        "function": "submit_log",
        "topic": "user_interaction",
        "message": "User logged in successfully",
        "user_id": "user_123",
        "session_id": "session_456", 
        "trace_id": "trace_789",
        "severity": "low",
        "environment": "development",
        "origin": "flutter_app",
        "extra": {
            "platform": "android",
            "app_version": "1.0.0"
        }
    }
    
    try:
        # Test health endpoint first
        print("Testing health endpoint...")
        health_response = requests.get("http://127.0.0.1:8771/api/v1/health/")
        print(f"Health Status: {health_response.status_code}")
        if health_response.status_code == 200:
            print(f"Health Response: {health_response.json()}")
        else:
            print(f"Health Error: {health_response.text}")
        
        print("\n" + "="*50 + "\n")
        
        # Test logs endpoint
        print("Testing logs endpoint...")
        print(f"Sending log data: {json.dumps(log_data, indent=2)}")
        
        response = requests.post(
            "http://127.0.0.1:8771/api/v1/logs/",
            json=log_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Success Response: {response.json()}")
        else:
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to backend server at http://127.0.0.1:8771")
        print("Make sure the backend is running with: python backend/main.py")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_logs_endpoint()
