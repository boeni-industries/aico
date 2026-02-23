"""
Policy Manager - Phase 6.8

Database-driven policy management system replacing hardcoded DEFAULT_POLICIES.
Includes consent management, policy versioning, conflict resolution, and ethics caching.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import async_sessionmaker

from aico.data.uow import UnitOfWork



# ============================================================================
# Enums & Data Models
# ============================================================================

class ConsentType(str, Enum):
    """Types of user consent."""
    CURIOSITY_EXPLORATION = "curiosity_exploration"
    DATA_COLLECTION = "data_collection"
    PROACTIVE_CONTACT = "proactive_contact"
    GOAL_GENERATION = "goal_generation"
    WORLD_MODEL_UPDATE = "world_model_update"


class ConsentScope(str, Enum):
    """Scope of consent."""
    GLOBAL = "global"
    FEATURE = "feature"
    LIFE_AREA = "life_area"
    SPECIFIC_GOAL = "specific_goal"


class EthicsDecision(str, Enum):
    """Ethics gate decision."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


@dataclass
class PolicyRule:
    """Dynamic policy rule from database."""
    rule_id: str
    rule_name: str
    user_id: Optional[str]
    target_type: str
    conditions: Dict[str, Any]
    effect: str
    user_message_template: Optional[str]
    priority: int
    scope: str
    version: int
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class Consent:
    """User consent record."""
    consent_id: str
    user_id: str
    consent_type: ConsentType
    scope: ConsentScope
    scope_identifier: Optional[str]
    granted: bool
    expires_at: Optional[datetime]
    inherited_from: Optional[str]
    granted_at: datetime
    revoked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Dynamic Policy Manager
# ============================================================================

