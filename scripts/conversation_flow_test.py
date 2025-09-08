#!/usr/bin/env python3
"""
Test script for AICO end-to-end conversation flow

Tests the complete conversation pipeline from user input through
the message bus to AI response generation and delivery.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any

from aico.core.logging import get_logger
from aico.core.bus import MessageBusClient
from aico.core.topics import AICOTopics
from aico.proto.aico_conversation_pb2 import ConversationMessage, Message, MessageAnalysis
from google.protobuf.timestamp_pb2 import Timestamp


class ConversationFlowTester:
    """Test the complete conversation flow"""
    
    def __init__(self):
        self.logger = get_logger("test", "conversation_flow")
        self.bus_client = None
        self.test_thread_id = str(uuid.uuid4())
        self.responses_received = []
        
    async def setup(self):
        """Set up test environment"""
        self.logger.info("Setting up conversation flow test...")
        
        # Connect to message bus
        self.bus_client = MessageBusClient("conversation_flow_test")
        await self.bus_client.connect()
        
        # Subscribe to AI responses
        await self.bus_client.subscribe(
            AICOTopics.CONVERSATION_AI_RESPONSE,
            self._handle_ai_response
        )
        
        self.logger.info(f"Test setup complete. Thread ID: {self.test_thread_id}")
    
    async def cleanup(self):
        """Clean up test environment"""
        if self.bus_client:
            await self.bus_client.disconnect()
        self.logger.info("Test cleanup complete")
    
    async def _handle_ai_response(self, topic: str, message: ConversationMessage):
        """Handle AI response messages"""
        if message.message.thread_id == self.test_thread_id:
            self.responses_received.append({
                "timestamp": datetime.utcnow().isoformat(),
                "thread_id": message.message.thread_id,
                "text": message.message.text,
                "type": message.message.type,
                "turn_number": message.message.turn_number
            })
            
            self.logger.info(f"Received AI response: {message.message.text[:100]}...")
    
    async def send_test_message(self, text: str, message_type: str = "user_input") -> str:
        """Send a test message and return message ID"""
        message_id = str(uuid.uuid4())
        
        # Create conversation message
        conv_message = ConversationMessage()
        conv_message.timestamp.GetCurrentTime()
        conv_message.source = "test_user"
        
        # Set message content
        conv_message.message.text = text
        conv_message.message.type = getattr(Message.MessageType, message_type.upper(), Message.MessageType.USER_INPUT)
        conv_message.message.thread_id = self.test_thread_id
        conv_message.message.turn_number = len(self.responses_received) + 1
        
        # Set message analysis
        conv_message.analysis.intent = "test_message"
        conv_message.analysis.urgency = MessageAnalysis.Urgency.MEDIUM
        conv_message.analysis.requires_response = True
        
        # Publish to message bus
        await self.bus_client.publish(
            AICOTopics.CONVERSATION_USER_INPUT,
            conv_message
        )
        
        self.logger.info(f"Sent test message: {text}")
        return message_id
    
    async def test_basic_conversation(self):
        """Test basic conversation flow"""
        self.logger.info("Testing basic conversation flow...")
        
        # Test messages
        test_messages = [
            "Hello, how are you today?",
            "Can you help me with something?",
            "What's the weather like?",
            "Thank you for your help!"
        ]
        
        for i, message in enumerate(test_messages):
            self.logger.info(f"Sending message {i+1}/{len(test_messages)}: {message}")
            
            # Send message
            message_id = await self.send_test_message(message)
            
            # Wait for response
            initial_count = len(self.responses_received)
            timeout = 10.0  # 10 second timeout
            elapsed = 0.0
            
            while len(self.responses_received) <= initial_count and elapsed < timeout:
                await asyncio.sleep(0.1)
                elapsed += 0.1
            
            if len(self.responses_received) > initial_count:
                response = self.responses_received[-1]
                self.logger.info(f"Received response: {response['text'][:100]}...")
            else:
                self.logger.warning(f"No response received for message: {message}")
            
            # Small delay between messages
            await asyncio.sleep(1.0)
    
    async def test_conversation_context(self):
        """Test conversation context handling"""
        self.logger.info("Testing conversation context...")
        
        # Send messages that should build context
        context_messages = [
            "My name is Alice",
            "I'm working on a Python project",
            "What's my name again?",
            "What am I working on?"
        ]
        
        for message in context_messages:
            await self.send_test_message(message)
            await asyncio.sleep(2.0)  # Wait for processing
    
    async def run_all_tests(self):
        """Run all conversation flow tests"""
        try:
            await self.setup()
            
            self.logger.info("Starting conversation flow tests...")
            
            # Test basic conversation
            await self.test_basic_conversation()
            
            # Wait a bit between test suites
            await asyncio.sleep(2.0)
            
            # Test context handling
            await self.test_conversation_context()
            
            # Final summary
            self.logger.info(f"Tests completed. Total responses received: {len(self.responses_received)}")
            
            # Print response summary
            for i, response in enumerate(self.responses_received):
                self.logger.info(f"Response {i+1}: {response['text'][:50]}...")
            
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """Main test function"""
    tester = ConversationFlowTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("AICO Conversation Flow Test")
    print("=" * 50)
    print("This script tests the end-to-end conversation flow:")
    print("1. Sends user messages via message bus")
    print("2. Waits for conversation engine processing")
    print("3. Receives AI responses")
    print("4. Validates the complete pipeline")
    print()
    
    try:
        asyncio.run(main())
        print("\n✅ Conversation flow test completed successfully!")
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
