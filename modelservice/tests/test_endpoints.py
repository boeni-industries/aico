#!/usr/bin/env python3
"""
Simple test script for modelservice endpoints.
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_health_endpoint():
    """Test the health check endpoint."""
    print("Testing /api/v1/health endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0.1:8773/api/v1/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False


async def test_models_endpoint():
    """Test the models list endpoint."""
    print("\nTesting /api/v1/models endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0.1:8773/api/v1/models")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code in [200, 502, 503]  # 502/503 if Ollama not running
        except Exception as e:
            print(f"Error: {e}")
            return False


async def test_completions_endpoint():
    """Test the completions endpoint."""
    print("\nTesting /api/v1/completions endpoint...")
    
    test_request = {
        "model": "llama3.2",
        "prompt": "Hello, how are you?",
        "parameters": {
            "max_tokens": 50,
            "temperature": 0.7
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8773/api/v1/completions",
                json=test_request
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code in [200, 502, 503]  # 502/503 if Ollama not running
        except Exception as e:
            print(f"Error: {e}")
            return False


async def main():
    """Run all endpoint tests."""
    print("=" * 50)
    print("AICO Modelservice Endpoint Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Models List", test_models_endpoint),
        ("Completions", test_completions_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        success = await test_func()
        results.append((test_name, success))
        print(f"✅ {test_name}: {'PASS' if success else 'FAIL'}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\nNote: Some failures may be expected if Ollama is not running.")


if __name__ == "__main__":
    asyncio.run(main())
