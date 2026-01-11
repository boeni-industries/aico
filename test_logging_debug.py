#!/usr/bin/env python3
"""
Debug version - trace where the hang occurs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

print("Step 1: Importing logging module...")
from aico.core.logging import initialize_logging, get_logger

print("Step 2: Calling initialize_logging...")
initialize_logging(
    service_name="test-debug",
    enable_influx=True,
    enable_console=True,
    log_level=20  # INFO
)

print("Step 3: Getting logger...")
logger = get_logger("test.module")

print("Step 4: Logging message...")
logger.info("Test message")

print("Step 5: Done!")