class PolicyManager:
    """
    Database-driven policy management system.
    
    Replaces hardcoded DEFAULT_POLICIES with dynamic database-driven rules.
    Supports user-specific policies, versioning, and conflict resolution.
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker,
        logger: Optional[Any] = None
    ):
        self.session_factory = session_factory
        self.logger = logger
        self._policy_cache: Dict[str, List[PolicyRule]] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
    
    async def load_policies(
        self,
        user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[PolicyRule]:
        """
        Load policies from database.
        
        Args:
            user_id: Optional user ID for user-specific policies
            target_type: Optional filter by target type
            force_refresh: Force cache refresh
            
        Returns:
            List of active policy rules
        """
        cache_key = f"{user_id}:{target_type}"
        
        # Check cache
        if not force_refresh and self._is_cache_valid():
            if cache_key in self._policy_cache:
                return self._policy_cache[cache_key]
        
        try:
            async with UnitOfWork(self.session_factory) as uow:
                policies = await uow.policy_rules.get_active_policies(
                    user_id=user_id,
                    target_type=target_type
                )
            
            # Update cache
            self._policy_cache[cache_key] = policies
            self._cache_time = datetime.now(UTC)
            
            if self.logger:
                self.logger.debug(
                    f"[POLICY] Loaded {len(policies)} policies "
                    f"(user={user_id}, target={target_type})"
                )
            
            return policies
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[POLICY] Failed to load policies: {e}")
            return []
    
    async def add_policy(
        self,
        rule_id: str,
        rule_name: str,
        target_type: str,
        conditions: Dict[str, Any],
        effect: str,
        user_id: Optional[str] = None,
        user_message_template: Optional[str] = None,
        priority: int = 50,
        scope: str = "global"
    ) -> str:
        """
        Add a new policy rule to database.
        
        Args:
            rule_id: Unique rule identifier
            rule_name: Human-readable name
            target_type: Type of target (goal, curiosity_signal, etc.)
            conditions: Conditions to match (dict)
            effect: Policy effect (allow, block, needs_consent, etc.)
            user_id: Optional user ID for user-specific policy
            user_message_template: Optional message template
            priority: Priority (higher = evaluated first)
            scope: Policy scope (global, user, deployment)
            
        Returns:
            rule_id
        """
        try:
            async with UnitOfWork(self.session_factory) as uow:
                await uow.policy_rules.create_policy(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    target_type=target_type,
                    conditions=conditions,
                    effect=effect,
                    user_id=user_id,
                    user_message_template=user_message_template,
                    priority=priority,
                    scope=scope
                )
                await uow.commit()
            
            # Invalidate cache
            self._policy_cache.clear()
            
            if self.logger:
                self.logger.info(f"[POLICY] Added policy rule: {rule_id}")
            
            return rule_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[POLICY] Failed to add policy: {e}")
            raise
    
    async def update_policy(
        self,
        rule_id: str,
        conditions: Optional[Dict[str, Any]] = None,
        effect: Optional[str] = None,
        priority: Optional[int] = None,
        active: Optional[bool] = None
    ) -> bool:
        """Update an existing policy rule."""
        try:
            async with UnitOfWork(self.session_factory) as uow:
                success = await uow.policy_rules.update_policy(
                    rule_id=rule_id,
                    conditions=conditions,
                    effect=effect,
                    priority=priority,
                    active=active
                )
                
                if not success:
                    raise ValueError(f"Policy rule {rule_id} not found")
                
                await uow.commit()
            
            # Invalidate cache
            self._policy_cache.clear()
            
            if self.logger:
                self.logger.info(f"[POLICY] Updated policy rule: {rule_id}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[POLICY] Failed to update policy: {e}")
            raise
    
    def resolve_conflicts(
        self,
        user_id: str,
        target_type: str,
        policies: List[PolicyRule]
    ) -> Tuple[PolicyRule, Optional[str]]:
        """
        Resolve conflicts between multiple matching policies.
        
        Args:
            user_id: User ID
            target_type: Target type
            policies: List of conflicting policies
            
        Returns:
            (selected_policy, conflict_id)
        """
        if len(policies) <= 1:
            return policies[0] if policies else None, None
        
        # Sort by priority (highest first)
        sorted_policies = sorted(policies, key=lambda p: p.priority, reverse=True)
        
        # Check for actual conflict (different effects at same priority)
        top_priority = sorted_policies[0].priority
        top_policies = [p for p in sorted_policies if p.priority == top_priority]
        
        if len(top_policies) > 1:
            effects = set(p.effect for p in top_policies)
            if len(effects) > 1:
                # Real conflict - log it
                conflict_id = self._log_conflict(
                    user_id,
                    top_policies[0].rule_id,
                    top_policies[1].rule_id,
                    target_type,
                    "priority_based"
                )
                
                # Use most restrictive
                restrictiveness = {"block": 3, "needs_consent": 2, "allow_with_warning": 1, "allow": 0}
                most_restrictive = max(top_policies, key=lambda p: restrictiveness.get(p.effect, 0))
                
                return most_restrictive, conflict_id
        
        return sorted_policies[0], None
    
    def _log_conflict(
        self,
        user_id: str,
        rule_id_a: str,
        rule_id_b: str,
        target_type: str,
        resolution: str
    ) -> str:
        """
        Log a policy conflict.
        
        Note: policy_conflicts table doesn't exist in production DB.
        This feature is not yet implemented. Logging to application logger only.
        """
        if self.logger:
            self.logger.warning(
                f"[POLICY] Conflict detected: user={user_id}, "
                f"rules={rule_id_a} vs {rule_id_b}, "
                f"target={target_type}, resolution={resolution}"
            )
        return None
    
    def _is_cache_valid(self) -> bool:
        """Check if policy cache is still valid."""
        if not self._cache_time:
            return False
        
        age = (datetime.now(UTC) - self._cache_time).total_seconds()
        return age < self._cache_ttl_seconds


# ============================================================================
# Consent Manager
# ============================================================================

class ConsentManager:
    """
    Granular consent tracking and management.
    
    Features:
    - Consent expiration and renewal
    - Consent inheritance and delegation
    - Comprehensive audit logging
    """
    
    def __init__(
        self,
        db: Any,  # Agency system being redesigned
        logger=None
    ):
        self.db = db
        self.logger = logger
    
    def grant_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        scope: ConsentScope,
        scope_identifier: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        inherited_from: Optional[str] = None
    ) -> str:
        """
        Grant user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            scope: Scope of consent
            scope_identifier: Optional scope identifier
            expires_in_days: Optional expiration in days
            inherited_from: Optional parent consent ID
            
        Returns:
            consent_id
        """
        consent_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = (now + timedelta(days=expires_in_days)).isoformat() if expires_in_days else None
        
        try:
            self.db.execute(
                """
                INSERT INTO consent_user_consents (
                    consent_id, user_id, consent_type, scope, scope_identifier,
                    granted, expires_at, inherited_from, granted_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (
                    consent_id,
                    user_id,
                    consent_type.value,
                    scope.value,
                    scope_identifier,
                    expires_at,
                    inherited_from,
                    now.isoformat(),
                    now.isoformat(),
                    now.isoformat()
                )
            )
            self.db.commit()
            
            # Log audit
            self._log_consent_audit(
                consent_id,
                user_id,
                "granted",
                f"Consent granted for {consent_type.value}"
            )
            
            if self.logger:
                self.logger.info(
                    f"[CONSENT] Granted {consent_type.value} consent for user {user_id}"
                )
            
            return consent_id
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[CONSENT] Failed to grant consent: {e}")
            raise
    
    def revoke_consent(
        self,
        consent_id: str,
        reason: Optional[str] = None
    ) -> None:
        """Revoke a consent."""
        try:
            row = self.db.fetch_one(
                "SELECT user_id FROM consent_user_consents WHERE consent_id = ?",
                (consent_id,)
            )
            
            if not row:
                return
            
            self.db.execute(
                """
                UPDATE consent_user_consents
                SET granted = 0, revoked_at = ?, updated_at = ?
                WHERE consent_id = ?
                """,
                (
                    datetime.now(UTC).isoformat(),
                    datetime.now(UTC).isoformat(),
                    consent_id
                )
            )
            self.db.commit()
            
            # Log audit
            self._log_consent_audit(
                consent_id,
                row["user_id"],
                "revoked",
                reason or "Consent revoked by user"
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[CONSENT] Failed to revoke consent: {e}")
            raise
    
    def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        scope: ConsentScope,
        scope_identifier: Optional[str] = None
    ) -> bool:
        """
        Check if user has granted consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            scope: Scope of consent
            scope_identifier: Optional scope identifier
            
        Returns:
            True if consent is granted and valid
        """
        try:
            now = datetime.now(UTC).isoformat()
            
            query = """
                SELECT consent_id FROM consent_user_consents
                WHERE user_id = ? AND consent_type = ? AND scope = ?
                  AND granted = 1 AND revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > ?)
            """
            params = [user_id, consent_type.value, scope.value, now]
            
            if scope_identifier:
                query += " AND scope_identifier = ?"
                params.append(scope_identifier)
            
            query += " LIMIT 1"
            
            row = self.db.fetch_one(query, tuple(params))
            
            return row is not None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[CONSENT] Failed to check consent: {e}")
            return False
    
    def expire_old_consents(self) -> int:
        """Expire consents that have passed their expiration date."""
        try:
            now = datetime.now(UTC).isoformat()
            
            # Get expired consents
            rows = self.db.fetch_all(
                """
                SELECT consent_id, user_id FROM consent_user_consents
                WHERE granted = 1 AND expires_at IS NOT NULL AND expires_at <= ?
                """,
                (now,)
            )
            
            for row in rows:
                self.db.execute(
                    """
                    UPDATE consent_user_consents
                    SET granted = 0, updated_at = ?
                    WHERE consent_id = ?
                    """,
                    (now, row["consent_id"])
                )
                
                # Log audit
                self._log_consent_audit(
                    row["consent_id"],
                    row["user_id"],
                    "expired",
                    "Consent expired automatically"
                )
            
            self.db.commit()
            
            return len(rows)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"[CONSENT] Failed to expire consents: {e}")
            return 0
    
    def _log_consent_audit(
        self,
        consent_id: str,
        user_id: str,
        action: str,
        reason: Optional[str] = None
    ) -> None:
        """Log consent action to audit trail."""
        try:
            audit_id = str(uuid.uuid4())
            
            self.db.execute(
                """
                INSERT INTO consent_audit_log (
                    audit_id, consent_id, user_id, action, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    consent_id,
                    user_id,
                    action,
                    reason,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[CONSENT] Failed to log audit: {e}")


# ============================================================================
# Enhanced Ethics Gate
# ============================================================================

class EnhancedEthicsGate:
    """
    Multi-level ethics checking with caching and explanation generation.
    """
    
    def __init__(
        self,
        db: Any,  # Agency system being redesigned
        policy_manager: PolicyManager,
        logger=None
    ):
        self.db = db
        self.policy_manager = policy_manager
        self.logger = logger
    
    async def check_ethics(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        check_level: int = 1,
        use_cache: bool = True
    ) -> Tuple[EthicsDecision, str, List[str]]:
        """
        Perform ethics check with caching.
        
        Args:
            user_id: User ID
            target_type: Type of target
            target_id: Target identifier
            check_level: 1=basic, 2=detailed, 3=comprehensive
            use_cache: Whether to use cached decisions
            
        Returns:
            (decision, reasoning, policy_rules_applied)
        """
        start_time = datetime.now(UTC)
        
        # Check cache
        if use_cache:
            cached = self._get_cached_decision(user_id, target_type, target_id)
            if cached:
                return cached
        
        # Perform ethics check
        decision, reasoning, rules_applied = await self._perform_check(
            user_id, target_type, target_id, check_level
        )
        
        # Cache decision
        if use_cache:
            self._cache_decision(
                user_id, target_type, target_id, decision, reasoning, rules_applied
            )
        
        # Log audit
        processing_time = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        self._log_audit(
            user_id, target_type, target_id, decision, reasoning,
            rules_applied, check_level, use_cache, processing_time
        )
        
        return decision, reasoning, rules_applied
    
    async def _perform_check(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        check_level: int
    ) -> Tuple[EthicsDecision, str, List[str]]:
        """Perform the actual ethics check."""
        # Load applicable policies
        policies = await self.policy_manager.load_policies(user_id, target_type)
        
        if not policies:
            return EthicsDecision.APPROVED, "No policies apply", []
        
        # Apply policies (simplified - would need full policy evaluation logic)
        blocking_policies = [p for p in policies if p.effect == "block"]
        
        if blocking_policies:
            return (
                EthicsDecision.BLOCKED,
                f"Blocked by policy: {blocking_policies[0].rule_name}",
                [p.rule_id for p in blocking_policies]
            )
        
        consent_policies = [p for p in policies if p.effect == "needs_consent"]
        if consent_policies:
            return (
                EthicsDecision.NEEDS_REVIEW,
                f"Requires consent: {consent_policies[0].rule_name}",
                [p.rule_id for p in consent_policies]
            )
        
        return EthicsDecision.APPROVED, "All policies satisfied", [p.rule_id for p in policies]
    
    def _get_cached_decision(
        self,
        user_id: str,
        target_type: str,
        target_id: str
    ) -> Optional[Tuple[EthicsDecision, str, List[str]]]:
        """Get cached ethics decision."""
        try:
            now = datetime.now(UTC).isoformat()
            
            row = self.db.fetch_one(
                """
                SELECT decision, reasoning, policy_rules_applied, cache_id
                FROM ethics_decisions_cache
                WHERE user_id = ? AND target_type = ? AND target_id = ?
                  AND (expires_at IS NULL OR expires_at > ?)
                LIMIT 1
                """,
                (user_id, target_type, target_id, now)
            )
            
            if row:
                # Update hit count
                self.db.execute(
                    """
                    UPDATE ethics_decisions_cache
                    SET hit_count = hit_count + 1, last_hit_at = ?
                    WHERE cache_id = ?
                    """,
                    (now, row["cache_id"])
                )
                self.db.commit()
                
                return (
                    EthicsDecision(row["decision"]),
                    row["reasoning"],
                    json.loads(row["policy_rules_applied"]) if row["policy_rules_applied"] else []
                )
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[ETHICS] Failed to get cached decision: {e}")
            return None
    
    def _cache_decision(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        decision: EthicsDecision,
        reasoning: str,
        rules_applied: List[str],
        ttl_hours: int = 24
    ) -> None:
        """Cache an ethics decision."""
        try:
            cache_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
            
            self.db.execute(
                """
                INSERT INTO ethics_decisions_cache (
                    cache_id, user_id, target_type, target_id, decision,
                    reasoning, policy_rules_applied, cached_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (cache_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    target_type = EXCLUDED.target_type,
                    target_id = EXCLUDED.target_id,
                    decision = EXCLUDED.decision,
                    reasoning = EXCLUDED.reasoning,
                    policy_rules_applied = EXCLUDED.policy_rules_applied,
                    cached_at = EXCLUDED.cached_at,
                    expires_at = EXCLUDED.expires_at
                """,
                (
                    cache_id,
                    user_id,
                    target_type,
                    target_id,
                    decision.value,
                    reasoning,
                    json.dumps(rules_applied),
                    now.isoformat(),
                    expires_at
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[ETHICS] Failed to cache decision: {e}")
    
    def _log_audit(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        decision: EthicsDecision,
        reasoning: str,
        rules_applied: List[str],
        check_level: int,
        cached: bool,
        processing_time_ms: int
    ) -> None:
        """Log ethics check to audit trail."""
        try:
            audit_id = str(uuid.uuid4())
            
            self.db.execute(
                """
                INSERT INTO ethics_gate_audit (
                    audit_id, user_id, target_type, target_id, decision,
                    reasoning, policy_rules_applied, check_level, cached,
                    processing_time_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    user_id,
                    target_type,
                    target_id,
                    decision.value,
                    reasoning,
                    json.dumps(rules_applied),
                    check_level,
                    1 if cached else 0,
                    processing_time_ms,
                    datetime.now(UTC).isoformat()
                )
            )
            self.db.commit()
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[ETHICS] Failed to log audit: {e}")
