#!/usr/bin/env python3
"""
Minimal test - just test the handler directly without any config/keyring.
"""

import logging
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

# Direct import
from aico.core.logging.influx_handler import InfluxDBLogHandler
import keyring

# Get token directly
token = keyring.get_password("AICO", "influx_admin_token_password")

print("Creating handler...")
handler = InfluxDBLogHandler(
    influx_url="http://127.0.0.1:8086",
    org="aico",
    bucket="aico_telemetry",
    token=token,
    service_name="test-minimal",
    buffer_size=100,
    flush_interval=3.0,
    batch_size=50
)

# Setup basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test")
logger.addHandler(handler)

print("Sending logs...")
logger.info("Test log 1")
logger.info("Test log 2")
logger.error("Test error")

print(f"Stats: {handler.get_stats()}")
print("Waiting 4s...")
time.sleep(4)

print(f"Final: {handler.get_stats()}")
handler.close()
print("✅ Done")
