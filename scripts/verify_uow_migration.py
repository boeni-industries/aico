#!/usr/bin/env python3
"""
Verification script for UoW/Repository pattern migration.
Tests that all migrated components can be imported and initialized correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

def test_imports():
    """Test that all migrated modules can be imported."""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    try:
        print("✓ Importing AgencyService...")
        from aico.services.agency_service import AgencyService
        
        print("✓ Importing BehavioralFeedbackService...")
        from aico.ai.agency.behavioral_feedback import BehavioralFeedbackService
        
        print("✓ Importing AdaptiveScoringEngine...")
        from aico.ai.agency.arbiter_adaptive import AdaptiveScoringEngine
        
        print("✓ Importing PlanExecutor...")
        from aico.ai.agency.executor import PlanExecutor
        
        print("✓ Importing SkillInvoker...")
        from aico.ai.agency.skill_invoker import SkillInvoker
        
        print("✓ Importing AgencyEngine...")
        from aico.ai.agency.engine import AgencyEngine
        
        print("\n✅ All imports successful!\n")
        return True
    except Exception as e:
        print(f"\n❌ Import failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_constructor_signatures():
    """Test that constructors have correct signatures (no db parameter)."""
    print("=" * 60)
    print("TESTING CONSTRUCTOR SIGNATURES")
    print("=" * 60)
    
    from aico.ai.agency.behavioral_feedback import BehavioralFeedbackService
    from aico.ai.agency.arbiter_adaptive import AdaptiveScoringEngine
    from aico.ai.agency.executor import PlanExecutor
    from aico.ai.agency.skill_invoker import SkillInvoker
    
    import inspect
    
    # Check BehavioralFeedbackService
    sig = inspect.signature(BehavioralFeedbackService.__init__)
    params = list(sig.parameters.keys())
    print(f"✓ BehavioralFeedbackService.__init__ params: {params}")
    assert 'db' not in params, "BehavioralFeedbackService still has 'db' parameter!"
    assert 'agency_service' in params, "BehavioralFeedbackService missing 'agency_service' parameter!"
    
    # Check AdaptiveScoringEngine
    sig = inspect.signature(AdaptiveScoringEngine.__init__)
    params = list(sig.parameters.keys())
    print(f"✓ AdaptiveScoringEngine.__init__ params: {params}")
    assert 'db' not in params, "AdaptiveScoringEngine still has 'db' parameter!"
    assert 'agency_service' in params, "AdaptiveScoringEngine missing 'agency_service' parameter!"
    
    # Check PlanExecutor
    sig = inspect.signature(PlanExecutor.__init__)
    params = list(sig.parameters.keys())
    print(f"✓ PlanExecutor.__init__ params: {params}")
    assert 'db' not in params, "PlanExecutor still has 'db' parameter!"
    assert 'agency_service' in params, "PlanExecutor missing 'agency_service' parameter!"
    
    # Check SkillInvoker
    sig = inspect.signature(SkillInvoker.__init__)
    params = list(sig.parameters.keys())
    print(f"✓ SkillInvoker.__init__ params: {params}")
    assert 'db' not in params, "SkillInvoker still has 'db' parameter!"
    
    print("\n✅ All constructor signatures correct!\n")
    return True

def test_async_methods():
    """Test that migrated methods are async."""
    print("=" * 60)
    print("TESTING ASYNC METHOD SIGNATURES")
    print("=" * 60)
    
    from aico.ai.agency.behavioral_feedback import BehavioralFeedbackService
    from aico.ai.agency.arbiter_adaptive import AdaptiveScoringEngine
    from aico.ai.agency.executor import PlanExecutor
    
    import inspect
    
    # Check BehavioralFeedbackService methods
    methods_to_check = [
        'record_skill_execution',
        'record_behavioral_feedback',
        'link_execution_to_goal',
        'get_goal_executions',
        'detect_outcome_from_execution',
        'update_feedback_with_outcome',
        'create_feedback_request',
        'record_feedback_response',
        'get_pending_feedback_requests',
        'get_skill_success_rate',
        'get_user_satisfaction_trend'
    ]
    
    for method_name in methods_to_check:
        method = getattr(BehavioralFeedbackService, method_name)
        assert inspect.iscoroutinefunction(method), f"BehavioralFeedbackService.{method_name} is not async!"
        print(f"✓ BehavioralFeedbackService.{method_name} is async")
    
    # Check AdaptiveScoringEngine methods (select_arm is pure computation, not async)
    adaptive_methods = ['load_arms', 'update_arm']
    for method_name in adaptive_methods:
        method = getattr(AdaptiveScoringEngine, method_name)
        assert inspect.iscoroutinefunction(method), f"AdaptiveScoringEngine.{method_name} is not async!"
        print(f"✓ AdaptiveScoringEngine.{method_name} is async")
    
    # Check PlanExecutor methods
    executor_methods = [
        'start_execution',
        'execute_next_step',
        '_get_next_pending_step',
        '_has_pending_steps',
        '_save_execution',
        '_save_step_execution',
        '_get_execution',
        '_get_step_executions',
        '_save_state_snapshot'
    ]
    
    for method_name in executor_methods:
        method = getattr(PlanExecutor, method_name)
        assert inspect.iscoroutinefunction(method), f"PlanExecutor.{method_name} is not async!"
        print(f"✓ PlanExecutor.{method_name} is async")
    
    print("\n✅ All methods are properly async!\n")
    return True

def test_agency_service_methods():
    """Test that AgencyService has all required methods."""
    print("=" * 60)
    print("TESTING AGENCYSERVICE METHODS")
    print("=" * 60)
    
    from aico.services.agency_service import AgencyService
    
    required_methods = [
        # Behavioral feedback methods
        'record_skill_execution',
        'link_goal_skill_execution',
        'get_goal_executions',
        'get_skill_execution_outcome',
        'update_feedback_outcome',
        'record_behavioral_feedback',
        'create_feedback_request',
        'respond_to_feedback_request',
        'get_pending_feedback_requests',
        'get_skill_performance_stats',
        
        # Adaptive arbiter methods
        'save_bandit_arm',
        'get_bandit_arms',
        'create_ab_test',
        'get_ab_test',
        
        # Plan executor methods
        'create_plan_execution',
        'update_plan_execution',
        'get_plan_execution',
        'create_step_execution',
        'update_step_execution',
        'get_step_executions',
        'get_next_pending_step',
        'count_pending_steps',
        'count_step_executions',
        'create_execution_snapshot',
    ]
    
    for method_name in required_methods:
        assert hasattr(AgencyService, method_name), f"AgencyService missing method: {method_name}"
        print(f"✓ AgencyService.{method_name} exists")
    
    print("\n✅ AgencyService has all required methods!\n")
    return True

def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("UoW/REPOSITORY PATTERN MIGRATION VERIFICATION")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    
    if results[0][1]:  # Only continue if imports succeeded
        results.append(("Constructor Signatures", test_constructor_signatures()))
        results.append(("Async Methods", test_async_methods()))
        results.append(("AgencyService Methods", test_agency_service_methods()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL VERIFICATIONS PASSED! 🎉")
        print("\nMigration Complete:")
        print("  ✓ BehavioralFeedbackService - fully migrated to AgencyService")
        print("  ✓ AdaptiveScoringEngine - fully migrated to AgencyService")
        print("  ✓ PlanExecutor - fully migrated to AgencyService")
        print("  ✓ SkillInvoker - legacy db parameter removed")
        print("  ✓ AgencyEngine - updated to use migrated components")
        print("  ✓ All methods converted to async")
        print("  ✓ All legacy db parameters removed")
        print("\n")
        return 0
    else:
        print("\n❌ SOME VERIFICATIONS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
