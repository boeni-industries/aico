#!/usr/bin/env python3
"""
Test direct logging to verify the backend logging system works
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger

async def test_direct_logging():
    """Test direct logging to the AICO system"""
    print("=== Testing Direct AICO Logging ===")
    
    # Initialize configuration and logging
    config_manager = ConfigurationManager()
    logger_factory = initialize_logging(config_manager)
    
    # Get a logger for testing
    logger = get_logger("test", "direct_logging")
    
    print("1. Sending test log messages...")
    
    # Send some test log messages
    logger.info("Test log message 1 - INFO level")
    logger.warning("Test log message 2 - WARNING level") 
    logger.error("Test log message 3 - ERROR level")
    
    # Wait a moment for async processing
    print("2. Waiting for logs to be processed...")
    await asyncio.sleep(2)
    
    print("3. Test complete - check database for new logs")

if __name__ == "__main__":
    asyncio.run(test_direct_logging())
