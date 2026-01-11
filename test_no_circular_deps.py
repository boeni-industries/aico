#!/usr/bin/env python3
"""
Test that there are NO circular dependencies in the logging system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

print("Testing import order to verify no circular dependencies...\n")

# Test 1: Import logging first
print("1. Import logging module...")
from aico.core.logging import get_logger
print("   ✅ Success\n")

# Test 2: Import config (which might try to log)
print("2. Import config module...")
from aico.core.config import ConfigurationManager
print("   ✅ Success\n")

# Test 3: Import security (which uses config and might log)
print("3. Import security module...")
from aico.security import AICOKeyManager
print("   ✅ Success\n")

# Test 4: Import authorization (which uses logging)
print("4. Import authorization module...")
from aico.core.authorization import AuthorizationService
print("   ✅ Success\n")

# Test 5: Import encrypted_file (which uses logging)
print("5. Import encrypted_file module...")
from aico.security.encrypted_file import EncryptedFile
print("   ✅ Success\n")

# Test 6: Actually use logging
print("6. Initialize logging and use it...")
from aico.core.logging import initialize_logging
initialize_logging("test-circular", enable_influx=False, enable_console=True, log_level=20)
logger = get_logger("test")
logger.info("Test log message")
print("   ✅ Success\n")

print("=" * 60)
print("✅ NO CIRCULAR DEPENDENCIES DETECTED!")
print("=" * 60)
