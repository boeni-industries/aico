#!/usr/bin/env python3
"""
AICO Memory Intelligence Evaluator - Advanced Usage Examples

This file demonstrates advanced usage patterns including custom metrics,
specialized scenarios, and integration with CI/CD pipelines.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_eval import (
    MemoryIntelligenceEvaluator,
    ConversationScenario,
    ConversationTurn,
    MemoryMetrics,
    MetricScore,
    EvaluationResult
)


class CustomMemoryMetrics(MemoryMetrics):
    """Extended metrics class with custom evaluation methods"""
    
    async def calculate_emotional_intelligence(self, session) -> MetricScore:
        """
        Custom metric: Evaluate AI's emotional intelligence and empathy
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        emotional_scores = []
        details = {"emotional_responses": [], "empathy_indicators": 0}
        
        # Emotional keywords that indicate empathy and emotional awareness
        empathy_keywords = [
            "understand", "feel", "sorry", "excited", "nervous", "happy",
            "congratulations", "empathize", "support", "comfort"
        ]
        
        for i, turn in enumerate(session.conversation_log):
            ai_response = turn.get("ai_response", "").lower()
            user_message = turn.get("user_message", "").lower()
            
            # Check if user expressed emotion
            user_emotions = []
            if any(word in user_message for word in ["excited", "nervous", "worried", "happy", "sad"]):
                user_emotions.append("emotion_detected")
                
            # Check AI's emotional response
            empathy_score = 0.0
            empathy_found = []
            
            for keyword in empathy_keywords:
                if keyword in ai_response:
                    empathy_score += 0.1
                    empathy_found.append(keyword)
                    details["empathy_indicators"] += 1
                    
            # Bonus for appropriate emotional response to user's emotional state
            if user_emotions and empathy_found:
                empathy_score += 0.3
                
            emotional_scores.append(min(empathy_score, 1.0))
            
            details["emotional_responses"].append({
                "turn": i + 1,
                "user_emotions": user_emotions,
                "ai_empathy_keywords": empathy_found,
                "empathy_score": empathy_score
            })
            
        overall_score = sum(emotional_scores) / len(emotional_scores) if emotional_scores else 0.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Emotional intelligence across {len(emotional_scores)} turns"
        )
        
    async def calculate_technical_accuracy(self, session) -> MetricScore:
        """
        Custom metric: Evaluate technical accuracy in domain-specific conversations
        """
        if not session.conversation_log:
            return MetricScore(0.0, explanation="No conversation data available")
            
        technical_scores = []
        details = {"technical_terms": [], "accuracy_checks": []}
        
        # Technical terms that should be handled accurately
        technical_terms = {
            "software engineer": ["programming", "code", "development"],
            "machine learning": ["ai", "model", "algorithm", "data"],
            "data scientist": ["analysis", "statistics", "python", "data"]
        }
        
        for i, turn in enumerate(session.conversation_log):
            ai_response = turn.get("ai_response", "").lower()
            user_message = turn.get("user_message", "").lower()
            
            turn_score = 1.0  # Start with perfect score
            accuracy_issues = []
            
            # Check for technical term usage
            for term, related_words in technical_terms.items():
                if term in user_message:
                    # AI should use related technical vocabulary
                    related_found = sum(1 for word in related_words if word in ai_response)
                    if related_found == 0:
                        turn_score -= 0.2
                        accuracy_issues.append(f"Missing technical context for {term}")
                    else:
                        details["technical_terms"].extend([word for word in related_words if word in ai_response])
                        
            technical_scores.append(max(turn_score, 0.0))
            
            details["accuracy_checks"].append({
                "turn": i + 1,
                "technical_score": turn_score,
                "issues": accuracy_issues
            })
            
        overall_score = sum(technical_scores) / len(technical_scores) if technical_scores else 1.0
        
        return MetricScore(
            score=overall_score,
            details=details,
            explanation=f"Technical accuracy across {len(technical_scores)} turns"
        )


