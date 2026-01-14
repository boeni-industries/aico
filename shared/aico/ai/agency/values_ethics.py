"""
Values & Ethics Layer for AICO Agency

Provides explicit value constraints and ethical reasoning for agency autonomy.
Evaluates goals, plans, curiosity signals, and world model updates against
configurable policies and user preferences.
"""

from __future__ import annotations

import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, UTC

from pydantic import BaseModel, Field



# ============================================================================
# Enums
# ============================================================================

class PolicyEffect(str, Enum):
    """Policy decision effects."""
    ALLOW = "allow"
    ALLOW_WITH_WARNING = "allow_with_warning"
    NEEDS_CONSENT = "needs_consent"
    BLOCK = "block"


class PolicyScope(str, Enum):
    """Policy rule scope."""
    GLOBAL = "global"
    DEPLOYMENT = "deployment"
    USER = "user"


class PolicyTargetType(str, Enum):
    """Types of entities that can be evaluated."""
    GOAL = "goal"
    PLAN = "plan"
    SKILL = "skill"
    CURIOSITY_SIGNAL = "curiosity_signal"
    WORLD_MODEL_UPDATE = "world_model_update"


class ConsentDecision(str, Enum):
    """User consent decision."""
    GRANTED = "granted"
    DENIED = "denied"


class ProactiveBehaviorLevel(str, Enum):
    """User preference for proactive behavior."""
    QUIET = "quiet"
    BALANCED = "balanced"
    PROACTIVE = "proactive"


# ============================================================================
# Data Models
# ============================================================================

class ValueProfile(BaseModel):
    """Per-user value preferences and boundaries."""
    
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    sensitive_life_areas: List[str] = Field(default_factory=list)
    allowed_curiosity_domains: List[str] = Field(default_factory=list)
    curiosity_intensity: float = 0.5  # 0.0-1.0
    proactive_behavior_level: ProactiveBehaviorLevel = ProactiveBehaviorLevel.BALANCED
    storage_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyRule(BaseModel):
    """Structured ethics/safety rule."""
    
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_name: str
    target_type: PolicyTargetType
    conditions: Dict[str, Any]  # Predicates over ontology
    effect: PolicyEffect
    user_message_template: Optional[str] = None
    priority: int = 100  # Lower = higher priority
    enabled: bool = True
    scope: PolicyScope = PolicyScope.GLOBAL
    scope_id: Optional[str] = None  # user_id for user-specific rules
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Consent(BaseModel):
    """Explicit user consent record."""
    
    consent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    consent_scope: Dict[str, Any]  # What was consented to
    decision: ConsentDecision
    context: Dict[str, Any] = Field(default_factory=dict)
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class EvaluationResult(BaseModel):
    """Result of a values/ethics evaluation."""
    
    decision: PolicyEffect
    reason_codes: List[str] = Field(default_factory=list)  # Rule IDs that fired
    consent_scope: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Values & Ethics Service
# ============================================================================

