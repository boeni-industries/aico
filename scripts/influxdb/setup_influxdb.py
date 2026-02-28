#!/usr/bin/env python3
"""
InfluxDB Setup Script for AICO
Creates downsampled bucket, sets up retention policies, and creates downsampling tasks.
Run this once to optimize InfluxDB for dashboard performance.
"""

import os
import sys
from influxdb_client import InfluxDBClient, BucketRetentionRules
from influxdb_client.client.tasks_api import TasksApi
from aico.security import AICOKeyManager
from aico.core.config import ConfigurationManager

def setup_influxdb():
    """Set up InfluxDB buckets, retention policies, and downsampling tasks."""
    
    # Load configuration
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    url = config.get_optional("influx.url") or "http://127.0.0.1:8086"
    org = config.get_optional("influx.org") or "aico"
    
    # Get token from environment first (container-friendly), then key manager
    token = os.getenv("AICO_INFLUX_ADMIN_TOKEN")
    if not token:
        key_manager = AICOKeyManager(config)
        token = key_manager.get_database_password("influx", username="admin_token")
    
    print(f"Connecting to InfluxDB at {url}...")
    
    with InfluxDBClient(url=url, token=token, org=org) as client:
        # Resolve organization (Tasks API expects an Organization object)
        orgs = client.organizations_api().find_organizations(org=org)
        if not orgs:
            raise RuntimeError(f"InfluxDB organization '{org}' not found")
        org_obj = orgs[0]

        # Get APIs
        buckets_api = client.buckets_api()
        tasks_api = client.tasks_api()
        
        # ========================================================================
        # Step 1: Create downsampled bucket with 30-day retention
        # ========================================================================
        print("\n[1/4] Creating downsampled bucket...")
        
        downsampled_bucket_name = "aico_telemetry_downsampled"
        existing_buckets = buckets_api.find_buckets().buckets
        
        downsampled_bucket = None
        for bucket in existing_buckets:
            if bucket.name == downsampled_bucket_name:
                downsampled_bucket = bucket
                print(f"  ✓ Bucket '{downsampled_bucket_name}' already exists")
                break
        
        if not downsampled_bucket:
            # 30 days = 720 hours = 2,592,000 seconds
            retention_rules = BucketRetentionRules(type="expire", every_seconds=2592000)
            downsampled_bucket = buckets_api.create_bucket(
                bucket_name=downsampled_bucket_name,
                org=org,
                retention_rules=retention_rules
            )
            print(f"  ✓ Created bucket '{downsampled_bucket_name}' with 30-day retention")
        
        # ========================================================================
        # Step 2: Update main bucket to 7-day retention
        # ========================================================================
        print("\n[2/4] Updating main bucket retention policy...")
        
        main_bucket_name = "aico_telemetry"
        main_bucket = None
        for bucket in existing_buckets:
            if bucket.name == main_bucket_name:
                main_bucket = bucket
                break
        
        if main_bucket:
            # 7 days = 168 hours = 604,800 seconds
            main_bucket.retention_rules = [BucketRetentionRules(type="expire", every_seconds=604800)]
            buckets_api.update_bucket(bucket=main_bucket)
            print(f"  ✓ Updated '{main_bucket_name}' to 7-day retention")
        else:
            print(f"  ⚠ Warning: Main bucket '{main_bucket_name}' not found")
        
        # ========================================================================
        # Step 3: Create downsampling tasks
        # ========================================================================
        print("\n[3/4] Creating downsampling tasks...")
        
        tasks = [
            {
                "name": "downsample_api_requests",
                "flux": """
option task = {name: "downsample_api_requests", every: 1m, offset: 10s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "api_request")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "status_code_i")
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "api_request_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            },
            {
                "name": "downsample_api_counts",
                "flux": """
option task = {name: "downsample_api_counts", every: 1m, offset: 15s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "api_request")
    |> filter(fn: (r) => r._field == "status_code_i")
    |> aggregateWindow(every: 1m, fn: count, createEmpty: false)
    |> set(key: "_measurement", value: "api_request_counts_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            },
            {
                "name": "downsample_messagebus",
                "flux": """
option task = {name: "downsample_messagebus", every: 1m, offset: 20s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "messagebus_event")
    |> filter(fn: (r) => r._field == "message_count_i" or r._field == "latency_ms_i")
    |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
    |> set(key: "_measurement", value: "messagebus_event_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            },
            {
                "name": "downsample_scheduler",
                "flux": """
option task = {name: "downsample_scheduler", every: 1m, offset: 25s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "scheduler_job")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "success_b")
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "scheduler_job_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            },
            {
                "name": "downsample_memory_queries",
                "flux": """
option task = {name: "downsample_memory_queries", every: 1m, offset: 30s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "memory_query")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "result_count_i")
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "memory_query_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            },
            {
                "name": "downsample_model_inference",
                "flux": """
option task = {name: "downsample_model_inference", every: 1m, offset: 35s}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "model_inference")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "token_count_i")
    |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "model_inference_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
"""
            }
        ]
        
        # Get existing tasks
        existing_tasks = tasks_api.find_tasks()
        existing_task_names = {task.name for task in existing_tasks}
        
        for task_def in tasks:
            task_name = task_def["name"]
            if task_name in existing_task_names:
                print(f"  ✓ Task '{task_name}' already exists")
            else:
                tasks_api.create_task_every(
                    name=task_name,
                    flux=task_def["flux"],
                    every="1m",
                    organization=org_obj,
                )
                print(f"  ✓ Created task '{task_name}'")
        
        # ========================================================================
        # Step 4: Summary
        # ========================================================================
        print("\n[4/4] Setup complete!")
        print("\n" + "="*70)
        print("InfluxDB Optimization Summary")
        print("="*70)
        print(f"✓ Downsampled bucket: {downsampled_bucket_name} (30-day retention)")
        print(f"✓ Main bucket: {main_bucket_name} (7-day retention)")
        print(f"✓ Downsampling tasks: {len(tasks)} tasks created")
        print("\nNext steps:")
        print("1. Wait 1-2 minutes for tasks to start generating downsampled data")
        print("2. Restart the backend to use optimized metric queries")
        print("3. Expected performance: 15s → <2s for /system/metrics/all")
        print("="*70)

if __name__ == "__main__":
    try:
        setup_influxdb()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