async def custom_metrics_example():
    """Example: Using custom metrics for specialized evaluation"""
    
    print("🔬 Custom Metrics Example")
    print("=" * 50)
    
    # Create evaluator with custom metrics
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000"
    )
    
    # Replace default metrics with custom ones
    evaluator.metrics = CustomMemoryMetrics()
    
    # Create a scenario that tests emotional intelligence
    emotional_scenario = ConversationScenario(
        name="emotional_intelligence_test",
        description="Test AI's emotional intelligence and empathy",
        conversation_turns=[
            ConversationTurn(
                user_message="Hi, I'm really nervous about starting my new job tomorrow. I've never worked at such a big company before.",
                expected_context_elements=["nervous_emotion", "new_job", "big_company"],
                validation_rules=["should_acknowledge_nervousness", "should_provide_support"],
                thread_expectation="new"
            ),
            ConversationTurn(
                user_message="Thanks for the encouragement! I'm also excited though. It's a software engineering role at TechCorp.",
                expected_entities={"ORG": ["TechCorp"]},
                expected_context_elements=["excited_emotion", "software_engineering"],
                should_remember_from_turns=[1],
                validation_rules=["should_acknowledge_excitement", "should_show_technical_interest"],
                thread_expectation="continue"
            ),
            ConversationTurn(
                user_message="Do you think I should be worried about the technical interview process?",
                expected_context_elements=["technical_interview", "worry"],
                should_remember_from_turns=[1, 2],
                validation_rules=["should_provide_technical_advice", "should_be_reassuring"],
                thread_expectation="continue"
            )
        ],
        tags=["emotional", "technical", "empathy"],
        difficulty_level="medium"
    )
    
    try:
        # Run evaluation with custom scenario
        result = await evaluator.run_comprehensive_evaluation(
            custom_scenario=emotional_scenario
        )
        
        # Calculate custom metrics
        emotional_intelligence = await evaluator.metrics.calculate_emotional_intelligence(
            evaluator.current_session
        )
        technical_accuracy = await evaluator.metrics.calculate_technical_accuracy(
            evaluator.current_session
        )
        
        print(f"\n✅ Custom Metrics Evaluation Complete!")
        print(f"Overall Score: {result.overall_score.percentage:.1f}%")
        print(f"Emotional Intelligence: {emotional_intelligence.percentage:.1f}%")
        print(f"Technical Accuracy: {technical_accuracy.percentage:.1f}%")
        
        # Show detailed emotional intelligence analysis
        if emotional_intelligence.details:
            empathy_indicators = emotional_intelligence.details.get("empathy_indicators", 0)
            print(f"Empathy Indicators Found: {empathy_indicators}")
            
        return result
        
    except Exception as e:
        print(f"❌ Custom metrics evaluation failed: {e}")
        return None


