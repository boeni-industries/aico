#!/usr/bin/env python3
"""
Quick test of InfluxDB logging handler.
Run: python test_influx_logging.py
"""

import logging
import time
import sys
sys.path.insert(0, 'shared')

# Direct import to avoid old logging system
from aico.core.logging.integration import setup_influx_logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add InfluxDB handler
print("Setting up InfluxDB logging...")
handler = setup_influx_logging(
    service_name="test",
    enabled=True
)

if not handler:
    print("❌ Failed to setup InfluxDB logging")
    sys.exit(1)

print(f"✅ InfluxDB handler created: {handler}")

# Test logging
logger = logging.getLogger("test.module")

print("\nSending test logs...")
logger.debug("Debug message")
logger.info("Info message", extra={"user_id": "test-user-123"})
logger.warning("Warning message")
logger.error("Error message", extra={"request_id": "req-456"})

try:
    raise ValueError("Test exception")
except Exception:
    logger.exception("Exception with traceback")

print(f"\nBuffer stats: {handler.get_stats()}")
print("\nWaiting 6 seconds for flush...")
time.sleep(6)

print(f"Final stats: {handler.get_stats()}")

# Cleanup
handler.close()
print("\n✅ Test complete - check InfluxDB for logs in 'aico_telemetry' bucket")
