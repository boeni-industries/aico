#!/usr/bin/env python3
"""
Quick test to verify ConversationEngine can start and subscribe to topics
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_conversation_engine():
    """Test if ConversationEngine can start independently"""
    try:
        print("🧪 Testing ConversationEngine startup...")
        
        # Initialize configuration first
        from aico.core.config import ConfigurationManager
        config = ConfigurationManager()
        
        # Initialize logging
        from aico.core.logging import initialize_cli_logging
        initialize_cli_logging(config, None)  # No DB connection needed for test
        
        # Create a minimal service container
        from backend.core.service_container import ServiceContainer
        container = ServiceContainer(config)
        
        # Import and create ConversationEngine
        from backend.services.conversation_engine import ConversationEngine
        engine = ConversationEngine("test_conversation_engine", container)
        
        print("✅ ConversationEngine created successfully")
        
        # Try to start it
        await engine.start()
        print("✅ ConversationEngine started successfully")
        
        # Check if it has active features
        features = engine.get_active_features()
        print(f"🔧 Active features: {features}")
        
        # Check if bus client is connected
        if engine.bus_client:
            print("✅ Message bus client is connected")
        else:
            print("❌ Message bus client is NOT connected")
        
        # Stop the engine
        await engine.stop()
        print("✅ ConversationEngine stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ ConversationEngine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_conversation_engine())
    sys.exit(0 if success else 1)
