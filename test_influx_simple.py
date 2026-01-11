#!/usr/bin/env python3
"""
Simple test of InfluxDB logging handler - no dependencies on old logging system.
"""

import logging
import time
import sys

# Add shared to path
sys.path.insert(0, 'shared')

# Import handler directly
from aico.core.logging.influx_handler import InfluxDBLogHandler

# Get InfluxDB credentials
from aico.core.config import ConfigurationManager
from aico.security import AICOKeyManager

config = ConfigurationManager()
config.initialize(lightweight=True)

influx_url = config.get("core.database.influx.url", "http://127.0.0.1:8086")
org = config.get("core.database.influx.org", "aico")
bucket = config.get("core.database.influx.bucket", "aico_telemetry")

key_manager = AICOKeyManager(config)
token = key_manager.get_database_password("influx", username="admin_token")

if not token:
    print("❌ No InfluxDB token found")
    sys.exit(1)

print(f"✅ InfluxDB config: {influx_url}, org={org}, bucket={bucket}")

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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test.module")
logger.addHandler(handler)

print("\n📝 Sending test logs...")
logger.debug("Debug message")
logger.info("Info message", extra={"user_id": "test-user-123"})
logger.warning("Warning message")
logger.error("Error message", extra={"request_id": "req-456"})

try:
    raise ValueError("Test exception")
except Exception:
    logger.exception("Exception with traceback")

print(f"\n📊 Buffer stats: {handler.get_stats()}")
print("\n⏳ Waiting 4 seconds for flush...")
time.sleep(4)

print(f"\n📊 Final stats: {handler.get_stats()}")

# Cleanup
handler.close()
print("\n✅ Test complete - check InfluxDB for logs in 'aico_telemetry' bucket, 'logs' measurement")
print("   Query: SELECT * FROM logs WHERE service='test' ORDER BY time DESC LIMIT 10")
