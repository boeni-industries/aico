"""
Tests for default policy installation.
"""

import pytest
from unittest.mock import Mock

from aico.ai.agency.default_policies import install_default_policies, DEFAULT_POLICIES
from aico.ai.agency.values_ethics import PolicyEffect, PolicyTargetType


class TestDefaultPoliciesInstall:
    """Test default policy installation."""
    
    def test_default_policies_defined(self):
        """Test that default policies are defined."""
        assert len(DEFAULT_POLICIES) > 0
        assert all(hasattr(p, 'rule_id') for p in DEFAULT_POLICIES)
    
    def test_default_policies_structure(self):
        """Test default policies have required fields."""
        for policy in DEFAULT_POLICIES:
            assert policy.rule_id is not None
            assert policy.rule_name is not None
            assert policy.target_type in [PolicyTargetType.GOAL, PolicyTargetType.CURIOSITY_SIGNAL, PolicyTargetType.PLAN]
            assert policy.effect in [PolicyEffect.ALLOW, PolicyEffect.ALLOW_WITH_WARNING, PolicyEffect.NEEDS_CONSENT, PolicyEffect.BLOCK]
            assert policy.priority > 0
    
    def test_install_default_policies_new(self):
        """Test installing policies when none exist."""
        # Mock service
        mock_service = Mock()
        mock_service.get_policy_rule = Mock(return_value=None)  # No existing policies
        mock_service.add_policy_rule = Mock()
        
        # Install
        count = install_default_policies(mock_service)
        
        # Should install all policies
        assert count == len(DEFAULT_POLICIES)
        assert mock_service.add_policy_rule.call_count == len(DEFAULT_POLICIES)
    
    def test_install_default_policies_existing(self):
        """Test installing policies when some already exist."""
        # Mock service - first policy exists, others don't
        def mock_get_policy(rule_id):
            if rule_id == DEFAULT_POLICIES[0].rule_id:
                return DEFAULT_POLICIES[0]
            return None
        
        mock_service = Mock()
        mock_service.get_policy_rule = Mock(side_effect=mock_get_policy)
        mock_service.add_policy_rule = Mock()
        
        # Install
        count = install_default_policies(mock_service)
        
        # Should install all except the first one
        assert count == len(DEFAULT_POLICIES) - 1
        assert mock_service.add_policy_rule.call_count == len(DEFAULT_POLICIES) - 1
    
    def test_install_default_policies_all_existing(self):
        """Test installing policies when all already exist."""
        # Mock service - all policies exist
        mock_service = Mock()
        mock_service.get_policy_rule = Mock(return_value=Mock())  # All exist
        mock_service.add_policy_rule = Mock()
        
        # Install
        count = install_default_policies(mock_service)
        
        # Should install none
        assert count == 0
        assert mock_service.add_policy_rule.call_count == 0
    
    def test_default_policy_rule_ids_unique(self):
        """Test that all default policy rule IDs are unique."""
        rule_ids = [p.rule_id for p in DEFAULT_POLICIES]
        assert len(rule_ids) == len(set(rule_ids))
    
    def test_default_policies_cover_all_target_types(self):
        """Test that default policies cover all major target types."""
        target_types = {p.target_type for p in DEFAULT_POLICIES}
        
        # Should have policies for goals, curiosity signals, and plans
        assert PolicyTargetType.GOAL in target_types
        assert PolicyTargetType.CURIOSITY_SIGNAL in target_types
        assert PolicyTargetType.PLAN in target_types
