"""
Comprehensive Tests for Phase 6.8: Policy & Ethics Depth

Tests dynamic policy loading, consent management, policy versioning,
conflict resolution, and enhanced ethics gates with caching.
"""

import pytest
from datetime import datetime, timedelta, UTC
import uuid

from aico.ai.agency.policy_manager import (
    PolicyManager,
    ConsentManager,
    EnhancedEthicsGate,
    ConsentType,
    ConsentScope,
    EthicsDecision
)


class _DB:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(q, params or ())
        return cur

    def fetch_one(self, query, params=None):
        cur = self.execute(query, params)
        row = cur.fetchone()
        cur.close()
        return row

    def fetch_all(self, query, params=None):
        cur = self.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


# ============================================================================
# HELPERS
# ============================================================================

def unique_rule_id(prefix="test_rule"):
    """Generate a unique rule ID for testing."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ============================================================================
# POLICY MANAGER TESTS
# ============================================================================

class TestPolicyManager:
    """Test dynamic policy loading and management."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def policy_manager(self, session_factory):
        """Create policy manager."""
        return PolicyManager(session_factory)
    
    @pytest.mark.asyncio
    async def test_add_global_policy(self, policy_manager, test_db):
        """Test adding a global policy rule."""
        rule_id = await policy_manager.add_policy(
            rule_id=unique_rule_id("global_policy"),
            rule_name="Test Global Policy",
            target_type="goal",
            conditions={"priority": "high"},
            effect="allow_with_warning",
            user_message_template="High priority goal detected",
            priority=60,
            scope="global"
        )
        
        assert rule_id is not None
        
        # Verify in database using raw connection
        db = _DB(test_db)
        row = db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = %s",
            (rule_id,)
        )
        
        assert row is not None
        assert row["rule_id"] == rule_id
        assert row["active"] == True
    
    @pytest.mark.asyncio
    async def test_add_user_specific_policy(self, policy_manager, test_user, test_db):
        """Test adding a user-specific policy."""
        rule_id = await policy_manager.add_policy(
            rule_id=unique_rule_id("user_policy"),
            rule_name="User Specific Policy",
            target_type="curiosity_signal",
            conditions={"intensity": 0.9},
            effect="needs_consent",
            user_id=test_user,
            priority=80,
            scope="user"
        )
        
        db = _DB(test_db)
        row = db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = %s",
            (rule_id,)
        )
        
        assert row is not None
    
    @pytest.mark.asyncio
    async def test_load_global_policies(self, policy_manager):
        """Test loading global policies."""
        # Add test policies
        await policy_manager.add_policy(
            rule_id=unique_rule_id("load"),
            rule_name="Load Test 1",
            target_type="goal",
            conditions={},
            effect="allow",
            priority=50,
            scope="global"
        )
        
        policies = await policy_manager.load_policies()
        
        assert len(policies) >= 1
        assert all(p.user_id is None for p in policies)
    
    @pytest.mark.asyncio
    async def test_load_user_policies(self, policy_manager, test_user):
        """Test loading user-specific policies."""
        # Add global policy
        await policy_manager.add_policy(
            rule_id=unique_rule_id("load_global"),
            rule_name="Global",
            target_type="goal",
            conditions={},
            effect="allow",
            scope="global"
        )
        
        # Add user policy
        await policy_manager.add_policy(
            rule_id=unique_rule_id("load_user"),
            rule_name="User",
            target_type="goal",
            conditions={},
            effect="block",
            user_id=test_user,
            scope="user"
        )
        
        policies = await policy_manager.load_policies(user_id=test_user)
        
        # Should include both global and user policies
        assert len(policies) >= 2
        scopes = [p.scope for p in policies]
        assert "global" in scopes
        assert "user" in scopes
    
    @pytest.mark.asyncio
    async def test_update_policy(self, policy_manager, test_db):
        """Test updating a policy rule."""
        rule_id = await policy_manager.add_policy(
            rule_id=unique_rule_id("update"),
            rule_name="Update Test",
            target_type="goal",
            conditions={"priority": "low"},
            effect="allow",
            priority=30,
            scope="global"
        )
        
        # Update policy
        await policy_manager.update_policy(
            rule_id=rule_id,
            conditions={"priority": "high"},
            effect="block",
            priority=90
        )
        
        # Verify update by querying database directly
        db = _DB(test_db)
        updated_rule = db.fetch_one(
            "SELECT * FROM agency_policy_rules WHERE rule_id = %s",
            (rule_id,)
        )
        assert updated_rule is not None
        import json
        # conditions is stored as JSON string in Text column
        conditions = json.loads(updated_rule["conditions"]) if isinstance(updated_rule["conditions"], str) else updated_rule["conditions"]
        assert conditions["priority"] == "high"
        assert updated_rule["effect"] == "block"
        assert updated_rule["priority"] == 90
    
    @pytest.mark.asyncio
    async def test_policy_caching(self, policy_manager, test_user):
        """Test that policies are cached."""
        # First load
        policies1 = await policy_manager.load_policies(user_id=test_user)
        
        # Second load (should use cache)
        policies2 = await policy_manager.load_policies(user_id=test_user)
        
        assert len(policies1) == len(policies2)
        
        # Force refresh
        policies3 = await policy_manager.load_policies(user_id=test_user, force_refresh=True)
        
        assert len(policies3) == len(policies1)


