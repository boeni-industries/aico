#!/usr/bin/env python3
"""
Test the new clean logging API.
"""

import time
import sys
import os

# Add shared to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

# Import new clean API
from aico.core.logging import initialize_logging, get_logger, shutdown_logging, get_influx_stats

print("=" * 60)
print("Testing Clean Logging API")
print("=" * 60)

# Initialize logging
print("\n1. Initializing logging for 'test-clean' service...")
initialize_logging(
    service_name="test-clean",
    enable_influx=True,
    enable_console=True,
    log_level=10  # DEBUG
)

# Get loggers
print("\n2. Getting loggers...")
logger1 = get_logger("api.gateway")
logger2 = get_logger("memory.semantic")
logger3 = get_logger("scheduler.tasks")

# Test logging
print("\n3. Sending test logs...")
logger1.debug("Debug from API gateway")
logger1.info("Request received", extra={"user_id": "user-123", "request_id": "req-456"})
logger1.warning("Slow response detected", extra={"duration_ms": 1500})
logger1.error("Request failed", extra={"error_code": "AUTH_FAILED"})

logger2.info("Semantic search completed", extra={"query": "test query", "results": 5})
logger2.debug("Vector similarity calculated")

logger3.info("Task scheduled", extra={"task_id": "task-789"})

try:
    raise ValueError("Test exception from scheduler")
except Exception:
    logger3.exception("Task execution failed")

# Check stats
print(f"\n4. Buffer stats: {get_influx_stats()}")

# Wait for flush
print("\n5. Waiting 6 seconds for flush...")
time.sleep(6)

# Final stats
print(f"\n6. Final stats: {get_influx_stats()}")

# Shutdown
print("\n7. Shutting down logging...")
shutdown_logging()

print("\n" + "=" * 60)
print("✅ Test complete!")
print("=" * 60)
print("\nCheck InfluxDB Data Explorer:")
print("  Measurement: logs")
print("  Service: test-clean")
print("  Fields: count, message, user_id, request_id, etc.")
print("\nFlux query:")
print("  from(bucket: \"aico_telemetry\")")
print("    |> range(start: -1h)")
print("    |> filter(fn: (r) => r._measurement == \"logs\")")
print("    |> filter(fn: (r) => r.service == \"test-clean\")")