async def performance_benchmarking_example():
    """Example: Performance benchmarking and stress testing"""
    
    print("\n⚡ Performance Benchmarking Example")
    print("=" * 50)
    
    # Create a high-load scenario for performance testing
    stress_scenario = ConversationScenario(
        name="performance_stress_test",
        description="High-load scenario with complex entities and rapid-fire questions",
        conversation_turns=[
            ConversationTurn(
                user_message="I'm organizing a global conference in New York City from March 15-17, 2024. We have speakers from Google, Microsoft, Apple, Amazon, Meta, Tesla, Netflix, and Spotify. The main venue is Madison Square Garden, with overflow at the Javits Center.",
                expected_entities={
                    "GPE": ["New York City"],
                    "DATE": ["March 15-17, 2024"],
                    "ORG": ["Google", "Microsoft", "Apple", "Amazon", "Meta", "Tesla", "Netflix", "Spotify", "Madison Square Garden", "Javits Center"]
                },
                thread_expectation="new"
            ),
            ConversationTurn(
                user_message="We need catering for 5,000 attendees including 1,200 vegetarians, 800 vegans, 300 gluten-free, and 150 kosher meals. Budget is $500,000. Can you suggest NYC caterers who can handle this volume?",
                expected_entities={
                    "CARDINAL": ["5,000", "1,200", "800", "300", "150"],
                    "MONEY": ["$500,000"],
                    "GPE": ["NYC"]
                },
                should_remember_from_turns=[1],
                thread_expectation="continue"
            ),
            ConversationTurn(
                user_message="Also, we need transportation for VIP speakers: Sundar Pichai from Google, Satya Nadella from Microsoft, Tim Cook from Apple, Andy Jassy from Amazon, and Mark Zuckerberg from Meta. They're arriving at JFK, LaGuardia, and Newark airports on different days.",
                expected_entities={
                    "PERSON": ["Sundar Pichai", "Satya Nadella", "Tim Cook", "Andy Jassy", "Mark Zuckerberg"],
                    "FAC": ["JFK", "LaGuardia", "Newark"]
                },
                should_remember_from_turns=[1],
                thread_expectation="continue"
            )
        ],
        success_criteria={
            "entity_extraction": 0.90,
            "performance_metrics": {"average_response_time_ms": 3000}
        },
        tags=["performance", "stress", "high-volume", "entities"],
        difficulty_level="expert"
    )
    
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000",
        timeout_seconds=45  # Longer timeout for stress test
    )
    
    try:
        # Run performance benchmark
        start_time = datetime.now()
        result = await evaluator.run_comprehensive_evaluation(
            custom_scenario=stress_scenario
        )
        end_time = datetime.now()
        
        total_duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Performance Benchmark Complete!")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Average Response Time: {result.performance_metrics.get('average_response_time_ms', 0):.0f}ms")
        print(f"Max Response Time: {result.performance_metrics.get('max_response_time_ms', 0):.0f}ms")
        print(f"Entity Extraction: {result.entity_extraction.percentage:.1f}%")
        
        # Performance analysis
        avg_response_time = result.performance_metrics.get('average_response_time_ms', 0)
        if avg_response_time > 3000:
            print("⚠️  Performance Warning: Response time exceeds 3000ms threshold")
        else:
            print("✅ Performance: Within acceptable limits")
            
        return result
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return None


async def ci_cd_integration_example():
    """Example: CI/CD integration with automated pass/fail criteria"""
    
    print("\n🔄 CI/CD Integration Example")
    print("=" * 50)
    
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000"
    )
    
    # Define strict pass/fail criteria for CI/CD
    ci_criteria = {
        "overall_score_min": 85.0,
        "context_adherence_min": 85.0,
        "knowledge_retention_min": 90.0,
        "entity_extraction_min": 80.0,
        "max_response_time_ms": 2500,
        "max_errors": 0
    }
    
    try:
        # Run comprehensive evaluation
        result = await evaluator.run_comprehensive_evaluation()
        
        # Check CI/CD criteria
        checks = {
            "overall_score": result.overall_score.percentage >= ci_criteria["overall_score_min"],
            "context_adherence": result.context_adherence.percentage >= ci_criteria["context_adherence_min"],
            "knowledge_retention": result.knowledge_retention.percentage >= ci_criteria["knowledge_retention_min"],
            "entity_extraction": result.entity_extraction.percentage >= ci_criteria["entity_extraction_min"],
            "response_time": result.performance_metrics.get('average_response_time_ms', 0) <= ci_criteria["max_response_time_ms"],
            "error_count": len(result.errors) <= ci_criteria["max_errors"]
        }
        
        all_passed = all(checks.values())
        
        print(f"\n📊 CI/CD Quality Gate Results:")
        print(f"{'='*40}")
        
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check_name:.<25} {status}")
            
        print(f"{'='*40}")
        print(f"Overall Result: {'✅ PASS' if all_passed else '❌ FAIL'}")
        
        # Generate CI/CD report
        ci_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_result": "PASS" if all_passed else "FAIL",
            "criteria": ci_criteria,
            "results": {
                "overall_score": result.overall_score.percentage,
                "context_adherence": result.context_adherence.percentage,
                "knowledge_retention": result.knowledge_retention.percentage,
                "entity_extraction": result.entity_extraction.percentage,
                "average_response_time_ms": result.performance_metrics.get('average_response_time_ms', 0),
                "error_count": len(result.errors)
            },
            "checks": checks,
            "session_id": result.session_id
        }
        
        # Save CI/CD report
        ci_report_file = Path("ci_cd_memory_report.json")
        with open(ci_report_file, "w") as f:
            json.dump(ci_report, f, indent=2)
            
        print(f"\n📄 CI/CD report saved: {ci_report_file}")
        
        # Return appropriate exit code for CI/CD
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"❌ CI/CD evaluation failed: {e}")
        
        # Generate failure report
        failure_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_result": "ERROR",
            "error": str(e),
            "criteria": ci_criteria
        }
        
        with open("ci_cd_memory_report.json", "w") as f:
            json.dump(failure_report, f, indent=2)
            
        return 2  # Error exit code