# ============================================================================
# CONSENT MANAGER TESTS
# ============================================================================

class TestConsentManager:
    """Test consent tracking and management."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def consent_manager(self, db):
        """Create consent manager."""
        return ConsentManager(db)
    
    def test_grant_consent(self, consent_manager, test_user):
        """Test granting user consent."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.CURIOSITY_EXPLORATION,
            scope=ConsentScope.GLOBAL
        )
        
        assert consent_id is not None
        
        # Verify in database
        row = consent_manager.db.fetch_one(
            "SELECT * FROM consent_user_consents WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert row is not None
        assert row["user_id"] == test_user
        assert row["consent_type"] == "curiosity_exploration"
        assert row["granted"] == 1
    
    def test_grant_consent_with_expiration(self, consent_manager, test_user):
        """Test granting consent with expiration."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.FEATURE,
            scope_identifier="analytics",
            expires_in_days=30
        )
        
        row = consent_manager.db.fetch_one(
            "SELECT * FROM consent_user_consents WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert row["expires_at"] is not None
    
    def test_revoke_consent(self, consent_manager, test_user):
        """Test revoking consent."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.PROACTIVE_CONTACT,
            scope=ConsentScope.GLOBAL
        )
        
        consent_manager.revoke_consent(consent_id, reason="User requested")
        
        row = consent_manager.db.fetch_one(
            "SELECT * FROM consent_user_consents WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert row["granted"] == 0
        assert row["revoked_at"] is not None
    
    def test_check_consent_granted(self, consent_manager, test_user):
        """Test checking granted consent."""
        consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.GOAL_GENERATION,
            scope=ConsentScope.GLOBAL
        )
        
        has_consent = consent_manager.check_consent(
            user_id=test_user,
            consent_type=ConsentType.GOAL_GENERATION,
            scope=ConsentScope.GLOBAL
        )
        
        assert has_consent is True
    
    def test_check_consent_not_granted(self, consent_manager, test_user):
        """Test checking non-existent consent."""
        has_consent = consent_manager.check_consent(
            user_id=test_user,
            consent_type=ConsentType.WORLD_MODEL_UPDATE,
            scope=ConsentScope.GLOBAL
        )
        
        assert has_consent is False
    
    def test_check_consent_revoked(self, consent_manager, test_user):
        """Test that revoked consent returns False."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.GLOBAL
        )
        
        consent_manager.revoke_consent(consent_id)
        
        has_consent = consent_manager.check_consent(
            user_id=test_user,
            consent_type=ConsentType.DATA_COLLECTION,
            scope=ConsentScope.GLOBAL
        )
        
        assert has_consent is False
    
    def test_consent_audit_logging(self, consent_manager, test_user, db):
        """Test that consent actions are audited."""
        consent_id = consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.CURIOSITY_EXPLORATION,
            scope=ConsentScope.GLOBAL
        )
        
        consent_manager.revoke_consent(consent_id, reason="Test revocation")
        
        # Check audit log
        audit_rows = db.fetch_all(
            "SELECT * FROM consent_audit_log WHERE consent_id = ?",
            (consent_id,)
        )
        
        assert len(audit_rows) >= 2  # granted + revoked
        actions = [row["action"] for row in audit_rows]
        assert "granted" in actions
        assert "revoked" in actions


# ============================================================================
# ENHANCED ETHICS GATE TESTS
# ============================================================================

class TestEnhancedEthicsGate:
    """Test enhanced ethics gate with caching."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def policy_manager(self, db):
        """Create policy manager."""
        return PolicyManager(db)
    
    @pytest.fixture
    def ethics_gate(self, db, policy_manager):
        """Create enhanced ethics gate."""
        return EnhancedEthicsGate(db, policy_manager)
    
    def test_ethics_check_approved(self, ethics_gate, policy_manager, test_user, db):
        """Test ethics check that approves."""
        # Clean up any existing policies for this user and target type
        db.execute("DELETE FROM agency_policy_rules WHERE user_id = ? OR target_type = 'goal'", (test_user,))
        db.execute("DELETE FROM ethics_decisions_cache WHERE user_id = ?", (test_user,))
        db.commit()
        policy_manager._policy_cache.clear()
        
        # Add allowing policy
        policy_manager.add_policy(
            rule_id=unique_rule_id("allow_policy"),
            rule_name="Allow Policy",
            target_type="goal",
            conditions={},
            effect="allow",
            user_id=test_user,
            priority=50,
            scope="user"
        )
        
        decision, reasoning, rules = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-1",
            use_cache=False
        )
        
        assert decision == EthicsDecision.APPROVED
        assert len(rules) >= 1
    
    def test_ethics_check_blocked(self, ethics_gate, policy_manager, test_user):
        """Test ethics check that blocks."""
        # Add blocking policy
        policy_manager.add_policy(
            rule_id=unique_rule_id("block_policy"),
            rule_name="Block Policy",
            target_type="goal",
            conditions={},
            effect="block",
            user_id=test_user,
            priority=90,
            scope="user"
        )
        
        decision, reasoning, rules = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-2",
            use_cache=False
        )
        
        assert decision == EthicsDecision.BLOCKED
        assert "block" in reasoning.lower()
    
    def test_ethics_check_caching(self, ethics_gate, policy_manager, test_user):
        """Test that ethics decisions are cached."""
        # Add policy
        policy_manager.add_policy(
            rule_id=unique_rule_id("cache_policy"),
            rule_name="Cache Policy",
            target_type="goal",
            conditions={},
            effect="allow",
            user_id=test_user,
            priority=50,
            scope="user"
        )
        
        # First check (not cached)
        decision1, _, _ = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-cache",
            use_cache=True
        )
        
        # Second check (should use cache)
        decision2, _, _ = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-cache",
            use_cache=True
        )
        
        assert decision1 == decision2
        
        # Verify cache hit count
        cache_row = ethics_gate.db.fetch_one(
            """SELECT hit_count FROM ethics_decisions_cache
               WHERE user_id = ? AND target_id = ?""",
            (test_user, "test-goal-cache")
        )
        
        assert cache_row is not None
        assert cache_row["hit_count"] >= 1
    
    def test_ethics_audit_logging(self, ethics_gate, policy_manager, test_user, db):
        """Test that ethics checks are audited."""
        policy_manager.add_policy(
            rule_id=unique_rule_id("audit_policy"),
            rule_name="Audit Policy",
            target_type="goal",
            conditions={},
            effect="allow",
            user_id=test_user,
            priority=50,
            scope="user"
        )
        
        ethics_gate.check_ethics(
            user_id=test_user,
            target_type="goal",
            target_id="test-goal-audit",
            check_level=2,
            use_cache=False
        )
        
        # Check audit log
        audit_rows = db.fetch_all(
            "SELECT * FROM ethics_gate_audit WHERE user_id = ? AND target_id = ?",
            (test_user, "test-goal-audit")
        )
        
        assert len(audit_rows) >= 1
        assert audit_rows[0]["check_level"] == 2
        assert audit_rows[0]["processing_time_ms"] is not None

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPolicyEthicsIntegration:
    """Test integration between policy, consent, and ethics systems."""
    
    @pytest.fixture
    def db(self, test_db):
        """Use test database fixture."""
        return _DB(test_db)
    
    @pytest.fixture
    def policy_manager(self, db):
        """Create policy manager."""
        return PolicyManager(db)
    
    @pytest.fixture
    def consent_manager(self, db):
        """Create consent manager."""
        return ConsentManager(db)
    
    @pytest.fixture
    def ethics_gate(self, db, policy_manager):
        """Create enhanced ethics gate."""
        return EnhancedEthicsGate(db, policy_manager)
    
    def test_policy_consent_integration(
        self,
        policy_manager,
        consent_manager,
        ethics_gate,
        test_user
    ):
        """Test that policies requiring consent work with consent manager."""
        # Add policy requiring consent
        policy_manager.add_policy(
            rule_id=unique_rule_id("consent_policy"),
            rule_name="Consent Required Policy",
            target_type="curiosity_signal",
            conditions={},
            effect="needs_consent",
            user_id=test_user,
            priority=80,
            scope="user"
        )
        
        # Check ethics (should need review)
        decision, _, _ = ethics_gate.check_ethics(
            user_id=test_user,
            target_type="curiosity_signal",
            target_id="test-signal-1",
            use_cache=False
        )
        
        assert decision == EthicsDecision.NEEDS_REVIEW
        
        # Grant consent
        consent_manager.grant_consent(
            user_id=test_user,
            consent_type=ConsentType.CURIOSITY_EXPLORATION,
            scope=ConsentScope.GLOBAL
        )
        
        # Verify consent was granted
        has_consent = consent_manager.check_consent(
            user_id=test_user,
            consent_type=ConsentType.CURIOSITY_EXPLORATION,
            scope=ConsentScope.GLOBAL
        )
        
        assert has_consent is True
