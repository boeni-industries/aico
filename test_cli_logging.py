#!/usr/bin/env python3
"""
Test CLI logging - should work without InfluxDB.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

print("Test 1: Using get_logger() without initialization (CLI mode)")
from aico.core.logging import get_logger

logger = get_logger("cli.test")
logger.info("CLI log without initialization")
logger.warning("This should work fine")
print("✅ Works without initialization\n")

print("Test 2: Initialize with console-only (no InfluxDB)")
from aico.core.logging import initialize_logging

initialize_logging("cli", enable_influx=False, enable_console=True, log_level=20)
logger2 = get_logger("cli.commands")
logger2.info("CLI log with console-only initialization")
logger2.error("Error message")
print("✅ Console-only logging works\n")

print("=" * 60)
print("✅ CLI logging works perfectly!")
print("=" * 60)
