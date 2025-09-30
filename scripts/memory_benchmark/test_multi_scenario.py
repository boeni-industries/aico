#!/usr/bin/env python3
"""
Simple test script for multi-scenario memory evaluation
"""

import asyncio
import sys
from pathlib import Path

# Add shared path for AICO modules
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from .evaluator import MemoryIntelligenceEvaluator
from .scenarios import ScenarioLibrary

async def test_multi_scenario():
    """Test the multi-scenario evaluation system"""
    
    print("🧠 AICO Multi-Scenario Memory Evaluation Test")
    print("=" * 60)
    
    evaluator = MemoryIntelligenceEvaluator()
    library = ScenarioLibrary()
    
    try:
        # Get the default 3 diverse scenarios
        scenario_names = library.get_default_multi_scenario_set()
        
        print(f"📋 Testing {len(scenario_names)} diverse scenarios:")
        for i, name in enumerate(scenario_names, 1):
            scenario = library.get_scenario(name)
            print(f"  {i}. {name}")
            print(f"     📝 {scenario.description}")
            print(f"     🎯 Difficulty: {scenario.difficulty_level}")
            print(f"     💬 Turns: {len(scenario.conversation_turns)}")
        
        print(f"\n🚀 Starting evaluation...")
        
        # Run each scenario
        results = []
        for i, scenario_name in enumerate(scenario_names, 1):
            print(f"\n{'='*60}")
            print(f"📊 SCENARIO {i}/{len(scenario_names)}: {scenario_name}")
            print(f"{'='*60}")
            
            try:
                result = await evaluator.run_comprehensive_evaluation(scenario_name)
                results.append((scenario_name, result))
                
                print(f"\n✅ Scenario Complete: {scenario_name}")
                print(f"🎯 Overall Score: {result.overall_score.percentage:.1f}%")
                print(f"📈 Key Metrics:")
                print(f"  Context Adherence........ {result.context_adherence.percentage:6.1f}%")
                print(f"  Knowledge Retention...... {result.knowledge_retention.percentage:6.1f}%")
                print(f"  Entity Extraction........ {result.entity_extraction.percentage:6.1f}%")
                
            except Exception as e:
                print(f"❌ Scenario failed: {e}")
                continue
        
        # Calculate compound score
        if len(results) > 1:
            print(f"\n{'='*60}")
            print(f"📊 COMPOUND EVALUATION RESULTS")
            print(f"{'='*60}")
            
            total_score = sum(result.overall_score.percentage for _, result in results)
            compound_score = total_score / len(results)
            
            print(f"🎯 Compound Overall Score: {compound_score:.1f}%")
            print(f"📋 Individual Results:")
            for scenario_name, result in results:
                color = "✅" if result.overall_score.percentage >= 85 else "⚠️" if result.overall_score.percentage >= 70 else "❌"
                print(f"  {color} {scenario_name}: {result.overall_score.percentage:.1f}%")
        
        print(f"\n🎉 Multi-scenario evaluation complete!")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await evaluator.cleanup()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(test_multi_scenario())
    sys.exit(exit_code)
