#!/usr/bin/env python3
"""
Completions Test Script - ZMQ Version

Tests the modelservice completions via ZeroMQ message bus with CurveZMQ encryption.
This script sends a simple "hello world" request to test the complete ZMQ flow.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, Any

# Add shared module to path
script_dir = Path(__file__).parent
shared_path = script_dir.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_logging, get_logger
from aico.core.topics import AICOTopics
from aico.core.bus import MessageBusClient

# Initialize configuration and logging
config_manager = ConfigurationManager()
config_manager.initialize()
initialize_logging(config_manager)
logger = get_logger("test", "completions")


async def test_modelservice_health() -> bool:
    """Test modelservice health via ZMQ."""
    try:
        # Initialize message bus client
        bus_config = config_manager.get('message_bus', {})
        client = MessageBusClient(
            broker_address=bus_config.get('broker_address', 'tcp://localhost:5555'),
            identity="test_client",
            enable_curve=True
        )
        
        await client.connect()
        logger.info("Connected to message bus")
        
        # Send health check request
        correlation_id = str(uuid.uuid4())
        request_message = {
            'correlation_id': correlation_id,
            'data': {},
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_health_response(topic: str, message: dict):
            nonlocal response_data
            if message.get('correlation_id') == correlation_id:
                response_data = message
                response_received.set()
        
        # Subscribe to response topic
        await client.subscribe(AICOTopics.MODELSERVICE_HEALTH_RESPONSE, handle_health_response)
        
        # Send request
        await client.publish(AICOTopics.MODELSERVICE_HEALTH_REQUEST, request_message)
        logger.info("Sent health check request")
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=10.0)
            
            if response_data.get('data', {}).get('success'):
                logger.info("Health check successful")
                print("✅ Modelservice health check passed")
                return True
            else:
                error = response_data.get('data', {}).get('error', 'Unknown error')
                logger.error(f"Health check failed: {error}")
                print(f"❌ Modelservice health check failed: {error}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Health check timed out")
            print("❌ Modelservice health check timed out")
            return False
        
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        print(f"❌ Health check error: {str(e)}")
        return False


async def test_modelservice_completions() -> bool:
    """Test modelservice completions via ZMQ."""
    try:
        # Initialize message bus client
        bus_config = config_manager.get('message_bus', {})
        client = MessageBusClient(
            broker_address=bus_config.get('broker_address', 'tcp://localhost:5555'),
            identity="test_client",
            enable_curve=True
        )
        
        await client.connect()
        logger.info("Connected to message bus for completions test")
        
        # Send completions request
        correlation_id = str(uuid.uuid4())
        completion_request = {
            'correlation_id': correlation_id,
            'data': {
                'model': 'llama3.2:1b',  # Use a small model for testing
                'prompt': 'Hello! Please respond with a brief greeting.',
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'max_tokens': 50
                }
            },
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_completion_response(topic: str, message: dict):
            nonlocal response_data
            if message.get('correlation_id') == correlation_id:
                response_data = message
                response_received.set()
        
        # Subscribe to response topic
        await client.subscribe(AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE, handle_completion_response)
        
        # Send request
        await client.publish(AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST, completion_request)
        logger.info("Sent completions request")
        print("🤖 Sending completion request to modelservice...")
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=30.0)
            
            if response_data.get('data', {}).get('success'):
                completion_data = response_data.get('data', {}).get('data', {})
                response_text = completion_data.get('response', 'No response text')
                model = completion_data.get('model', 'unknown')
                
                logger.info(f"Completion successful from model {model}")
                print(f"✅ Completion successful!")
                print(f"📝 Model: {model}")
                print(f"💬 Response: {response_text}")
                return True
            else:
                error = response_data.get('data', {}).get('error', 'Unknown error')
                logger.error(f"Completion failed: {error}")
                print(f"❌ Completion failed: {error}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Completion request timed out")
            print("❌ Completion request timed out (30s)")
            return False
        
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"Completion test error: {str(e)}")
        print(f"❌ Completion test error: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 AICO Modelservice ZMQ Test Suite")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing modelservice health...")
    health_ok = await test_modelservice_health()
    
    if not health_ok:
        print("\n❌ Health check failed - skipping completions test")
        return False
    
    # Test 2: Completions
    print("\n2️⃣ Testing modelservice completions...")
    completions_ok = await test_modelservice_completions()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Completions:  {'✅ PASS' if completions_ok else '❌ FAIL'}")
    print("=" * 60)
    
    return health_ok and completions_ok


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite error: {str(e)}")
        sys.exit(1)
