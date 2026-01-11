#!/usr/bin/env python3
"""Test exception logging with new InfluxDB handler."""

import logging
import time
from aico.core.logging.simple import initialize_logging

# Setup logging
initialize_logging(service_name="test-exceptions")
logger = logging.getLogger("test-exceptions.main")

print("Testing exception logging...")
print("=" * 60)

# Test 1: logger.exception() in except block
print("\n1. Testing logger.exception() in except block:")
try:
    result = 1 / 0
except ZeroDivisionError:
    logger.exception("Division by zero error occurred")

# Test 2: logger.error() with exc_info=True
print("\n2. Testing logger.error() with exc_info=True:")
try:
    data = {"key": "value"}
    _ = data["missing_key"]
except KeyError as e:
    logger.error(f"Key error: {e}", exc_info=True)

# Test 3: Nested exception
print("\n3. Testing nested exception:")
try:
    try:
        raise ValueError("Inner exception")
    except ValueError:
        raise RuntimeError("Outer exception") from ValueError("Inner exception")
except RuntimeError:
    logger.exception("Nested exception caught")

# Test 4: Exception with extra metadata
print("\n4. Testing exception with extra metadata:")
try:
    raise ConnectionError("Failed to connect to database")
except ConnectionError:
    logger.exception(
        "Database connection failed",
        extra={
            "user_id": "user-123",
            "request_id": "req-456",
            "error_code": "DB_CONN_FAILED"
        }
    )

# Test 5: Regular log with extra metadata (no exception)
print("\n5. Testing regular log with metadata:")
logger.info(
    "User action completed",
    extra={
        "user_id": "user-789",
        "conversation_id": "conv-abc",
        "duration_ms": 250
    }
)

print("\n" + "=" * 60)
print("Waiting 3 seconds for logs to flush to InfluxDB...")
time.sleep(3)

print("\n✅ Test complete!")
print("\nTo view the logs in InfluxDB:")
print("  aico logs tail --service test-exceptions -n 20")
print("\nTo see only exceptions:")
print("  aico logs tail --service test-exceptions --level error -n 20")
