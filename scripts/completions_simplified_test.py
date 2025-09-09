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
    """Test modelservice health check via ZMQ."""
    try:
        import time
        
        # Timing data for performance analysis
        timing_data = {}
        
        # Initialize message bus client
        start_init = time.time()
        client = MessageBusClient(
            client_id="test_client_health",
            config_manager=config_manager
        )
        
        start_connect = time.time()
        await client.connect()
        timing_data['client_init'] = start_connect - start_init
        timing_data['client_connect'] = time.time() - start_connect
        logger.info("Connected to message bus for health test")
        logger.info(f"[CLIENT] Client connected status: {client.connected}")
        logger.info(f"[CLIENT] Client ID: {client.client_id}")
        
        # Create health request using Protocol Buffer
        start_request_prep = time.time()
        correlation_id = str(uuid.uuid4())
        from aico.proto.aico_modelservice_pb2 import HealthRequest
        health_request = HealthRequest()
        timing_data['request_prep'] = time.time() - start_request_prep  # Create raw request, let MessageBusClient wrap it
        
        # Set up response handler
        response_received = asyncio.Event()
        health_response_data = {}
        
        async def handle_health_response(envelope: AicoMessage):
            nonlocal health_response_data
            timing_data['response_received'] = time.time()
            logger.info("Health response callback triggered!")
            try:
                if ModelserviceMessageParser.get_correlation_id(envelope) == correlation_id:
                    start_parse = time.time()
                    # Extract the health response payload
                    health_response = ModelserviceMessageFactory.extract_payload(envelope, HealthResponse)
                    timing_data['response_parse'] = time.time() - start_parse
                    
                    if health_response.success:
                        health_response_data = {
                            'success': health_response.success,
                            'status': health_response.status
                        }
                    else:
                        health_response_data = {
                            'success': health_response.success,
                            'error': health_response.error if health_response.HasField('error') else 'Unknown error'
                        }
                    response_received.set()
                else:
                    logger.warning(f"Health response indicated failure: {health_response.error}")
            except Exception as e:
                logger.error(f"Error parsing health response: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Subscribe to response topic
        start_subscribe = time.time()
        logger.info(f"Subscribing to response topic: {AICOTopics.MODELSERVICE_HEALTH_RESPONSE}")
        await client.subscribe(AICOTopics.MODELSERVICE_HEALTH_RESPONSE, handle_health_response)
        timing_data['subscription'] = time.time() - start_subscribe
        logger.info("Subscription completed")
        
        # Longer delay to ensure subscription is fully established
        start_sub_delay = time.time()
        await asyncio.sleep(0.5)
        timing_data['subscription_delay'] = time.time() - start_sub_delay
        logger.info("Ready to send request")
        
        # Start timing the health check roundtrip
        start_time = time.time()
        timing_data['request_start'] = start_time
        
        # Send request (pass raw protobuf object, let MessageBusClient wrap it)
        start_publish = time.time()
        logger.info(f"Publishing health request to topic: {AICOTopics.MODELSERVICE_HEALTH_REQUEST}")
        logger.info(f"Request object type: {type(health_request)}")
        await client.publish(AICOTopics.MODELSERVICE_HEALTH_REQUEST, health_request, correlation_id=correlation_id)
        timing_data['publish'] = time.time() - start_publish
        logger.info("Sent health check request")
        
        # Small delay to allow response to be processed
        await asyncio.sleep(0.2)
        logger.info("Waiting for response...")
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=10.0)
            
            # Calculate roundtrip time
            end_time = time.time()
            roundtrip_time = end_time - start_time
            timing_data['total_roundtrip'] = roundtrip_time
            
            # Calculate derived timings
            if 'response_received' in timing_data and 'request_start' in timing_data:
                timing_data['network_roundtrip'] = timing_data['response_received'] - timing_data['request_start']
                timing_data['processing_time'] = timing_data['network_roundtrip'] - timing_data.get('response_parse', 0)
            
            if health_response_data.get('success'):
                logger.info("Health check successful")
                print("✅ Modelservice health check passed")
                
                # Store timing data for later use
                timing_data['success'] = True
                return timing_data
            else:
                error = health_response_data.get('error', 'Unknown error')
                logger.error(f"Health check failed: {error}")
                print(f"❌ Modelservice health check failed: {error}")
                timing_data['success'] = False
                timing_data['error'] = error
                return timing_data
                
        except asyncio.TimeoutError:
            logger.error("Health check timed out")
            print("❌ Modelservice health check timed out")
            timing_data['success'] = False
            timing_data['error'] = 'Timeout'
            timing_data['total_roundtrip'] = 10.0
            return timing_data
        
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        print(f"❌ Health check error: {str(e)}")
        return {'success': False, 'error': str(e), 'total_roundtrip': 0}


