"""
Tests for Default Policies

Tests the default policy rules and installation process.
"""

import pytest

from aico.ai.agency.default_policies import DEFAULT_POLICIES, install_default_policies
from aico.ai.agency.values_ethics import PolicyRule


def test_default_policies_exist():
    """Test that DEFAULT_POLICIES is defined and not empty."""
    assert DEFAULT_POLICIES is not None
    assert isinstance(DEFAULT_POLICIES, list)
    assert len(DEFAULT_POLICIES) > 0


def test_default_policies_structure():
    """Test that each policy has required fields."""
    for policy in DEFAULT_POLICIES:
        assert isinstance(policy, PolicyRule)
        assert policy.rule_id is not None
        assert policy.target_type is not None
        assert policy.effect is not None
        assert policy.priority is not None


def test_default_policies_have_goal_rules():
    """Test that there are goal-related policies."""
    from aico.ai.agency.values_ethics import PolicyTargetType
    goal_policies = [p for p in DEFAULT_POLICIES if p.target_type == PolicyTargetType.GOAL]
    assert len(goal_policies) > 0


def test_default_policies_have_curiosity_rules():
    """Test that there are curiosity-related policies."""
    from aico.ai.agency.values_ethics import PolicyTargetType
    curiosity_policies = [p for p in DEFAULT_POLICIES if p.target_type == PolicyTargetType.CURIOSITY_SIGNAL]
    assert len(curiosity_policies) > 0


def test_policy_priorities_are_valid():
    """Test that all policy priorities are in valid range."""
    for policy in DEFAULT_POLICIES:
        assert 0 <= policy.priority <= 100


def test_policy_effects_are_valid():
    """Test that all policy effects are valid PolicyEffect enum values."""
    from aico.ai.agency.values_ethics import PolicyEffect
    
    for policy in DEFAULT_POLICIES:
        assert isinstance(policy.effect, PolicyEffect)


def test_policies_have_descriptions():
    """Test that policies have user-facing messages."""
    for policy in DEFAULT_POLICIES:
        assert policy.user_message_template is not None
        assert len(policy.user_message_template) > 0


def test_policy_rule_ids_are_unique():
    """Test that all policy rule IDs are unique."""
    rule_ids = [p.rule_id for p in DEFAULT_POLICIES]
    assert len(rule_ids) == len(set(rule_ids)), "Duplicate rule IDs found"


def test_policies_have_valid_scopes():
    """Test that all policies have valid scopes."""
    from aico.ai.agency.values_ethics import PolicyScope
    
    for policy in DEFAULT_POLICIES:
        assert isinstance(policy.scope, PolicyScope)
