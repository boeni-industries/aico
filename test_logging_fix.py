#!/usr/bin/env python3
"""
Test script to verify the logging protocol fix
"""
import sys
import os
import asyncio
import time

# Add project root to path
sys.path.insert(0, '/Users/mbo/Documents/dev/aico')

from shared.aico.core.config import ConfigurationManager
from shared.aico.core.logging import get_logger
from shared.aico.core.bus import MessageBusBroker
from backend.log_consumer import AICOLogConsumer

async def test_logging_protocol():
    """Test the fixed logging protocol"""
    print("=== Testing AICO Logging Protocol Fix ===")
    
    # Initialize configuration
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    # Start message bus broker
    print("\n1. Starting Message Bus Broker...")
    broker = MessageBusBroker()
    await broker.start()
    print("✅ Message bus broker started")
    
    # Start log consumer
    print("\n2. Starting Log Consumer...")
    log_consumer = AICOLogConsumer()
    await log_consumer.start()
    print("✅ Log consumer started and subscribed to logs.*")
    
    # Wait a moment for connections to stabilize
    await asyncio.sleep(1)
    
    # Create a logger and send test messages
    print("\n3. Creating Logger and Sending Test Messages...")
    logger = get_logger("test", "protocol")
    
    # Send various log levels
    logger.info("Test INFO message - protocol fix verification")
    logger.warning("Test WARNING message - should appear in database")
    logger.error("Test ERROR message - checking message bus routing")
    
    print("✅ Test messages sent via ZMQ transport")
    
    # Wait for messages to be processed
    print("\n4. Waiting for message processing...")
    await asyncio.sleep(3)
    
    # Check if log consumer received messages
    print("\n5. Test Results:")
    print("Check the console output above for:")
    print("  - '[LOG CONSUMER] Received AICOMessage' messages")
    print("  - '[LOG CONSUMER] Parsed log entry:' messages")
    print("  - '[LOG CONSUMER] Inserted log into database' messages")
    
    # Cleanup
    print("\n6. Cleaning up...")
    await log_consumer.stop()
    await broker.stop()
    print("✅ Cleanup complete")
    
    print("\n=== Test Complete ===")
    print("If you see log consumer messages above, the protocol fix is working!")

if __name__ == "__main__":
    asyncio.run(test_logging_protocol())