class ValuesEthicsService:
    """
    Values & Ethics evaluation service.
    
    Evaluates goals, plans, curiosity signals, and world model updates
    against configured policies and user preferences.
    """
    
    def __init__(self, db: Any, logger=None):  # Agency system being redesigned
        self.db = db
        self.logger = logger
        
        # Cache for loaded policies and profiles
        self._policy_cache: Dict[str, List[PolicyRule]] = {}
        self._profile_cache: Dict[str, ValueProfile] = {}
    
    # ========================================================================
    # Core Evaluation APIs
    # ========================================================================
    
    def evaluate_goal(self, goal: Any, user_id: str) -> EvaluationResult:
        """
        Evaluate a goal against values/ethics policies.
        
        Args:
            goal: Goal object to evaluate
            user_id: User ID for context
            
        Returns:
            EvaluationResult with decision and reasons
        """
        # Get applicable policies
        policies = self._get_policies_for_target(PolicyTargetType.GOAL, user_id)
        
        # Get user profile
        profile = self._get_or_create_profile(user_id)
        
        # Evaluate against policies
        result = self._evaluate_against_policies(
            target=goal,
            target_type=PolicyTargetType.GOAL,
            policies=policies,
            profile=profile,
            context={"user_id": user_id}
        )
        
        if self.logger:
            self.logger.debug(
                f"[VALUES_ETHICS] Goal evaluation: {goal.goal_id} -> {result.decision.value}"
            )
        
        return result
    
    def evaluate_plan(self, plan: Any, user_id: str) -> EvaluationResult:
        """
        Evaluate a plan against values/ethics policies.
        
        Args:
            plan: Plan object to evaluate
            user_id: User ID for context
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = self._get_policies_for_target(PolicyTargetType.PLAN, user_id)
        profile = self._get_or_create_profile(user_id)
        
        result = self._evaluate_against_policies(
            target=plan,
            target_type=PolicyTargetType.PLAN,
            policies=policies,
            profile=profile,
            context={"user_id": user_id}
        )
        
        if self.logger:
            self.logger.debug(
                f"[VALUES_ETHICS] Plan evaluation: {plan.plan_id} -> {result.decision.value}"
            )
        
        return result
    
    def evaluate_curiosity_signal(self, signal: Any, user_id: str) -> EvaluationResult:
        """
        Evaluate a curiosity signal against values/ethics policies.
        
        Args:
            signal: CuriositySignal object to evaluate
            user_id: User ID for context
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = self._get_policies_for_target(PolicyTargetType.CURIOSITY_SIGNAL, user_id)
        profile = self._get_or_create_profile(user_id)
        
        result = self._evaluate_against_policies(
            target=signal,
            target_type=PolicyTargetType.CURIOSITY_SIGNAL,
            policies=policies,
            profile=profile,
            context={"user_id": user_id}
        )
        
        if self.logger:
            self.logger.debug(
                f"[VALUES_ETHICS] Curiosity signal evaluation: {signal.topic} -> {result.decision.value}"
            )
        
        return result
    
    def evaluate_world_model_change(
        self, 
        change: Dict[str, Any], 
        user_id: str
    ) -> EvaluationResult:
        """
        Evaluate a world model change against values/ethics policies.
        
        Args:
            change: World model change description
            user_id: User ID for context
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = self._get_policies_for_target(
            PolicyTargetType.WORLD_MODEL_UPDATE, 
            user_id
        )
        profile = self._get_or_create_profile(user_id)
        
        result = self._evaluate_against_policies(
            target=change,
            target_type=PolicyTargetType.WORLD_MODEL_UPDATE,
            policies=policies,
            profile=profile,
            context={"user_id": user_id}
        )
        
        if self.logger:
            self.logger.debug(
                f"[VALUES_ETHICS] World model change evaluation -> {result.decision.value}"
            )
        
        return result
    
    def record_consent(
        self,
        user_id: str,
        consent_scope: Dict[str, Any],
        decision: ConsentDecision,
        context: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> Consent:
        """
        Record explicit user consent or denial.
        
        Args:
            user_id: User ID
            consent_scope: What was consented to
            decision: granted or denied
            context: Optional context (goal_id, plan_id, etc.)
            expires_in_days: Optional expiration in days
            
        Returns:
            Consent record
        """
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        
        consent = Consent(
            user_id=user_id,
            consent_scope=consent_scope,
            decision=decision,
            context=context or {},
            expires_at=expires_at
        )
        
        # Store in database
        self.db.execute(
            """
            INSERT INTO consent_records (
                consent_id, user_id, consent_scope, decision, 
                context_json, granted_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                consent.consent_id,
                consent.user_id,
                json.dumps(consent.consent_scope),
                consent.decision.value,
                json.dumps(consent.context),
                consent.granted_at.isoformat(),
                consent.expires_at.isoformat() if consent.expires_at else None
            )
        )
        
        if self.logger:
            self.logger.info(
                f"[VALUES_ETHICS] Consent recorded: {decision.value} for {consent_scope}"
            )
        
        return consent
    
    # ========================================================================
    # Policy Management
    # ========================================================================
    
    def add_policy_rule(self, rule: PolicyRule) -> PolicyRule:
        """Add a new policy rule."""
        self.db.execute(
            """
            INSERT INTO ethics_policy_rules (
                rule_id, rule_name, target_type, conditions_json, effect,
                user_message_template, priority, enabled, scope, scope_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.rule_id,
                rule.rule_name,
                rule.target_type.value,
                json.dumps(rule.conditions),
                rule.effect.value,
                rule.user_message_template,
                rule.priority,
                1 if rule.enabled else 0,
                rule.scope.value,
                rule.scope_id,
                rule.created_at.isoformat(),
                rule.updated_at.isoformat()
            )
        )
        
        # Clear cache
        self._policy_cache.clear()
        
        if self.logger:
            self.logger.info(f"[VALUES_ETHICS] Policy rule added: {rule.rule_name}")
        
        return rule
    
    def get_policy_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a policy rule by ID."""
        row = self.db.fetch_one(
            "SELECT * FROM ethics_policy_rules WHERE rule_id = ?",
            (rule_id,)
        )
        
        if not row:
            return None
        
        return PolicyRule(
            rule_id=row["rule_id"],
            rule_name=row["rule_name"],
            target_type=PolicyTargetType(row["target_type"]),
            conditions=json.loads(row["conditions_json"]),
            effect=PolicyEffect(row["effect"]),
            user_message_template=row["user_message_template"],
            priority=row["priority"],
            enabled=bool(row["enabled"]),
            scope=PolicyScope(row["scope"]),
            scope_id=row["scope_id"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
        )
    
    # ========================================================================
    # Profile Management
    # ========================================================================
    
    def _get_or_create_profile(self, user_id: str) -> ValueProfile:
        """Get or create a value profile for a user."""
        # Check cache
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]
        
        # Check database
        row = self.db.fetch_one(
            "SELECT * FROM ethics_value_profiles WHERE user_id = ?",
            (user_id,)
        )
        
        if row:
            profile = ValueProfile(
                profile_id=row["profile_id"],
                user_id=row["user_id"],
                sensitive_life_areas=json.loads(row["sensitive_life_areas"] or "[]"),
                allowed_curiosity_domains=json.loads(row["allowed_curiosity_domains"] or "[]"),
                curiosity_intensity=row["curiosity_intensity"],
                proactive_behavior_level=ProactiveBehaviorLevel(row["proactive_behavior_level"]),
                storage_preferences=json.loads(row["storage_preferences"] or "{}"),
                created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
                updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
            )
        else:
            # Create default profile
            profile = ValueProfile(user_id=user_id)
            self.db.execute(
                """
                INSERT INTO ethics_value_profiles (
                    profile_id, user_id, sensitive_life_areas, 
                    allowed_curiosity_domains, curiosity_intensity,
                    proactive_behavior_level, storage_preferences,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.user_id,
                    json.dumps(profile.sensitive_life_areas),
                    json.dumps(profile.allowed_curiosity_domains),
                    profile.curiosity_intensity,
                    profile.proactive_behavior_level.value,
                    json.dumps(profile.storage_preferences),
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat()
                )
            )
        
        # Cache it
        self._profile_cache[user_id] = profile
        return profile
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    def _get_policies_for_target(
        self, 
        target_type: PolicyTargetType, 
        user_id: str
    ) -> List[PolicyRule]:
        """Get all applicable policies for a target type."""
        cache_key = f"{target_type.value}:{user_id}"
        
        if cache_key in self._policy_cache:
            return self._policy_cache[cache_key]
        
        # Get global + user-specific policies
        rows = self.db.fetch_all(
            """
            SELECT * FROM ethics_policy_rules 
            WHERE target_type = ? 
              AND enabled = 1
              AND (scope = 'global' OR (scope = 'user' AND scope_id = ?))
            ORDER BY priority ASC
            """,
            (target_type.value, user_id)
        )
        
        policies = []
        for row in rows:
            policies.append(PolicyRule(
                rule_id=row["rule_id"],
                rule_name=row["rule_name"],
                target_type=PolicyTargetType(row["target_type"]),
                conditions=json.loads(row["conditions_json"]),
                effect=PolicyEffect(row["effect"]),
                user_message_template=row["user_message_template"],
                priority=row["priority"],
                enabled=bool(row["enabled"]),
                scope=PolicyScope(row["scope"]),
                scope_id=row["scope_id"],
                created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
                updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC)
            ))
        
        self._policy_cache[cache_key] = policies
        return policies
    
    def _evaluate_against_policies(
        self,
        target: Any,
        target_type: PolicyTargetType,
        policies: List[PolicyRule],
        profile: ValueProfile,
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate target against policies.
        
        Returns the most restrictive decision from matching policies.
        """
        if not policies:
            # No policies = allow by default
            return EvaluationResult(decision=PolicyEffect.ALLOW)
        
        # Track all matching policies
        matching_policies: List[PolicyRule] = []
        
        for policy in policies:
            if self._policy_matches(target, policy, profile, context):
                matching_policies.append(policy)
        
        if not matching_policies:
            # No matching policies = allow
            return EvaluationResult(decision=PolicyEffect.ALLOW)
        
        # Find most restrictive effect
        # Priority: BLOCK > NEEDS_CONSENT > ALLOW_WITH_WARNING > ALLOW
        most_restrictive = matching_policies[0]
        for policy in matching_policies[1:]:
            if self._is_more_restrictive(policy.effect, most_restrictive.effect):
                most_restrictive = policy
        
        # Build result
        result = EvaluationResult(
            decision=most_restrictive.effect,
            reason_codes=[p.rule_id for p in matching_policies],
            user_message=most_restrictive.user_message_template
        )
        
        # Add consent scope if needed
        if result.decision == PolicyEffect.NEEDS_CONSENT:
            result.consent_scope = {
                "target_type": target_type.value,
                "rule_id": most_restrictive.rule_id,
                "rule_name": most_restrictive.rule_name
            }
        
        return result
    
    def _policy_matches(
        self,
        target: Any,
        policy: PolicyRule,
        profile: ValueProfile,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a policy's conditions match the target."""
        conditions = policy.conditions
        
        # If no conditions, policy doesn't match
        if not conditions:
            return False
        
        # All conditions must match for policy to apply
        for key, expected_value in conditions.items():
            if key == "origin":
                if not hasattr(target, "origin") or target.origin.value != expected_value:
                    return False
            elif key == "life_area":
                # Check if target touches sensitive life area
                # Only match if the expected value is in the sensitive areas list
                if expected_value == "sensitive":
                    # Check if any sensitive areas are configured
                    if not profile.sensitive_life_areas:
                        return False  # No sensitive areas = doesn't match
            elif key == "curiosity_intensity":
                # Check if signal score exceeds the threshold specified in the condition
                # The condition value is the threshold, and we check against profile's setting
                if hasattr(target, "total_score"):
                    # If signal score exceeds profile's curiosity_intensity threshold, match
                    if target.total_score <= profile.curiosity_intensity:
                        return False  # Signal is within acceptable range
                else:
                    return False
        
        # All conditions matched
        return True
    
    def _is_more_restrictive(self, effect1: PolicyEffect, effect2: PolicyEffect) -> bool:
        """Check if effect1 is more restrictive than effect2."""
        restrictiveness = {
            PolicyEffect.ALLOW: 0,
            PolicyEffect.ALLOW_WITH_WARNING: 1,
            PolicyEffect.NEEDS_CONSENT: 2,
            PolicyEffect.BLOCK: 3
        }
        return restrictiveness[effect1] > restrictiveness[effect2]
