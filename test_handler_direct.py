#!/usr/bin/env python3
"""
Direct test of InfluxDB handler - bypasses all imports.
"""

import logging
import time
import sys
import os

# Direct file import to bypass package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

# Import handler module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "influx_handler",
    "shared/aico/core/logging/influx_handler.py"
)
influx_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(influx_module)

InfluxDBLogHandler = influx_module.InfluxDBLogHandler

# Hardcode credentials for test
influx_url = "http://127.0.0.1:8086"
org = "aico"
bucket = "aico_telemetry"

# Get token from keyring
import keyring
token = keyring.get_password("AICO", "influx_admin_token_password")

if not token:
    print("❌ No InfluxDB token found in keyring")
    sys.exit(1)

print(f"✅ InfluxDB: {influx_url}, org={org}, bucket={bucket}")
print(f"✅ Token: {token[:8]}...{token[-4:]}")

# Create handler
handler = InfluxDBLogHandler(
    influx_url=influx_url,
    org=org,
    bucket=bucket,
    token=token,
    service_name="test",
    buffer_size=100,
    flush_interval=3.0,
    batch_size=50
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test.module")
logger.addHandler(handler)

print("\n📝 Sending test logs...")
logger.debug("Debug message from test")
logger.info("Info message from test", extra={"user_id": "test-user-123"})
logger.warning("Warning message from test")
logger.error("Error message from test", extra={"request_id": "req-456"})

try:
    raise ValueError("Test exception")
except Exception:
    logger.exception("Exception with traceback from test")

print(f"\n📊 Buffer stats: {handler.get_stats()}")
print("\n⏳ Waiting 4 seconds for flush...")
time.sleep(4)

print(f"\n📊 Final stats: {handler.get_stats()}")

# Cleanup
handler.close()
print("\n✅ Test complete!")
print("   Check InfluxDB: SELECT * FROM logs WHERE service='test' ORDER BY time DESC LIMIT 10")
