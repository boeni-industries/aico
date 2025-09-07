#!/usr/bin/env python3
"""
HOWTO: Minimal Working Example - AICO Modelservice Completions via ZMQ

This is the absolute minimal code needed to send a completion request
to the AICO modelservice over the secure ZeroMQ message bus.

WHAT THIS EXAMPLE SHOWS:
    ✅ How to connect to AICO's secure ZMQ message bus
    ✅ How to create and send a completion request with protobuf
    ✅ How to handle async responses with correlation ID matching
    ✅ How to parse completion responses and extract text

PREREQUISITES:
    1. AICO backend running (starts the message bus broker)
       Command: `aico backend start` or `uv run backend/main.py`
    
    2. AICO modelservice running with Ollama
       Command: `aico modelservice start` or `uv run modelservice/main.py`
    
    3. Ollama running with a model (e.g., hermes3:8b)
       Commands: `ollama serve` then `ollama pull hermes3:8b`

USAGE:
    python howto_completions_zmq.py
    # or
    uv run scripts/howto_completions_zmq.py

COMMON PITFALLS FOR NEW DEVELOPERS:

    ❌ PITFALL #1: Not subscribing before sending request
       The subscription MUST be active before sending the request,
       otherwise you'll miss the response and get a timeout.
       
    ❌ PITFALL #2: Wrong correlation ID matching
       Each request gets a unique correlation_id. The response handler
       MUST check that response_correlation_id == correlation_id.
       
    ❌ PITFALL #3: Incorrect protobuf parsing
       Use envelope.any_payload.Unpack(response) NOT ParseFromString().
       The envelope wraps the actual protobuf message.
       
    ❌ PITFALL #4: Missing HasField() checks
       Always check response.HasField('result') and result.HasField('message')
       before accessing nested protobuf fields to avoid AttributeError.
       
    ❌ PITFALL #5: Forgetting async/await
       All ZMQ operations are async. Don't forget await on client methods.
       
    ❌ PITFALL #6: Wrong topic names
       Use AICOTopics constants: AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST
       and AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE (centralized management).

ARCHITECTURE NOTES:
    - Uses CurveZMQ encryption for secure communication
    - Protocol Buffers for message serialization
    - Correlation IDs for request/response matching
    - Async/await pattern for non-blocking operations
    - Topic-based pub/sub messaging pattern

CUSTOMIZATION:
    - Change the model: request.model = "your-model-name"
    - Change the prompt: modify the prompt variable in main()
    - Add conversation history: append more ConversationMessage objects to request.messages
    - Adjust timeout: change the timeout value in asyncio.wait_for()
"""

import asyncio
import sys
import uuid
from pathlib import Path
from aico.core.config import ConfigurationManager
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_modelservice_pb2 import CompletionsRequest, ConversationMessage, CompletionsResponse
from aico.proto.aico_core_envelope_pb2 import AicoMessage

# Add modelservice path for message factory
script_dir = Path(__file__).parent
modelservice_path = script_dir.parent / "modelservice"
sys.path.insert(0, str(modelservice_path))

from core.protobuf_messages import ModelserviceMessageFactory, ModelserviceMessageParser


async def send_completion_request(prompt: str) -> str:
    """Send a completion request and return the response text."""
    
    # Initialize AICO configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Create ZMQ client
    client = MessageBusClient(
        client_id="test_client_completions",
        config_manager=config_manager
    )
    
    try:
        # Connect to message bus
        await client.connect()
        print("✅ Connected to AICO message bus")
        
        # Create completion request
        correlation_id = str(uuid.uuid4())
        request = CompletionsRequest()
        request.model = "hermes3:8b"  # Use your preferred model
        
        # Add the user message
        message = ConversationMessage()
        message.role = "user"
        message.content = prompt
        request.messages.append(message)
        
        # Set up response handler
        response_text = None
        response_received = asyncio.Event()
        
        async def handle_response(envelope: AicoMessage):
            nonlocal response_text
            try:
                print("📨 Received response from modelservice")
                
                # Extract correlation ID directly from envelope metadata
                response_correlation_id = envelope.metadata.attributes.get("correlation_id")
                
                if response_correlation_id != correlation_id:
                    return  # Not our response
                
                # Parse the completions response directly from envelope payload
                response = CompletionsResponse()
                envelope.any_payload.Unpack(response)
                
                if response.success and response.HasField('result'):
                    result = response.result
                    if result.HasField('message'):
                        response_text = result.message.content
                        print(f"✅ Got completion response")
                    else:
                        response_text = "No message content in response"
                else:
                    response_text = f"Error: {response.error if response.HasField('error') else 'Unknown error'}"
                
                response_received.set()
                
            except Exception as e:
                print(f"❌ Error handling response: {e}")
                response_text = f"Response parsing error: {e}"
                response_received.set()
        
        # Subscribe to response topic BEFORE sending request
        await client.subscribe(AICOTopics.MODELSERVICE_COMPLETIONS_RESPONSE, handle_response)
        
        # Small delay to ensure subscription is active
        await asyncio.sleep(0.1)
        
        # Send the request
        await client.publish(
            AICOTopics.MODELSERVICE_COMPLETIONS_REQUEST,
            request,
            correlation_id=correlation_id
        )
        
        print(f"📤 Sent completion request: '{prompt}'")
        
        # Wait for response (15 second timeout)
        try:
            await asyncio.wait_for(response_received.wait(), timeout=15.0)
            return response_text or "No response received"
        except asyncio.TimeoutError:
            return "Timeout: No response received within 15 seconds"
            
    finally:
        await client.disconnect()


async def main():
    """Main example function."""
    print("🤖 AICO Modelservice Completion Example")
    print("=" * 50)
    
    # Example prompt
    prompt = "Hello! How are you?"
    
    print(f"Sending prompt: '{prompt}'")
    print("Waiting for response...")
    
    # Send completion request
    response = await send_completion_request(prompt)
    
    print(f"\n🎯 Response: {response}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n💥 Error: {e}")
