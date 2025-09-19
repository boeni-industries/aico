#!/usr/bin/env python3
"""
Test script for sentiment analysis functionality.

This script tests the complete sentiment analysis pipeline:
1. TransformersManager initialization
2. Model downloading and loading
3. Sentiment analysis processing
4. Integration with modelservice client
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aico.core.config import ConfigurationManager
from modelservice.core.transformers_manager import TransformersManager


async def test_transformers_manager():
    """Test TransformersManager directly."""
    print("🧪 Testing TransformersManager...")
    
    # Initialize configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Create TransformersManager
    transformers_manager = TransformersManager(config_manager)
    
    print("📥 Initializing models (this may take a few minutes for first run)...")
    success = await transformers_manager.initialize_models()
    
    if not success:
        print("❌ Failed to initialize models")
        return False
    
    print("✅ Models initialized successfully!")
    
    # Test sentiment analysis
    test_texts = [
        "I love this new feature! It's amazing and works perfectly.",
        "This is terrible and doesn't work at all. Very disappointed.",
        "The weather is okay today, nothing special.",
        "I had a positive exchange with AICO, here are the results!"
    ]
    
    print("\n🔍 Testing sentiment analysis...")
    
    for text in test_texts:
        print(f"\nText: {text[:50]}...")
        
        try:
            # Get sentiment pipeline
            pipeline = await transformers_manager.get_pipeline("sentiment_multilingual")
            
            if pipeline is None:
                print("❌ Failed to get sentiment pipeline")
                continue
            
            # Analyze sentiment
            result = pipeline(text)
            
            if result and len(result) > 0:
                sentiment_result = result[0]
                label = sentiment_result['label'].lower()
                confidence = sentiment_result['score']
                
                print(f"Raw label: '{sentiment_result['label']}' -> '{label}'")
                
                # Map model labels to standard format (same as zmq_handlers.py)
                # nlptown/bert-base-multilingual-uncased-sentiment uses star ratings
                if label in ['5 stars', '4 stars']:
                    sentiment = 'positive'
                elif label in ['1 star', '2 stars']:
                    sentiment = 'negative'
                elif label in ['3 stars']:
                    sentiment = 'neutral'
                else:
                    # Fallback for other models that might use different labels
                    if label in ['positive', 'pos']:
                        sentiment = 'positive'
                    elif label in ['negative', 'neg']:
                        sentiment = 'negative'
                    else:
                        sentiment = 'neutral'
                
                print(f"✅ Sentiment: {sentiment} (confidence: {confidence:.3f})")
            else:
                print("❌ No sentiment result returned")
                
        except Exception as e:
            print(f"❌ Error analyzing sentiment: {e}")
    
    # Test model info
    print("\n📊 Model Information:")
    model_info = transformers_manager.get_model_info()
    
    print(f"Available models: {len(model_info['available_models'])}")
    for name, info in model_info['available_models'].items():
        status = "✅ Required" if info['required'] else "⚪ Optional"
        print(f"  {status} {name}: {info['description']}")
    
    print(f"Loaded models: {model_info['loaded_models']}")
    print(f"Memory config: {model_info['memory_config']}")
    
    # Test health check
    print("\n🏥 Health Check:")
    health = await transformers_manager.health_check()
    print(f"Status: {health['status']}")
    print(f"Transformers version: {health.get('transformers_version', 'N/A')}")
    print(f"Required models: {health.get('required_models', 0)}")
    print(f"Available models: {health.get('available_models', 0)}")
    
    return True


async def test_modelservice_integration():
    """Test integration with modelservice client (if running)."""
    print("\n🔗 Testing modelservice integration...")
    
    try:
        from backend.services.modelservice_client import get_modelservice_client
        from aico.core.config import ConfigurationManager
        
        config_manager = ConfigurationManager()
        config_manager.initialize()
        
        client = get_modelservice_client(config_manager)
        
        # Test sentiment analysis via modelservice
        test_text = "I had a positive exchange with AICO!"
        
        print(f"Testing via modelservice: {test_text}")
        
        result = await client.get_sentiment_analysis(test_text)
        
        if result.get('success'):
            data = result.get('data', {})
            sentiment = data.get('sentiment', 'unknown')
            confidence = data.get('confidence', 0.0)
            print(f"✅ Modelservice result: {sentiment} (confidence: {confidence:.3f})")
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Modelservice error: {error}")
            
    except Exception as e:
        print(f"⚠️ Modelservice integration test failed (service may not be running): {e}")


async def main():
    """Main test function."""
    print("🚀 AICO Sentiment Analysis Test")
    print("=" * 50)
    
    # Test TransformersManager directly
    success = await test_transformers_manager()
    
    if not success:
        print("\n❌ TransformersManager test failed")
        return 1
    
    # Test modelservice integration
    await test_modelservice_integration()
    
    print("\n🎉 All tests completed!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
