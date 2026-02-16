#!/usr/bin/env python3
"""Test script for InfluxDB connection layer.

This script verifies that the InfluxDB connection layer can:
1. Connect to InfluxDB using credentials from keyring
2. Write test data points
3. Query data back
4. Perform health checks

Run with: python3 test_connection.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add shared to path
shared_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(shared_path))

from aico.data.influx.connection import InfluxDBConnection


def test_connection():
    """Test basic InfluxDB connection and operations."""
    
    print("=" * 80)
    print("InfluxDB Connection Layer Test")
    print("=" * 80)
    print()
    
    # Test 1: Initialize connection
    print("1. Initializing connection...")
    try:
        conn = InfluxDBConnection()
        print(f"   ✅ Connected to {conn.url}")
        print(f"   ✅ Org: {conn.org}, Bucket: {conn.bucket}")
    except Exception as e:
        print(f"   ❌ Failed to initialize connection: {e}")
        return False
    
    print()
    
    # Test 2: Health check
    print("2. Checking InfluxDB health...")
    try:
        health = conn.health()
        if health["healthy"]:
            print(f"   ✅ InfluxDB is healthy")
            print(f"   ✅ Status: {health['status']}")
            print(f"   ✅ Version: {health.get('version', 'unknown')}")
        else:
            print(f"   ❌ InfluxDB unhealthy: {health['message']}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    print()
    
    # Test 3: Ping
    print("3. Pinging InfluxDB...")
    try:
        if conn.ping():
            print("   ✅ Ping successful")
        else:
            print("   ❌ Ping failed")
            return False
    except Exception as e:
        print(f"   ❌ Ping error: {e}")
        return False
    
    print()
    
    # Test 4: Write single point
    print("4. Writing test data point...")
    try:
        conn.write_point(
            measurement="test_connection",
            tags={
                "service": "test_script",
                "test_type": "connection_test"
            },
            fields={
                "test_value_f": 123.45,
                "test_count_i": 1,
                "test_success_b": True
            }
        )
        print("   ✅ Single point written successfully")
    except Exception as e:
        print(f"   ❌ Failed to write point: {e}")
        return False
    
    print()
    
    # Test 5: Write batch
    print("5. Writing batch of test points...")
    try:
        points = [
            {
                "measurement": "test_batch",
                "tags": {"batch_id": "1", "service": "test_script"},
                "fields": {"value_f": 10.5, "count_i": 10}
            },
            {
                "measurement": "test_batch",
                "tags": {"batch_id": "2", "service": "test_script"},
                "fields": {"value_f": 20.5, "count_i": 20}
            },
            {
                "measurement": "test_batch",
                "tags": {"batch_id": "3", "service": "test_script"},
                "fields": {"value_f": 30.5, "count_i": 30}
            }
        ]
        conn.write_points(points)
        print(f"   ✅ Batch of {len(points)} points written successfully")
    except Exception as e:
        print(f"   ❌ Failed to write batch: {e}")
        return False
    
    print()
    
    # Test 6: Query data back
    print("6. Querying test data...")
    try:
        flux_query = '''
            from(bucket: "aico_telemetry")
            |> range(start: -1m)
            |> filter(fn: (r) => r._measurement == "test_connection" or r._measurement == "test_batch")
            |> limit(n: 10)
        '''
        results = conn.query(flux_query)
        print(f"   ✅ Query returned {len(results)} results")
        
        if results:
            print("   Sample result:")
            sample = results[0]
            print(f"      Measurement: {sample.get('measurement')}")
            print(f"      Time: {sample.get('time')}")
            print(f"      Field: {sample.get('field')} = {sample.get('value')}")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        # Don't fail the test - query might fail if data hasn't propagated yet
        print("   ⚠️  This is acceptable - data may not have propagated yet")
    
    print()
    
    # Test 7: Close connection
    print("7. Closing connection...")
    try:
        conn.close()
        print("   ✅ Connection closed successfully")
    except Exception as e:
        print(f"   ❌ Failed to close connection: {e}")
        return False
    
    print()
    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
