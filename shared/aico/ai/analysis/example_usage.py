"""
Example usage of PersonalFactExtractor and SemanticMemoryStore integration.

This demonstrates how to extract and store personal facts from user messages
using the LLM-based fact extraction system.
"""

import asyncio
from aico.core.config import ConfigurationManager
from aico.ai.memory.semantic import SemanticMemoryStore
from backend.services.modelservice_client import ModelserviceClient


async def example_fact_extraction():
    """Example of extracting and storing personal facts"""
    
    # Initialize configuration
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    
    # Initialize semantic memory store
    semantic_store = SemanticMemoryStore(config)
    
    # Initialize modelservice client
    modelservice = ModelserviceClient(config)
    await modelservice.connect()
    
    # Inject modelservice dependency
    semantic_store.set_modelservice(modelservice)
    
    # Initialize the store
    await semantic_store.initialize()
    
    # Example user messages with facts
    test_messages = [
        {
            "user_id": "user123",
            "message": "Hi! My name is Sarah and I'm a vegetarian. I live in San Francisco.",
            "context": {"thread_id": "thread_001"}
        },
        {
            "user_id": "user123", 
            "message": "My birthday is March 15th, 1990. I work as a software engineer.",
            "context": {"thread_id": "thread_001"}
        },
        {
            "user_id": "user123",
            "message": "I'm feeling tired today, but the weather is nice.",
            "context": {"thread_id": "thread_001"}
        }
    ]
    
    # Extract and store facts from each message
    for msg_data in test_messages:
        print(f"\nProcessing message: {msg_data['message']}")
        
        facts_stored = await semantic_store.extract_and_store_facts(
            user_message=msg_data["message"],
            user_id=msg_data["user_id"],
            context=msg_data["context"]
        )
        
        print(f"Stored {facts_stored} facts")
    
    # Query for facts about the user
    print("\nQuerying for facts about Sarah:")
    results = await semantic_store.query("What do I know about Sarah?", max_results=10)
    
    for result in results:
        print(f"- {result['content']} (confidence: {result.get('similarity', 0.0):.2f})")
    
    # Cleanup
    await modelservice.disconnect()
    await semantic_store.cleanup()


if __name__ == "__main__":
    asyncio.run(example_fact_extraction())
