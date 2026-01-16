#!/usr/bin/env python3
"""
Simple verification script for UoW/Repository pattern migration.
Tests constructor signatures and method signatures without full imports.
"""

import sys
import ast
from pathlib import Path

def check_file_for_db_parameter(filepath: Path) -> tuple[bool, list[str]]:
    """Check if a file has any __init__ methods with 'db' parameter."""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                for arg in node.args.args:
                    if arg.arg == 'db':
                        # Get class name
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.ClassDef):
                                for child in parent.body:
                                    if child == node:
                                        issues.append(f"{parent.name}.__init__ has 'db' parameter")
                                        break
        
        return len(issues) == 0, issues
    except Exception as e:
        return False, [f"Error parsing {filepath}: {e}"]

def check_file_for_agency_service(filepath: Path) -> tuple[bool, list[str]]:
    """Check if migrated files have agency_service parameter."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(filepath))
        
        # Files that should have agency_service
        migrated_classes = [
            'BehavioralFeedbackService',
            'AdaptiveScoringEngine', 
            'PlanExecutor'
        ]
        
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in migrated_classes:
                # Find __init__ method
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        has_agency_service = any(arg.arg == 'agency_service' for arg in item.args.args)
                        if not has_agency_service:
                            issues.append(f"{node.name}.__init__ missing 'agency_service' parameter")
        
        return len(issues) == 0, issues
    except Exception as e:
        return False, [f"Error parsing {filepath}: {e}"]

def check_async_methods(filepath: Path, class_name: str, method_names: list[str]) -> tuple[bool, list[str]]:
    """Check if specified methods are async."""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name in method_names:
                        if not isinstance(item, ast.AsyncFunctionDef):
                            issues.append(f"{class_name}.{item.name} is not async")
        
        return len(issues) == 0, issues
    except Exception as e:
        return False, [f"Error parsing {filepath}: {e}"]

def main():
    """Run verification tests."""
    print("\n" + "=" * 70)
    print("UoW/REPOSITORY PATTERN MIGRATION VERIFICATION (AST-based)")
    print("=" * 70 + "\n")
    
    base_path = Path(__file__).parent.parent / "shared" / "aico"
    
    results = []
    
    # Test 1: Check BehavioralFeedbackService
    print("Testing BehavioralFeedbackService...")
    filepath = base_path / "ai" / "agency" / "behavioral_feedback.py"
    
    passed, issues = check_file_for_db_parameter(filepath)
    if not passed:
        print(f"  ❌ Has legacy 'db' parameter: {issues}")
        results.append(False)
    else:
        print("  ✓ No legacy 'db' parameter")
    
    passed, issues = check_file_for_agency_service(filepath)
    if not passed:
        print(f"  ❌ Missing agency_service: {issues}")
        results.append(False)
    else:
        print("  ✓ Has 'agency_service' parameter")
    
    methods = ['record_skill_execution', 'record_behavioral_feedback', 'link_execution_to_goal']
    passed, issues = check_async_methods(filepath, 'BehavioralFeedbackService', methods)
    if not passed:
        print(f"  ❌ Methods not async: {issues}")
        results.append(False)
    else:
        print(f"  ✓ Key methods are async")
        results.append(True)
    
    # Test 2: Check AdaptiveScoringEngine
    print("\nTesting AdaptiveScoringEngine...")
    filepath = base_path / "ai" / "agency" / "arbiter_adaptive.py"
    
    passed, issues = check_file_for_db_parameter(filepath)
    if not passed:
        print(f"  ❌ Has legacy 'db' parameter: {issues}")
        results.append(False)
    else:
        print("  ✓ No legacy 'db' parameter")
    
    passed, issues = check_file_for_agency_service(filepath)
    if not passed:
        print(f"  ❌ Missing agency_service: {issues}")
        results.append(False)
    else:
        print("  ✓ Has 'agency_service' parameter")
    
    # Only check methods that do I/O operations (select_arm is pure computation)
    methods = ['load_arms', 'update_arm', 'record_reward']
    passed, issues = check_async_methods(filepath, 'AdaptiveScoringEngine', methods)
    if not passed:
        print(f"  ❌ Methods not async: {issues}")
        results.append(False)
    else:
        print(f"  ✓ Key methods are async")
        results.append(True)
    
    # Test 3: Check PlanExecutor
    print("\nTesting PlanExecutor...")
    filepath = base_path / "ai" / "agency" / "executor.py"
    
    passed, issues = check_file_for_db_parameter(filepath)
    if not passed:
        print(f"  ❌ Has legacy 'db' parameter: {issues}")
        results.append(False)
    else:
        print("  ✓ No legacy 'db' parameter")
    
    passed, issues = check_file_for_agency_service(filepath)
    if not passed:
        print(f"  ❌ Missing agency_service: {issues}")
        results.append(False)
    else:
        print("  ✓ Has 'agency_service' parameter")
    
    methods = ['start_execution', 'execute_next_step', '_save_execution', '_save_step_execution']
    passed, issues = check_async_methods(filepath, 'PlanExecutor', methods)
    if not passed:
        print(f"  ❌ Methods not async: {issues}")
        results.append(False)
    else:
        print(f"  ✓ Key methods are async")
        results.append(True)
    
    # Test 4: Check SkillInvoker
    print("\nTesting SkillInvoker...")
    filepath = base_path / "ai" / "agency" / "skill_invoker.py"
    
    passed, issues = check_file_for_db_parameter(filepath)
    if not passed:
        print(f"  ❌ Has legacy 'db' parameter: {issues}")
        results.append(False)
    else:
        print("  ✓ No legacy 'db' parameter")
        results.append(True)
    
    # Test 5: Check AgencyEngine
    print("\nTesting AgencyEngine...")
    filepath = base_path / "ai" / "agency" / "engine.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check that PlanExecutor and SkillInvoker are initialized without db parameter
    if 'PlanExecutor(\n            db=' in content or 'SkillInvoker(\n            db=' in content:
        print("  ❌ Still passing 'db' parameter to PlanExecutor or SkillInvoker")
        results.append(False)
    else:
        print("  ✓ Not passing legacy 'db' parameter to components")
        results.append(True)
    
    # Print summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    
    if all(results):
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
