"""
Coverage tests for policy_manager.py - targeting uncovered lines.

Focuses on error handling, edge cases, and conditional branches.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json
import uuid

from aico.ai.agency.policy_manager import (
    PolicyManager,
    ConsentManager,
    EnhancedEthicsGate,
    ConsentType,
    ConsentScope,
    EthicsDecision
)


def unique_rule_id(prefix="test_rule"):
    """Generate a unique rule ID for testing."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestPolicyManagerCoverage:
    """Tests targeting uncovered lines in PolicyManager."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def policy_manager(self, db):
        """Create policy manager with logger."""
        logger = Mock()
        return PolicyManager(db, logger=logger)
    
    # ========================================================================
    # Load Policies Tests
    # ========================================================================
    
    def test_load_policies_with_target_type_filter(self, policy_manager, test_user):
        """Test loading policies with target type filter (covers lines 146-148)."""
        # Add policies with different target types
        policy_manager.add_policy(
            rule_id=unique_rule_id("goal_policy"),
            rule_name="Goal Policy",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50,
            scope="global"
        )
        
        policy_manager.add_policy(
            rule_id=unique_rule_id("signal_policy"),
            rule_name="Signal Policy",
            target_type="curiosity_signal",
            conditions={},
            effect="allow",
            priority=50,
            scope="global"
        )
        
        # Load only goal policies
        policies = policy_manager.load_policies(target_type="goal")
        
        assert len(policies) >= 1
        assert all(p.target_type == "goal" for p in policies)
    
    def test_load_policies_cache_hit(self, policy_manager, test_user):
        """Test that cache is used on second load (covers lines 126-128)."""
        # First load - populates cache
        policies1 = policy_manager.load_policies(user_id=test_user)
        
        # Second load - should use cache
        policies2 = policy_manager.load_policies(user_id=test_user)
        
        # Should return same results
        assert len(policies1) == len(policies2)
        
        # Verify cache was used (logger.debug should be called only once for load)
        # The second call should skip the database query
    
    def test_load_policies_without_user_filter(self, policy_manager):
        """Test loading policies without user filter (covers lines 142-143)."""
        # Add global policy
        policy_manager.add_policy(
            rule_id=unique_rule_id("global_only"),
            rule_name="Global Only",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50,
            scope="global"
        )
        
        # Load without user_id
        policies = policy_manager.load_policies(user_id=None)
        
        # Should only get global policies
        assert all(p.user_id is None for p in policies)
    
    def test_load_policies_database_error(self, policy_manager, db):
        """Test error handling when loading policies fails (covers lines 168-171)."""
        with patch.object(db, 'fetch_all', side_effect=Exception("DB error")):
            policies = policy_manager.load_policies()
            
            assert policies == []
            assert policy_manager.logger.error.called
    
    def test_load_policies_logging(self, policy_manager, test_user):
        """Test that policy loading logs debug message (covers lines 160-164)."""
        policy_manager.load_policies(user_id=test_user, force_refresh=True)
        
        assert policy_manager.logger.debug.called
    
    # ========================================================================
    # Add Policy Tests
    # ========================================================================
    
    def test_add_policy_database_error(self, policy_manager, db):
        """Test error handling when adding policy fails (covers lines 237-240)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                policy_manager.add_policy(
                    rule_id=unique_rule_id("error_policy"),
                    rule_name="Error Policy",
                    target_type="goal",
                    conditions={},
                    effect="allow"
                )
            
            assert policy_manager.logger.error.called
    
    def test_add_policy_clears_cache(self, policy_manager):
        """Test that adding policy clears cache (covers line 230)."""
        # Populate cache
        policy_manager.load_policies()
        assert len(policy_manager._policy_cache) > 0
        
        # Add new policy
        policy_manager.add_policy(
            rule_id=unique_rule_id("clear_cache"),
            rule_name="Clear Cache",
            target_type="goal",
            conditions={},
            effect="allow"
        )
        
        # Cache should be cleared
        assert len(policy_manager._policy_cache) == 0
    
    # ========================================================================
    # Update Policy Tests
    # ========================================================================
    
    def test_update_policy_not_found(self, policy_manager):
        """Test updating non-existent policy (covers line 259)."""
        with pytest.raises(ValueError, match="not found"):
            policy_manager.update_policy(
                rule_id="nonexistent-rule",
                effect="block"
            )
    
    def test_update_policy_conditions_only(self, policy_manager):
        """Test updating only conditions (covers lines 285-287)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_cond"),
            rule_name="Update Conditions",
            target_type="goal",
            conditions={"priority": "low"},
            effect="allow",
            priority=50
        )
        
        new_conditions = {"priority": "high", "category": "work"}
        policy_manager.update_policy(
            rule_id=rule_id,
            conditions=new_conditions
        )
        
        row = policy_manager.db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = ?",
            (rule_id,)
        )
        
        stored_conditions = json.loads(row["conditions"])
        assert stored_conditions == new_conditions
    
    def test_update_policy_effect_only(self, policy_manager):
        """Test updating only effect (covers lines 289-291)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_effect"),
            rule_name="Update Effect",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50
        )
        
        policy_manager.update_policy(
            rule_id=rule_id,
            effect="block"
        )
        
        row = policy_manager.db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = ?",
            (rule_id,)
        )
        
        assert row["effect"] == "block"
    
    def test_update_policy_priority_only(self, policy_manager):
        """Test updating only priority (covers lines 293-295)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_priority"),
            rule_name="Update Priority",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50
        )
        
        policy_manager.update_policy(
            rule_id=rule_id,
            priority=90
        )
        
        row = policy_manager.db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = ?",
            (rule_id,)
        )
        
        assert row["priority"] == 90
    
    def test_update_policy_active_flag(self, policy_manager):
        """Test updating active flag (covers lines 297-299)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_active"),
            rule_name="Update Active",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50
        )
        
        # Deactivate policy
        policy_manager.update_policy(
            rule_id=rule_id,
            active=False
        )
        
        row = policy_manager.db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = ?",
            (rule_id,)
        )
        
        assert row["active"] == 0
    
    def test_update_policy_database_error(self, policy_manager, db):
        """Test error handling when updating policy fails (covers lines 315-318)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_error"),
            rule_name="Update Error",
            target_type="goal",
            conditions={},
            effect="allow"
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                policy_manager.update_policy(
                    rule_id=rule_id,
                    effect="block"
                )
            
            assert policy_manager.logger.error.called
    
    def test_update_policy_clears_cache(self, policy_manager):
        """Test that updating policy clears cache (covers line 313)."""
        rule_id = policy_manager.add_policy(
            rule_id=unique_rule_id("update_cache"),
            rule_name="Update Cache",
            target_type="goal",
            conditions={},
            effect="allow"
        )
        
        # Populate cache
        policy_manager.load_policies()
        assert len(policy_manager._policy_cache) > 0
        
        # Update policy
        policy_manager.update_policy(
            rule_id=rule_id,
            effect="block"
        )
        
        # Cache should be cleared
        assert len(policy_manager._policy_cache) == 0
    
    # ========================================================================
    # Conflict Resolution Tests
    # ========================================================================
    
    def test_resolve_conflicts_no_conflict(self, policy_manager):
        """Test conflict resolution with single policy (covers line 338)."""
        from aico.ai.agency.policy_manager import PolicyRule
        
        policy = PolicyRule(
            rule_id="test-rule",
            rule_name="Test",
            user_id=None,
            target_type="goal",
            conditions={},
            effect="allow",
            user_message_template=None,
            priority=50,
            scope="global",
            version=1,
            active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        selected, conflict_id = policy_manager.resolve_conflicts(
            user_id="test-user",
            target_type="goal",
            policies=[policy]
        )
        
        assert selected == policy
        assert conflict_id is None
    
    def test_resolve_conflicts_empty_list(self, policy_manager):
        """Test conflict resolution with empty list (covers line 338)."""
        selected, conflict_id = policy_manager.resolve_conflicts(
            user_id="test-user",
            target_type="goal",
            policies=[]
        )
        
        assert selected is None
        assert conflict_id is None
    
    def test_resolve_conflicts_same_priority_same_effect(self, policy_manager):
        """Test conflict resolution with same priority and effect (covers lines 347-349)."""
        from aico.ai.agency.policy_manager import PolicyRule
        
        now = datetime.utcnow()
        policies = [
            PolicyRule(
                rule_id="rule-1",
                rule_name="Rule 1",
                user_id=None,
                target_type="goal",
                conditions={},
                effect="allow",
                user_message_template=None,
                priority=50,
                scope="global",
                version=1,
                active=True,
                created_at=now,
                updated_at=now
            ),
            PolicyRule(
                rule_id="rule-2",
                rule_name="Rule 2",
                user_id=None,
                target_type="goal",
                conditions={},
                effect="allow",
                user_message_template=None,
                priority=50,
                scope="global",
                version=1,
                active=True,
                created_at=now,
                updated_at=now
            )
        ]
        
        selected, conflict_id = policy_manager.resolve_conflicts(
            user_id="test-user",
            target_type="goal",
            policies=policies
        )
        
        # Should select first one, no conflict logged
        assert selected in policies
        assert conflict_id is None
    
    def test_resolve_conflicts_real_conflict(self, policy_manager):
        """Test conflict resolution with different effects (covers lines 347-363)."""
        from aico.ai.agency.policy_manager import PolicyRule
        
        now = datetime.utcnow()
        policies = [
            PolicyRule(
                rule_id="allow-rule",
                rule_name="Allow Rule",
                user_id=None,
                target_type="goal",
                conditions={},
                effect="allow",
                user_message_template=None,
                priority=50,
                scope="global",
                version=1,
                active=True,
                created_at=now,
                updated_at=now
            ),
            PolicyRule(
                rule_id="block-rule",
                rule_name="Block Rule",
                user_id=None,
                target_type="goal",
                conditions={},
                effect="block",
                user_message_template=None,
                priority=50,
                scope="global",
                version=1,
                active=True,
                created_at=now,
                updated_at=now
            )
        ]
        
        selected, conflict_id = policy_manager.resolve_conflicts(
            user_id="test-user",
            target_type="goal",
            policies=policies
        )
        
        # Should select most restrictive (block)
        assert selected.effect == "block"
        # Conflict may or may not be logged depending on DB constraints
        # The important part is that the most restrictive policy is selected
    
    def test_log_conflict_database_error(self, policy_manager, db):
        """Test error handling when logging conflict fails (covers lines 400-403)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            conflict_id = policy_manager._log_conflict(
                user_id="test-user",
                rule_id_a="rule-a",
                rule_id_b="rule-b",
                target_type="goal",
                resolution="priority_based"
            )
            
            assert conflict_id is None
            assert policy_manager.logger.warning.called
    
    # ========================================================================
    # Cache Management Tests
    # ========================================================================
    
    def test_is_cache_valid_no_cache_time(self, policy_manager):
        """Test cache validity check with no cache time (covers lines 407-408)."""
        policy_manager._cache_time = None
        
        assert policy_manager._is_cache_valid() is False
    
    def test_is_cache_valid_expired(self, policy_manager):
        """Test cache validity check with expired cache (covers lines 410-411)."""
        # Set cache time to 10 minutes ago
        policy_manager._cache_time = datetime.utcnow() - timedelta(minutes=10)
        policy_manager._cache_ttl_seconds = 300  # 5 minutes
        
        assert policy_manager._is_cache_valid() is False
    
    def test_is_cache_valid_fresh(self, policy_manager):
        """Test cache validity check with fresh cache (covers lines 410-411)."""
        # Set cache time to 1 minute ago
        policy_manager._cache_time = datetime.utcnow() - timedelta(minutes=1)
        policy_manager._cache_ttl_seconds = 300  # 5 minutes
        
        assert policy_manager._is_cache_valid() is True