async def test_modelservice_completions() -> bool:
    """Test modelservice completions via ZMQ."""
    try:
        import time
        
        # Timing data for performance analysis
        timing_data = {}
        
        # Initialize message bus client
        start_init = time.time()
        client = MessageBusClient(
            client_id="test_client_completions",
            config_manager=config_manager
        )
        
        start_connect = time.time()
        await client.connect()
        timing_data['client_init'] = start_connect - start_init
        timing_data['client_connect'] = time.time() - start_connect
        logger.info("Connected to message bus for completions test")
        
        # Create completions request using Protocol Buffer
        start_request_prep = time.time()
        correlation_id = str(uuid.uuid4())
        from aico.proto.aico_modelservice_pb2 import CompletionsRequest, ConversationMessage
        completions_request = CompletionsRequest()
        completions_request.model = "hermes3:8b"
        
        # Create conversation message
        message = ConversationMessage()
        message.role = "user"
        message.content = "Hello, how are you?"
        completions_request.messages.append(message)
        timing_data['request_prep'] = time.time() - start_request_prep
        
        # Set up response handler
        response_received = asyncio.Event()
        response_data = {}
        
        async def handle_completion_response(envelope: AicoMessage):
            nonlocal response_data
            timing_data['response_received'] = time.time()
            logger.info("Completions response callback triggered!")
            try:
                
                if ModelserviceMessageParser.get_correlation_id(envelope) == correlation_id:
                    start_parse = time.time()
                    # Extract the completions response payload
                    completions_response = ModelserviceMessageFactory.extract_payload(envelope, CompletionsResponse)
                    timing_data['response_parse'] = time.time() - start_parse
                    
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
                    response_received.set()
                else:
                    pass
            except Exception as e:
                logger.error(f"Error parsing completions response: {e}")
                import traceback
        
        # Subscribe to response topic
        start_subscribe = time.time()
        await client.subscribe(AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE, handle_completion_response)
        timing_data['subscription'] = time.time() - start_subscribe
        
        # Brief delay to ensure subscription is established
        start_sub_delay = time.time()
        await asyncio.sleep(0.5)
        timing_data['subscription_delay'] = time.time() - start_sub_delay
        
        # Start timing the LLM roundtrip
        start_time = time.time()
        timing_data['request_start'] = start_time
        
        # Send request (pass raw protobuf object, let MessageBusClient wrap it)
        start_publish = time.time()
        await client.publish(AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST, completions_request, correlation_id=correlation_id)
        timing_data['publish'] = time.time() - start_publish
        logger.info("Sent completions request")
        print("🤖 Sending completion request to modelservice...")
        
        # Small delay to allow response to be processed
        await asyncio.sleep(0.2)
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=30.0)
            
            # Calculate roundtrip time
            end_time = time.time()
            roundtrip_time = end_time - start_time
            timing_data['total_roundtrip'] = roundtrip_time
            
            if response_data.get('success'):
                response_text = response_data.get('message', 'No response text')
                model = response_data.get('model', 'unknown')
                
                # Calculate derived timings
                if 'response_received' in timing_data and 'request_start' in timing_data:
                    timing_data['network_roundtrip'] = timing_data['response_received'] - timing_data['request_start']
                    timing_data['processing_time'] = timing_data['network_roundtrip'] - timing_data.get('response_parse', 0)
                
                logger.info(f"Completion successful from model {model}")
                print(f"✅ Completion successful!")
                print(f"📝 Model: {model}")
                print(f"💬 Response: {response_text}")
                
                # Store Ollama timing data for comprehensive report
                if response_data.get('total_duration', 0) > 0:
                    timing_data['ollama_total_duration'] = response_data.get('total_duration', 0) / 1_000_000  # Convert nanoseconds to milliseconds
                    timing_data['ollama_eval_duration'] = response_data.get('eval_duration', 0) / 1_000_000
                    timing_data['ollama_eval_count'] = response_data.get('eval_count', 0)
                
                timing_data['success'] = True
                timing_data['response_text'] = response_text
                timing_data['model'] = model
                return timing_data
            else:
                error = response_data.get('message', 'Unknown error')
                logger.error(f"Completion failed: {error}")
                print(f"❌ Completion failed: {error}")
                timing_data['success'] = False
                timing_data['error'] = error
                return timing_data
                
        except asyncio.TimeoutError:
            logger.error("Completion request timed out")
            print("❌ Completion request timed out (30s)")
            timing_data['success'] = False
            timing_data['error'] = 'Timeout'
            timing_data['total_roundtrip'] = 30.0
            return timing_data
        
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"Completions test error: {str(e)}")
        print(f"❌ Completions test error: {str(e)}")
        return {'success': False, 'error': str(e), 'total_roundtrip': 0}


