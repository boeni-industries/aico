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
from aico.proto.aico_core_envelope_pb2 import AicoMessage
from aico.proto.aico_modelservice_pb2 import HealthResponse, CompletionsResponse

# Add modelservice path for message factory
modelservice_path = script_dir.parent / "modelservice"
sys.path.insert(0, str(modelservice_path))

from core.protobuf_messages import ModelserviceMessageFactory, ModelserviceMessageParser

# Initialize configuration and logging
config_manager = ConfigurationManager()
config_manager.initialize()
initialize_logging(config_manager)
logger = get_logger("test", "completions")


async def test_modelservice_health() -> bool:
    """Test modelservice health via ZMQ."""
    try:
        # Initialize message bus client
        client = MessageBusClient(
            client_id="test_client_health",
            config_manager=config_manager
        )
        
        await client.connect()
        logger.info("Connected to message bus")
        logger.info(f"[CLIENT] Client connected status: {client.connected}")
        logger.info(f"[CLIENT] Client ID: {client.client_id}")
        
        # Create health check request using Protocol Buffer
        correlation_id = str(uuid.uuid4())
        from aico.proto.aico_modelservice_pb2 import HealthRequest
        health_request = HealthRequest()  # Create raw request, let MessageBusClient wrap it
        
        # Set up response handler
        response_received = asyncio.Event()
        health_response_data = {}
        
        async def handle_health_response(envelope):
            nonlocal health_response_data
            print(f"[CLIENT] Health response callback triggered!")
            logger.info(f"[CLIENT] Health response callback triggered!")
            print(f"[CLIENT] Received envelope type: {type(envelope)}")
            logger.info(f"[CLIENT] Received envelope type: {type(envelope)}")
            try:
                # Debug the envelope payload
                print(f"[CLIENT] Envelope payload type URL: {envelope.any_payload.type_url}")
                print(f"[CLIENT] Expected HealthResponse descriptor: {HealthResponse.DESCRIPTOR.full_name}")
                print(f"[CLIENT] Payload value length: {len(envelope.any_payload.value)} bytes")
                
                # Extract the health response from the envelope
                health_response = ModelserviceMessageFactory.extract_payload(envelope, HealthResponse)
                print(f"[CLIENT] Health response success: {health_response.success}")
                print(f"[CLIENT] Health response status: {health_response.status}")
                logger.info(f"[CLIENT] Health response success: {health_response.success}")
                logger.info(f"[CLIENT] Health response status: {health_response.status}")
                
                if health_response.success:
                    health_response_data = {
                        'success': health_response.success,
                        'status': health_response.status
                    }
                    print(f"[CLIENT] Setting response_received event")
                    logger.info(f"[CLIENT] Setting response_received event")
                    response_received.set()
                else:
                    print(f"[CLIENT] Health response indicated failure: {health_response.error}")
                    logger.warning(f"[CLIENT] Health response indicated failure: {health_response.error}")
            except Exception as e:
                print(f"[CLIENT] Error parsing health response: {e}")
                logger.error(f"[CLIENT] Error parsing health response: {e}")
                import traceback
                print(f"[CLIENT] Traceback: {traceback.format_exc()}")
                logger.error(f"[CLIENT] Traceback: {traceback.format_exc()}")
        
        # Subscribe to response topic
        print(f"[CLIENT] Subscribing to response topic: {AICOTopics.MODELSERVICE_HEALTH_RESPONSE}")
        logger.info(f"[CLIENT] Subscribing to response topic: {AICOTopics.MODELSERVICE_HEALTH_RESPONSE}")
        await client.subscribe(AICOTopics.MODELSERVICE_HEALTH_RESPONSE, handle_health_response)
        print(f"[CLIENT] Subscription completed")
        logger.info(f"[CLIENT] Subscription completed")
        
        # Longer delay to ensure subscription is fully established
        await asyncio.sleep(0.5)
        print(f"[CLIENT] Ready to send request")
        logger.info(f"[CLIENT] Ready to send request")
        
        # Send request (pass raw protobuf object, let MessageBusClient wrap it)
        print(f"[CLIENT] Publishing health request to topic: {AICOTopics.MODELSERVICE_HEALTH_REQUEST}")
        print(f"[CLIENT] Request object type: {type(health_request)}")
        logger.info(f"Publishing health request to topic: {AICOTopics.MODELSERVICE_HEALTH_REQUEST}")
        logger.info(f"Request object type: {type(health_request)}")
        await client.publish(AICOTopics.MODELSERVICE_HEALTH_REQUEST, health_request, correlation_id=correlation_id)
        print(f"[CLIENT] Sent health check request")
        logger.info("Sent health check request")
        
        # Small delay to allow response to be processed
        await asyncio.sleep(0.2)
        print(f"[CLIENT] Waiting for response...")
        logger.info(f"[CLIENT] Waiting for response...")
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=10.0)
            
            if health_response_data.get('success'):
                logger.info("Health check successful")
                print("✅ Modelservice health check passed")
                return True
            else:
                error = health_response_data.get('error', 'Unknown error')
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
        import time
        
        # Initialize message bus client
        client = MessageBusClient(
            client_id="test_client_completions",
            config_manager=config_manager
        )
        
        await client.connect()
        logger.info("Connected to message bus for completions test")
        
        # Create completions request using Protocol Buffer
        correlation_id = str(uuid.uuid4())
        from aico.proto.aico_modelservice_pb2 import CompletionsRequest, ChatMessage
        completions_request = CompletionsRequest()
        completions_request.model = "hermes3:8b"
        
        # Create chat message
        message = ChatMessage()
        message.role = "user"
        message.content = "Hello, how are you?"
        completions_request.messages.append(message)
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_completion_response(envelope: AicoMessage):
            nonlocal response_data
            print(f"[CLIENT] Completions response callback triggered!")
            logger.info(f"[CLIENT] Completions response callback triggered!")
            print(f"[CLIENT] Received envelope type: {type(envelope)}")
            try:
                print(f"[CLIENT] Envelope payload type URL: {envelope.any_payload.type_url}")
                print(f"[CLIENT] Payload value length: {len(envelope.any_payload.value)} bytes")
                
                if ModelserviceMessageParser.get_correlation_id(envelope) == correlation_id:
                    print(f"[CLIENT] Correlation ID matches, processing response")
                    # Extract the completions response payload
                    completions_response = ModelserviceMessageFactory.extract_payload(envelope, CompletionsResponse)
                    print(f"[CLIENT] Completions response success: {completions_response.success}")
                    
                    if completions_response.success and completions_response.HasField('result'):
                        result = completions_response.result
                        response_data = {
                            'success': completions_response.success,
                            'message': result.message.content if result.HasField('message') else '',
                            'model': result.model,
                            'done': result.done,
                            'total_duration': result.total_duration if result.HasField('total_duration') else 0,
                            'eval_count': result.eval_count if result.HasField('eval_count') else 0,
                            'eval_duration': result.eval_duration if result.HasField('eval_duration') else 0
                        }
                    else:
                        response_data = {
                            'success': completions_response.success,
                            'error': completions_response.error if completions_response.HasField('error') else 'Unknown error'
                        }
                    print(f"[CLIENT] Setting completions response_received event")
                    response_received.set()
                else:
                    print(f"[CLIENT] Correlation ID mismatch: expected {correlation_id}, got {ModelserviceMessageParser.get_correlation_id(envelope)}")
            except Exception as e:
                print(f"[CLIENT] Error parsing completions response: {e}")
                logger.error(f"Error parsing completions response: {e}")
                import traceback
                print(f"[CLIENT] Traceback: {traceback.format_exc()}")
        
        # Subscribe to response topic
        print(f"[CLIENT] Subscribing to completions response topic: {AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE}")
        await client.subscribe(AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE, handle_completion_response)
        print(f"[CLIENT] Completions subscription completed")
        
        # Brief delay to ensure subscription is established
        await asyncio.sleep(0.5)
        print(f"[CLIENT] Ready to send completions request")
        
        # Start timing the LLM roundtrip
        start_time = time.time()
        
        # Send request (pass raw protobuf object, let MessageBusClient wrap it)
        print(f"[CLIENT] Publishing completions request to topic: {AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST}")
        print(f"[CLIENT] Request object type: {type(completions_request)}")
        await client.publish(AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST, completions_request, correlation_id=correlation_id)
        print(f"[CLIENT] Sent completions request")
        logger.info("Sent completions request")
        print("🤖 Sending completion request to modelservice...")
        
        # Small delay to allow response to be processed
        await asyncio.sleep(0.2)
        print(f"[CLIENT] Waiting for completions response...")
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=30.0)
            
            # Calculate roundtrip time
            end_time = time.time()
            roundtrip_time = end_time - start_time
            
            if response_data.get('success'):
                response_text = response_data.get('message', 'No response text')
                model = response_data.get('model', 'unknown')
                
                logger.info(f"Completion successful from model {model}")
                print(f"✅ Completion successful!")
                print(f"📝 Model: {model}")
                print(f"⏱️  Roundtrip Time: {roundtrip_time:.2f} seconds")
                print(f"💬 Response: {response_text}")
                return True
            else:
                error = response_data.get('message', 'Unknown error')
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
