#!/usr/bin/env python3
"""
Debug script to check what labels the sentiment model actually returns.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aico.core.config import ConfigurationManager
from modelservice.core.transformers_manager import TransformersManager


async def debug_sentiment_labels():
    """Debug the actual labels returned by the sentiment model."""
    print("🔍 Debugging Sentiment Model Labels")
    print("=" * 50)
    
    # Initialize configuration
    config_manager = ConfigurationManager()
    config_manager.initialize()
    
    # Create TransformersManager
    transformers_manager = TransformersManager(config_manager)
    
    # Initialize models
    await transformers_manager.initialize_models()
    
    # Get sentiment pipeline
    pipeline = await transformers_manager.get_pipeline("sentiment_multilingual")
    
    if pipeline is None:
        print("❌ Failed to get sentiment pipeline")
        return
    
    # Test texts with clear sentiments
    test_texts = [
        "I absolutely love this! It's fantastic and amazing!",
        "This is terrible, awful, and completely broken. I hate it!",
        "This is okay, nothing special.",
        "Great job! Excellent work! Perfect!",
        "Horrible experience. Very disappointed and angry.",
    ]
    
    print("\n🧪 Testing sentiment analysis with debug info:")
    
    for text in test_texts:
        print(f"\nText: {text}")
        
        # Get raw result
        result = pipeline(text)
        print(f"Raw result: {result}")
        
        if result and len(result) > 0:
            sentiment_result = result[0]
            label = sentiment_result['label']
            confidence = sentiment_result['score']
            
            print(f"Label: '{label}' (type: {type(label)})")
            print(f"Confidence: {confidence}")
            print(f"Label lower: '{label.lower()}'")
            
            # Current mapping logic
            label_lower = label.lower()
            if label_lower in ['positive', 'pos']:
                mapped = 'positive'
            elif label_lower in ['negative', 'neg']:
                mapped = 'negative'
            else:
                mapped = 'neutral'
            
            print(f"Current mapping: '{label}' -> '{mapped}'")
    
    # Test with return_all_scores=True to see all possible labels
    print("\n🔍 Testing with all scores to see possible labels:")
    
    try:
        from transformers import pipeline as transformers_pipeline
        
        # Create pipeline with all scores
        debug_pipeline = transformers_pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
            return_all_scores=True
        )
        
        test_text = "I love this!"
        all_results = debug_pipeline(test_text)
        print(f"\nAll possible labels for '{test_text}':")
        for result in all_results:
            print(f"  {result['label']}: {result['score']:.3f}")
            
    except Exception as e:
        print(f"Error getting all scores: {e}")


if __name__ == "__main__":
    asyncio.run(debug_sentiment_labels())
