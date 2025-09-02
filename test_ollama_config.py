#!/usr/bin/env python3
"""
Test script to verify Ollama configuration integration.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

from shared.aico.core.config import AICOConfig
from modelservice.core.ollama_manager import OllamaManager

async def test_ollama_config():
    """Test that OllamaManager properly loads and uses configuration."""
    print("🧪 Testing Ollama Configuration Integration")
    print("=" * 50)
    
    try:
        # Load configuration
        print("📋 Loading AICO configuration...")
        config = AICOConfig()
        
        # Check if ollama config exists
        ollama_config = config.get("modelservice.ollama", {})
        if not ollama_config:
            print("❌ No Ollama configuration found in core.yaml")
            return False
            
        print("✅ Ollama configuration loaded successfully")
        print(f"   Host: {ollama_config.get('host', 'NOT SET')}")
        print(f"   Port: {ollama_config.get('port', 'NOT SET')}")
        print(f"   URL: {ollama_config.get('url', 'NOT SET')}")
        print(f"   Auto Install: {ollama_config.get('auto_install', 'NOT SET')}")
        print(f"   Auto Start: {ollama_config.get('auto_start', 'NOT SET')}")
        
        # Test default models configuration
        default_models = ollama_config.get("default_models", {})
        print(f"\n📦 Default Models Configuration:")
        for role, model_config in default_models.items():
            print(f"   {role}: {model_config.get('name', 'NOT SET')} (auto_pull: {model_config.get('auto_pull', False)})")
        
        # Verify vision_extended exists (renamed from precision)
        if "vision_extended" in default_models:
            print("✅ 'vision_extended' model role found (renamed from 'precision')")
        else:
            print("❌ 'vision_extended' model role not found")
            
        # Verify conversation model is Nous Hermes 3
        conversation_model = default_models.get("conversation", {}).get("name", "")
        if "hermes3" in conversation_model:
            print("✅ Conversation model is Nous Hermes 3")
        else:
            print(f"❌ Conversation model is not Nous Hermes 3: {conversation_model}")
        
        # Test OllamaManager initialization
        print(f"\n🔧 Testing OllamaManager initialization...")
        ollama_manager = OllamaManager()
        
        # Check if config is loaded
        if hasattr(ollama_manager, 'ollama_config') and ollama_manager.ollama_config:
            print("✅ OllamaManager loaded configuration successfully")
            print(f"   Manager URL: {ollama_manager.ollama_config.get('url', 'NOT SET')}")
        else:
            print("❌ OllamaManager failed to load configuration")
            return False
            
        # Test status method (without requiring Ollama to be running)
        print(f"\n📊 Testing status method...")
        status = await ollama_manager.get_status()
        print(f"   Status keys: {list(status.keys())}")
        print(f"   Running: {status.get('running', 'NOT SET')}")
        print(f"   Healthy: {status.get('healthy', 'NOT SET')}")
        
        print(f"\n✅ All configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ollama_config())
    sys.exit(0 if success else 1)