async def regression_testing_example():
    """Example: Regression testing to ensure memory system stability"""
    
    print("\n🔍 Regression Testing Example")
    print("=" * 50)
    
    evaluator = MemoryIntelligenceEvaluator(
        backend_url="http://localhost:8000"
    )
    
    # Run multiple scenarios to check for regressions
    regression_scenarios = [
        "comprehensive_memory_test",
        "entity_extraction_intensive", 
        "thread_management_test"
    ]
    
    baseline_scores = {
        "comprehensive_memory_test": 85.0,
        "entity_extraction_intensive": 80.0,
        "thread_management_test": 90.0
    }
    
    regression_results = []
    
    try:
        for scenario_name in regression_scenarios:
            print(f"\n🧪 Testing scenario: {scenario_name}")
            
            result = await evaluator.run_comprehensive_evaluation(scenario_name)
            
            baseline = baseline_scores.get(scenario_name, 80.0)
            current_score = result.overall_score.percentage
            regression = current_score < (baseline - 5.0)  # 5% tolerance
            
            regression_result = {
                "scenario": scenario_name,
                "baseline_score": baseline,
                "current_score": current_score,
                "difference": current_score - baseline,
                "regression_detected": regression,
                "status": "REGRESSION" if regression else "STABLE"
            }
            
            regression_results.append(regression_result)
            
            status_icon = "⚠️" if regression else "✅"
            print(f"   {status_icon} {scenario_name}: {current_score:.1f}% (baseline: {baseline:.1f}%)")
            
        # Summary
        regressions_found = sum(1 for r in regression_results if r["regression_detected"])
        
        print(f"\n📊 Regression Testing Summary:")
        print(f"   Scenarios Tested: {len(regression_results)}")
        print(f"   Regressions Found: {regressions_found}")
        print(f"   Overall Status: {'⚠️ REGRESSIONS DETECTED' if regressions_found > 0 else '✅ STABLE'}")
        
        # Save regression report
        regression_report = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(regression_results),
            "regressions_found": regressions_found,
            "overall_status": "REGRESSION" if regressions_found > 0 else "STABLE",
            "results": regression_results
        }
        
        with open("regression_test_report.json", "w") as f:
            json.dump(regression_report, f, indent=2)
            
        return regression_results
        
    except Exception as e:
        print(f"❌ Regression testing failed: {e}")
        return None


async def main():
    """Run all advanced examples"""
    
    print("🚀 AICO Memory Intelligence Evaluator - Advanced Examples")
    print("=" * 70)
    
    try:
        # Example 1: Custom metrics
        await custom_metrics_example()
        
        # Example 2: Performance benchmarking
        await performance_benchmarking_example()
        
        # Example 3: CI/CD integration
        ci_exit_code = await ci_cd_integration_example()
        print(f"CI/CD Exit Code: {ci_exit_code}")
        
        # Example 4: Regression testing
        await regression_testing_example()
        
        print(f"\n🎉 All advanced examples completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Advanced examples interrupted")
    except Exception as e:
        print(f"\n❌ Advanced examples failed: {e}")


if __name__ == "__main__":
    # Run advanced examples
    asyncio.run(main())