async def main():
    """Main test function."""
    import time
    
    print("🧪 AICO Modelservice ZMQ Test Suite")
    print("=" * 60)
    
    # Start overall timing
    overall_start = time.time()
    
    # Test 1: Health Check
    print("\n1️⃣ Testing modelservice health...")
    health_timing = await test_modelservice_health()
    health_ok = health_timing.get('success', False) if isinstance(health_timing, dict) else health_timing
    
    if not health_ok:
        print("\n❌ Health check failed - skipping completions test")
        return False
    
    # Test 2: Completions
    print("\n2️⃣ Testing modelservice completions...")
    completions_timing = await test_modelservice_completions()
    completions_ok = completions_timing.get('success', False) if isinstance(completions_timing, dict) else completions_timing
    
    # Calculate total time
    total_time = time.time() - overall_start
    
    # Comprehensive Performance Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # Health Check Performance
    if isinstance(health_timing, dict):
        print("\n🏥 HEALTH CHECK PERFORMANCE:")
        print(f"   Client Init:        {health_timing.get('client_init', 0)*1000:.1f}ms")
        print(f"   Client Connect:     {health_timing.get('client_connect', 0)*1000:.1f}ms")
        print(f"   Request Prep:       {health_timing.get('request_prep', 0)*1000:.1f}ms")
        print(f"   Subscription:       {health_timing.get('subscription', 0)*1000:.1f}ms")
        print(f"   Subscription Delay: {health_timing.get('subscription_delay', 0)*1000:.1f}ms")
        print(f"   Publish Request:    {health_timing.get('publish', 0)*1000:.1f}ms")
        print(f"   Processing Time:    {health_timing.get('processing_time', 0)*1000:.1f}ms")
        print(f"   Response Parse:     {health_timing.get('response_parse', 0)*1000:.1f}ms")
        print(f"   ─────────────────────────────────────")
        print(f"   HEALTH ROUNDTRIP:   {health_timing.get('total_roundtrip', 0)*1000:.1f}ms")
    
    # Completions Performance
    if isinstance(completions_timing, dict):
        print("\n🤖 COMPLETIONS PERFORMANCE:")
        print(f"   Client Init:        {completions_timing.get('client_init', 0)*1000:.1f}ms")
        print(f"   Client Connect:     {completions_timing.get('client_connect', 0)*1000:.1f}ms")
        print(f"   Request Prep:       {completions_timing.get('request_prep', 0)*1000:.1f}ms")
        print(f"   Subscription:       {completions_timing.get('subscription', 0)*1000:.1f}ms")
        print(f"   Subscription Delay: {completions_timing.get('subscription_delay', 0)*1000:.1f}ms")
        print(f"   Publish Request:    {completions_timing.get('publish', 0)*1000:.1f}ms")
        print(f"   Processing Time:    {completions_timing.get('processing_time', 0)*1000:.1f}ms")
        print(f"   Response Parse:     {completions_timing.get('response_parse', 0)*1000:.1f}ms")
        print(f"   ─────────────────────────────────────")
        print(f"   COMPLETIONS ROUNDTRIP: {completions_timing.get('total_roundtrip', 0)*1000:.1f}ms")
        
        # Extract Ollama timing if available
        if completions_timing.get('ollama_total_duration', 0) > 0:
            ollama_total = completions_timing.get('ollama_total_duration', 0)
            ollama_eval = completions_timing.get('ollama_eval_duration', 0)
            print(f"\n🦙 OLLAMA PERFORMANCE:")
            print(f"   Total Duration:     {ollama_total:.1f}ms")
            print(f"   Eval Duration:      {ollama_eval:.1f}ms")
            print(f"   Eval Count:         {completions_timing.get('ollama_eval_count', 0)} tokens")
            if completions_timing.get('ollama_eval_count', 0) > 0:
                tokens_per_sec = completions_timing.get('ollama_eval_count', 0) / (ollama_eval / 1000)
                print(f"   Tokens/Second:      {tokens_per_sec:.1f}")
    
    # Overall Summary
    print(f"\n⏱️  OVERALL TEST SUITE:")
    print(f"   Total Test Time:    {total_time*1000:.1f}ms ({total_time:.2f}s)")
    print(f"   Health Check:       {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Completions:        {'✅ PASS' if completions_ok else '❌ FAIL'}")
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
