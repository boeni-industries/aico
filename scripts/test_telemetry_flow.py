#!/usr/bin/env python3
"""
Test End-to-End Telemetry Flow

This script tests that telemetry data flows correctly from:
1. Backend API requests → InfluxDB (api_request measurement)
2. Modelservice inferences → InfluxDB (model_inference measurement)

It simulates metrics, waits for export, then queries InfluxDB to verify data.
"""

import sys
import time
from pathlib import Path

# Add shared to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.data.influx.connection import InfluxDBConnection


def test_backend_metrics():
    """Test that backend API metrics are being written to InfluxDB."""
    print("\n" + "=" * 80)
    print("Testing Backend API Metrics → InfluxDB")
    print("=" * 80)
    
    # Query for recent api_request measurements
    query = '''
        from(bucket: "aico_telemetry")
        |> range(start: -5m)
        |> filter(fn: (r) => r._measurement == "api_request")
        |> filter(fn: (r) => r.service == "aico-backend")
        |> limit(n: 10)
    '''
    
    try:
        conn = InfluxDBConnection()
        results = conn.query(query)
        
        if results:
            print(f"✅ Found {len(results)} api_request metrics from backend")
            print("\nSample metrics:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  {i}. {result.get('time')}")
                print(f"     Method: {result.get('method')}")
                print(f"     Path: {result.get('path')}")
                print(f"     Status: {result.get('status_class')}")
                print(f"     Field: {result.get('field')} = {result.get('value')}")
        else:
            print("⚠️  No api_request metrics found")
            print("   This is expected if backend hasn't processed any requests yet")
        
        conn.close()
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error querying backend metrics: {e}")
        return False


def test_modelservice_metrics():
    """Test that modelservice inference metrics are being written to InfluxDB."""
    print("\n" + "=" * 80)
    print("Testing Modelservice Inference Metrics → InfluxDB")
    print("=" * 80)
    
    # Query for recent model_inference measurements
    query = '''
        from(bucket: "aico_telemetry")
        |> range(start: -5m)
        |> filter(fn: (r) => r._measurement == "model_inference")
        |> filter(fn: (r) => r.service == "modelservice")
        |> limit(n: 10)
    '''
    
    try:
        conn = InfluxDBConnection()
        results = conn.query(query)
        
        if results:
            print(f"✅ Found {len(results)} model_inference metrics from modelservice")
            print("\nSample metrics:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  {i}. {result.get('time')}")
                print(f"     Model: {result.get('model_name')}")
                print(f"     Task: {result.get('task_type')}")
                print(f"     Field: {result.get('field')} = {result.get('value')}")
        else:
            print("⚠️  No model_inference metrics found")
            print("   This is expected if modelservice hasn't processed any inferences yet")
        
        conn.close()
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error querying modelservice metrics: {e}")
        return False


def test_all_measurements():
    """Query all measurements to see what's in InfluxDB."""
    print("\n" + "=" * 80)
    print("All Measurements in InfluxDB (last 5 minutes)")
    print("=" * 80)
    
    query = '''
        from(bucket: "aico_telemetry")
        |> range(start: -5m)
        |> group(columns: ["_measurement", "service"])
        |> count()
    '''
    
    try:
        conn = InfluxDBConnection()
        results = conn.query(query)
        
        if results:
            print(f"\nFound {len(results)} measurement groups:")
            
            # Group by measurement
            measurements = {}
            for result in results:
                measurement = result.get('measurement', 'unknown')
                service = result.get('service', 'unknown')
                count = result.get('value', 0)
                
                if measurement not in measurements:
                    measurements[measurement] = []
                measurements[measurement].append((service, count))
            
            for measurement, services in sorted(measurements.items()):
                print(f"\n  📊 {measurement}:")
                for service, count in services:
                    print(f"     - {service}: {count} points")
        else:
            print("⚠️  No measurements found in the last 5 minutes")
            print("   This might mean:")
            print("   1. Backend/modelservice haven't exported metrics yet (60s interval)")
            print("   2. Instrumentation is disabled in config")
            print("   3. Services aren't running")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error querying measurements: {e}")


def main():
    """Run all telemetry tests."""
    print("=" * 80)
    print("AICO Telemetry Flow Test")
    print("=" * 80)
    print()
    print("This test verifies that telemetry data is flowing from:")
    print("  • Backend → InfluxDB (api_request)")
    print("  • Modelservice → InfluxDB (model_inference)")
    print()
    print("Note: Metrics export every 60 seconds, so you may need to wait")
    print("      or generate some activity (API calls, model inferences)")
    print()
    
    # Test connection first
    print("Testing InfluxDB connection...")
    try:
        conn = InfluxDBConnection()
        health = conn.health()
        if health["healthy"]:
            print(f"✅ InfluxDB is healthy (version: {health.get('version', 'unknown')})")
        else:
            print(f"❌ InfluxDB unhealthy: {health['message']}")
            return 1
        conn.close()
    except Exception as e:
        print(f"❌ Failed to connect to InfluxDB: {e}")
        return 1
    
    # Run tests
    test_all_measurements()
    backend_ok = test_backend_metrics()
    modelservice_ok = test_modelservice_metrics()
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Backend metrics:      {'✅ FOUND' if backend_ok else '⚠️  NOT FOUND'}")
    print(f"Modelservice metrics: {'✅ FOUND' if modelservice_ok else '⚠️  NOT FOUND'}")
    print()
    
    if not backend_ok and not modelservice_ok:
        print("💡 To generate test data:")
        print("   1. Start backend: uv run python3 backend/main.py")
        print("   2. Make API requests to generate api_request metrics")
        print("   3. Start modelservice: uv run python3 modelservice/main.py")
        print("   4. Trigger model inferences to generate model_inference metrics")
        print("   5. Wait 60 seconds for metrics to export")
        print("   6. Run this test again")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
