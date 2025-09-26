#!/usr/bin/env python3
"""
AICO Memory Intelligence Evaluator - Basic Usage Examples

This file demonstrates basic usage patterns for the memory evaluation framework.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_eval import (
    MemoryIntelligenceEvaluator,
    ScenarioLibrary,
    ConversationScenario,
    ConversationTurn
)


async def basic_evaluation_example():
    """Basic example: Run the comprehensive memory test"""
    
    print("🧠 Basic Memory Evaluation Example")
    print("=" * 50)
    
    # Initialize evaluator
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000",
        timeout_seconds=30
    )
    
    try:
        # Run the default comprehensive memory test
        result = await evaluator.run_comprehensive_evaluation()
        
        print(f"\n✅ Evaluation Complete!")
        print(f"Overall Score: {result.overall_score.percentage:.1f}%")
        print(f"Context Adherence: {result.context_adherence.percentage:.1f}%")
        print(f"Knowledge Retention: {result.knowledge_retention.percentage:.1f}%")
        print(f"Entity Extraction: {result.entity_extraction.percentage:.1f}%")
        
        return result
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return None


async def custom_scenario_example():
    """Example: Create and run a custom scenario"""
    
    print("\n🎯 Custom Scenario Example")
    print("=" * 50)
    
    # Create a custom scenario
    custom_scenario = ConversationScenario(
        name="simple_memory_test",
        description="Simple 3-turn memory test focusing on name retention",
        conversation_turns=[
            ConversationTurn(
                user_message="Hi, I'm Alice and I work as a data scientist at Google.",
                expected_entities={
                    "PERSON": ["Alice"],
                    "ORG": ["Google"]
                },
                expected_context_elements=["user_name_alice", "job_data_scientist", "company_google"],
                validation_rules=["should_acknowledge_name", "should_show_interest"],
                thread_expectation="new"
            ),
            ConversationTurn(
                user_message="I'm working on a machine learning project about natural language processing.",
                expected_context_elements=["ml_project", "nlp_focus"],
                should_remember_from_turns=[1],
                should_reference_entities=["Alice"],
                validation_rules=["should_remember_user_name", "should_show_technical_interest"],
                thread_expectation="continue"
            ),
            ConversationTurn(
                user_message="What was my name again? I want to make sure you remember.",
                expected_context_elements=["name_recall_test"],
                should_remember_from_turns=[1],
                should_reference_entities=["Alice"],
                validation_rules=["should_recall_name_alice", "should_demonstrate_memory"],
                thread_expectation="continue"
            )
        ],
        success_criteria={
            "context_adherence": 0.90,
            "knowledge_retention": 0.95,
            "overall_score": 0.85
        },
        tags=["simple", "name-retention", "3-turn"],
        estimated_duration_minutes=3,
        difficulty_level="easy"
    )
    
    # Initialize evaluator
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000"
    )
    
    try:
        # Run the custom scenario
        result = await evaluator.run_comprehensive_evaluation(
            custom_scenario=custom_scenario
        )
        
        print(f"\n✅ Custom Scenario Complete!")
        print(f"Scenario: {result.scenario_name}")
        print(f"Overall Score: {result.overall_score.percentage:.1f}%")
        
        # Check if it met success criteria
        met_criteria = (
            result.context_adherence.percentage >= 90.0 and
            result.knowledge_retention.percentage >= 95.0 and
            result.overall_score.percentage >= 85.0
        )
        
        print(f"Success Criteria Met: {'✅ Yes' if met_criteria else '❌ No'}")
        
        return result
        
    except Exception as e:
        print(f"❌ Custom scenario failed: {e}")
        return None


async def continuous_evaluation_example():
    """Example: Run continuous evaluation for system improvement"""
    
    print("\n🔄 Continuous Evaluation Example")
    print("=" * 50)
    
    # Initialize evaluator
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000"
    )
    
    try:
        # Run continuous evaluation with multiple scenarios
        scenarios = ["comprehensive_memory_test", "entity_extraction_intensive"]
        
        results = await evaluator.run_continuous_evaluation(
            scenarios=scenarios,
            iterations=3,
            delay_seconds=1.0  # Short delay for example
        )
        
        print(f"\n✅ Continuous Evaluation Complete!")
        print(f"Total Results: {len(results)}")
        
        # Calculate improvement trend
        if len(results) >= 2:
            first_score = results[0].overall_score.percentage
            last_score = results[-1].overall_score.percentage
            improvement = last_score - first_score
            
            print(f"Score Trend: {first_score:.1f}% → {last_score:.1f}% ({improvement:+.1f}%)")
            
        # Show performance trends
        trends = evaluator.get_performance_trends()
        print(f"Average Score: {trends['average_overall_score']:.1f}%")
        
        return results
        
    except Exception as e:
        print(f"❌ Continuous evaluation failed: {e}")
        return None


async def scenario_library_example():
    """Example: Explore available scenarios"""
    
    print("\n📚 Scenario Library Example")
    print("=" * 50)
    
    # Initialize scenario library
    library = ScenarioLibrary()
    
    # List all available scenarios
    scenarios = library.list_scenarios()
    print(f"Available Scenarios: {len(scenarios)}")
    
    for scenario_name in scenarios:
        scenario = library.get_scenario(scenario_name)
        if scenario:
            print(f"\n📋 {scenario_name}")
            print(f"   Description: {scenario.description}")
            print(f"   Turns: {len(scenario.conversation_turns)}")
            print(f"   Difficulty: {scenario.difficulty_level}")
            print(f"   Duration: ~{scenario.estimated_duration_minutes} min")
            
            # Show what it tests
            test_areas = []
            if scenario.tests_working_memory: test_areas.append("Working")
            if scenario.tests_episodic_memory: test_areas.append("Episodic")
            if scenario.tests_semantic_memory: test_areas.append("Semantic")
            if scenario.tests_semantic_memory_quality: test_areas.append("Memory Quality")
            if scenario.tests_entity_extraction: test_areas.append("Entities")
            
            print(f"   Tests: {', '.join(test_areas)}")
    
    # Get scenarios by difficulty
    easy_scenarios = library.get_scenarios_by_difficulty("easy")
    hard_scenarios = library.get_scenarios_by_difficulty("hard")
    
    print(f"\nEasy Scenarios: {len(easy_scenarios)}")
    print(f"Hard Scenarios: {len(hard_scenarios)}")
    
    # Get scenarios by tag
    entity_scenarios = library.get_scenarios_by_tag("entities")
    print(f"Entity-focused Scenarios: {len(entity_scenarios)}")


async def main():
    """Run all examples"""
    
    print("🚀 AICO Memory Intelligence Evaluator - Examples")
    print("=" * 60)
    
    try:
        # Example 1: Basic evaluation
        await basic_evaluation_example()
        
        # Example 2: Custom scenario
        await custom_scenario_example()
        
        # Example 3: Continuous evaluation
        await continuous_evaluation_example()
        
        # Example 4: Scenario library exploration
        await scenario_library_example()
        
        print(f"\n🎉 All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted")
    except Exception as e:
        print(f"\n❌ Examples failed: {e}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