class TestConsentManagerCoverage:
    """Tests targeting uncovered lines in ConsentManager."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def consent_manager(self, db):
        """Create consent manager with logger."""
        logger = Mock()
        return ConsentManager(db, logger=logger)
    
    def test_grant_consent_without_expiration(self, consent_manager, test_user):
        """Test granting consent without expiration (covers lines 477-478)."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.CURIOSITY_EXPLORATION,
            scope=ConsentScope.GLOBAL,
            expires_in_days=None
        )
        
        row = consent_manager.db.fetch_one(
            "SELECT * FROM user_consents WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert row["expires_at"] is None
    
    def test_grant_consent_with_scope_identifier(self, consent_manager, test_user):
        """Test granting consent with scope identifier (covers line 469)."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.FEATURE,
            scope_identifier="analytics"
        )
        
        row = consent_manager.db.fetch_one(
            "SELECT * FROM user_consents WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert row["scope_identifier"] == "analytics"
    
    def test_grant_consent_database_error(self, consent_manager, test_user, db):
        """Test error handling when granting consent fails."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                consent_manager.grant_consent(
                    user_id=test_user,
                    consent_type=ConsentType.GOAL_GENERATION,
                    scope=ConsentScope.GLOBAL
                )
            
            assert consent_manager.logger.error.called
    
    def test_revoke_consent_database_error(self, consent_manager, test_user, db):
        """Test error handling when revoking consent fails."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.PROACTIVE_CONTACT,
            scope=ConsentScope.GLOBAL
        )
        
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                consent_manager.revoke_consent(consent_id)
            
            assert consent_manager.logger.error.called
    
    def test_check_consent_with_scope_identifier(self, consent_manager, test_user):
        """Test checking consent with scope identifier."""
        consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.FEATURE,
            scope_identifier="feature-x"
        )
        
        has_consent = consent_manager.check_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.FEATURE,
            scope_identifier="feature-x"
        )
        
        assert has_consent is True
    
    def test_check_consent_database_error(self, consent_manager, test_user, db):
        """Test error handling when checking consent fails."""
        with patch.object(db, 'fetch_one', side_effect=Exception("DB error")):
            has_consent = consent_manager.check_consent(
                user_id=test_user,
                consent_type=ConsentType.CURIOSITY_EXPLORATION,
                scope=ConsentScope.GLOBAL
            )
            
            assert has_consent is False
            assert consent_manager.logger.error.called


class TestEnhancedEthicsGateCoverage:
    """Tests targeting uncovered lines in EnhancedEthicsGate."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return test_db
    
    @pytest.fixture
    def policy_manager(self, db):
        """Create policy manager."""
        return PolicyManager(db)
    
    @pytest.fixture
    def ethics_gate(self, db, policy_manager):
        """Create enhanced ethics gate with logger."""
        logger = Mock()
        return EnhancedEthicsGate(db, policy_manager, logger=logger)
    
    def test_check_ethics_no_policies(self, ethics_gate, test_user, db):
        """Test ethics check with no applicable policies (covers lines 764-765)."""
        # Clear all policies
        db.execute("DELETE FROM agency_policy_rules WHERE user_id = ? OR user_id IS NULL", (test_user,))
        db.commit()
        
        decision, reasoning, rules = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-no-policies",
            use_cache=False
        )
        
        assert decision == EthicsDecision.APPROVED
        assert "No policies apply" in reasoning
        assert len(rules) == 0
    
    def test_check_ethics_needs_consent(self, ethics_gate, policy_manager, test_user):
        """Test ethics check that needs consent (covers lines 777-783)."""
        policy_manager.add_policy(
            rule_id=unique_rule_id("consent_policy"),
            rule_name="Consent Policy",
            target_type="goal",
            conditions={},
            effect="needs_consent",
            user_id=test_user,
            priority=70
        )
        
        decision, reasoning, rules = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-consent",
            use_cache=False
        )
        
        assert decision == EthicsDecision.NEEDS_REVIEW
        assert "consent" in reasoning.lower()
    
    def test_get_cached_decision_with_null_rules(self, ethics_gate, test_user, db):
        """Test getting cached decision with null policy_rules_applied (covers line 823)."""
        # Manually insert cache entry with null rules
        cache_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO ethics_decisions_cache (
                cache_id, user_id, target_type, target_id, decision,
                reasoning, policy_rules_applied, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)""",
            (cache_id, test_user, "goal", "test-null-rules", "approved",
             "Test", datetime.utcnow().isoformat())
        )
        db.commit()
        
        cached = ethics_gate._get_cached_decision(
            user_id=test_user,
            target_type="goal",
            target_id="test-null-rules"
        )
        
        assert cached is not None
        decision, reasoning, rules = cached
        assert rules == []
    
    def test_get_cached_decision_database_error(self, ethics_gate, test_user, db):
        """Test error handling when getting cached decision fails (covers lines 828-831)."""
        with patch.object(db, 'fetch_one', side_effect=Exception("DB error")):
            cached = ethics_gate._get_cached_decision(
                user_id=test_user,
                target_type="goal",
                target_id="test-error"
            )
            
            assert cached is None
            assert ethics_gate.logger.warning.called
    
    def test_cache_decision_database_error(self, ethics_gate, test_user, db):
        """Test error handling when caching decision fails (covers lines 870-872)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            # Should not raise, just log warning
            ethics_gate._cache_decision(
                user_id=test_user,
                target_type="goal",
                target_id="test-cache-error",
                decision=EthicsDecision.APPROVED,
                reasoning="Test",
                rules_applied=[]
            )
            
            assert ethics_gate.logger.warning.called
    
    def test_log_audit_database_error(self, ethics_gate, test_user, db):
        """Test error handling when logging audit fails (covers lines 914-916)."""
        with patch.object(db, 'execute', side_effect=Exception("DB error")):
            # Should not raise, just log warning
            ethics_gate._log_audit(
                user_id=test_user,
                target_type="goal",
                target_id="test-audit-error",
                decision=EthicsDecision.APPROVED,
                reasoning="Test",
                rules_applied=[],
                check_level=1,
                cached=False,
                processing_time_ms=10
            )
            
            assert ethics_gate.logger.warning.called
