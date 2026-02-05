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


class AutonomyLevel(str, Enum):
    """User preference for autonomy level."""
    QUIET = "quiet"
    BALANCED = "balanced"
    PROACTIVE = "proactive"
    AUTONOMOUS = "autonomous"


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
    autonomy_level: AutonomyLevel  # No default - must be set explicitly from config
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
    
    def __init__(self, logger=None):
        self.logger = logger
        
        # Cache for loaded policies and profiles
        self._policy_cache: Dict[str, List[PolicyRule]] = {}
        self._profile_cache: Dict[str, ValueProfile] = {}
    
    # ========================================================================
    # Core Evaluation APIs
    # ========================================================================
    
    async def evaluate_goal(self, goal: Any, user_id: str, uow: "UnitOfWork") -> EvaluationResult:
        """
        Evaluate a goal against values/ethics policies.
        
        Args:
            goal: Goal object to evaluate
            user_id: User ID for context
            uow: Unit of Work for database access
            
        Returns:
            EvaluationResult with decision and reasons
        """
        # Get applicable policies
        policies = await self._get_policies_for_target(PolicyTargetType.GOAL, user_id, uow)
        
        # Get user profile
        profile = await self._get_or_create_profile(user_id, uow)
        
        # Evaluate against policies
        result = await self._evaluate_against_policies(
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
    
    async def evaluate_plan(self, plan: Any, user_id: str, uow: "UnitOfWork") -> EvaluationResult:
        """
        Evaluate a plan against values/ethics policies.
        
        Args:
            plan: Plan object to evaluate
            user_id: User ID for context
            uow: Unit of Work for database access
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = await self._get_policies_for_target(PolicyTargetType.PLAN, user_id, uow)
        profile = await self._get_or_create_profile(user_id, uow)
        
        result = await self._evaluate_against_policies(
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
    
    async def evaluate_curiosity_signal(self, signal: Any, user_id: str, uow: "UnitOfWork") -> EvaluationResult:
        """
        Evaluate a curiosity signal against values/ethics policies.
        
        Args:
            signal: CuriositySignal object to evaluate
            user_id: User ID for context
            uow: Unit of Work for database access
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = await self._get_policies_for_target(PolicyTargetType.CURIOSITY_SIGNAL, user_id, uow)
        profile = await self._get_or_create_profile(user_id, uow)
        
        result = await self._evaluate_against_policies(
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
    
    async def evaluate_world_model_change(
        self, 
        change: Dict[str, Any], 
        user_id: str,
        uow: "UnitOfWork"
    ) -> EvaluationResult:
        """
        Evaluate a world model change against values/ethics policies.
        
        Args:
            change: World model change description
            user_id: User ID for context
            uow: Unit of Work for database access
            
        Returns:
            EvaluationResult with decision and reasons
        """
        policies = await self._get_policies_for_target(
            PolicyTargetType.WORLD_MODEL_UPDATE, 
            user_id,
            uow
        )
        profile = await self._get_or_create_profile(user_id, uow)
        
        result = await self._evaluate_against_policies(
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
    
    async def record_consent(
        self,
        user_id: str,
        consent_scope: Dict[str, Any],
        decision: ConsentDecision,
        uow: "UnitOfWork",
        context: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> Consent:
        """
        Record explicit user consent or denial.
        
        Args:
            user_id: User ID
            consent_scope: What the consent applies to
            decision: Granted or denied
            uow: Unit of Work for database access
            context: Optional context for the consent
            expires_in_days: Optional expiration in days
            
        Returns:
            Consent record
        """
        from aico.data.consent.models import ConsentRecord
        
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
        
        # Create entity and store in database
        entity = ConsentRecord(
            consent_id=consent.consent_id,
            user_id=consent.user_id,
            consent_scope_json=json.dumps(consent.consent_scope),
            decision=consent.decision.value,
            context_json=json.dumps(consent.context),
            expires_at=consent.expires_at,
            created_at=consent.created_at
        )
        
        await uow.consent_records.create(entity)
        await uow.commit()
        
        if self.logger:
            self.logger.info(
                f"[VALUES_ETHICS] Recorded consent: {decision.value} for {user_id}"
            )
        
        return consent
    
    # ========================================================================
    # Policy Management
    # ========================================================================
    
    async def add_policy_rule(self, rule: PolicyRule, uow: "UnitOfWork") -> PolicyRule:
        """Add a new policy rule."""
        from aico.data.ethics.models import EthicsPolicyRule
        
        entity = EthicsPolicyRule(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            target_type=rule.target_type.value,
            conditions_json=rule.conditions,  # Pass dict directly, not JSON string
            effect=rule.effect.value,
            user_message_template=rule.user_message_template,
            priority=rule.priority,
            enabled=rule.enabled,
            scope=rule.scope.value,
            scope_id=rule.scope_id,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        
        await uow.ethics_policy_rules.create(entity)
        await uow.commit()
        
        # Invalidate cache
        self._policy_cache.clear()
        
        if self.logger:
            self.logger.info(f"[VALUES_ETHICS] Policy rule added: {rule.rule_name}")
        
        return rule
    
    async def get_policy_rule(self, rule_id: str, uow: "UnitOfWork") -> Optional[PolicyRule]:
        """Get a policy rule by ID."""
        from aico.data.ethics.models import EthicsPolicyRule
        
        entity = await uow.ethics_policy_rules.get_by_id(rule_id)
        
        if not entity:
            return None
        
        return PolicyRule(
            rule_id=entity.rule_id,
            rule_name=entity.rule_name,
            target_type=PolicyTargetType(entity.target_type),
            conditions=entity.conditions_json,
            effect=PolicyEffect(entity.effect),
            user_message_template=entity.user_message_template,
            priority=entity.priority,
            enabled=entity.enabled,
            scope=PolicyScope(entity.scope),
            scope_id=entity.scope_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    # ========================================================================
    # Profile Management
    # ========================================================================
    
    async def _get_or_create_profile(self, user_id: str, uow: "UnitOfWork") -> ValueProfile:
        """Get or create user value profile."""
        from aico.data.ethics.models import EthicsValueProfile
        
        # Check cache
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]
        
        # Check database
        profiles = await uow.ethics_value_profiles.list(filters={"user_id": user_id}, limit=1)
        
        if profiles:
            entity = profiles[0]
            profile = ValueProfile(
                profile_id=entity.profile_id,
                user_id=entity.user_id,
                sensitive_life_areas=json.loads(entity.sensitive_life_areas) if entity.sensitive_life_areas else [],
                allowed_curiosity_domains=json.loads(entity.allowed_curiosity_domains) if entity.allowed_curiosity_domains else [],
                curiosity_intensity=entity.curiosity_intensity,
                autonomy_level=AutonomyLevel(entity.autonomy_level),
                storage_preferences=json.loads(entity.storage_preferences) if entity.storage_preferences else {},
                created_at=entity.created_at,
                updated_at=entity.updated_at
            )
            self._profile_cache[user_id] = profile
            return profile
        else:
            # Create default profile - read autonomy level from configuration
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            default_autonomy = config.get("agency.safety_control.autonomy_level", "balanced")
            
            profile = ValueProfile(
                user_id=user_id,
                autonomy_level=AutonomyLevel(default_autonomy)
            )
            entity = EthicsValueProfile(
                profile_id=profile.profile_id,
                user_id=profile.user_id,
                sensitive_life_areas=json.dumps(profile.sensitive_life_areas),
                allowed_curiosity_domains=json.dumps(profile.allowed_curiosity_domains),
                curiosity_intensity=profile.curiosity_intensity,
                autonomy_level=profile.autonomy_level.value,
                storage_preferences=json.dumps(profile.storage_preferences),
                created_at=profile.created_at,
                updated_at=profile.updated_at
            )
            await uow.ethics_value_profiles.create(entity)
            await uow.commit()
            self._profile_cache[user_id] = profile
            return profile
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    async def _get_policies_for_target(
        self, 
        target_type: PolicyTargetType, 
        user_id: Optional[str],
        uow: "UnitOfWork"
    ) -> List[PolicyRule]:
        """Get applicable policies for a target type."""
        cache_key = f"{target_type.value}:{user_id or 'global'}"
        
        # Check cache
        if cache_key in self._policy_cache:
            return self._policy_cache[cache_key]
        
        # Get global + user-specific policies
        all_policies = await uow.ethics_policy_rules.list(
            filters={"target_type": target_type.value, "enabled": True}
        )
        
        # Filter to global or matching user
        relevant_policies = [
            p for p in all_policies
            if p.scope == "global" or (p.scope == "user" and p.scope_id == user_id)
        ]
        
        # Sort by priority ascending
        relevant_policies.sort(key=lambda p: p.priority)
        
        policies = []
        for entity in relevant_policies:
            policies.append(PolicyRule(
                rule_id=entity.rule_id,
                rule_name=entity.rule_name,
                target_type=PolicyTargetType(entity.target_type),
                conditions=entity.conditions_json,
                effect=PolicyEffect(entity.effect),
                user_message_template=entity.user_message_template,
                priority=entity.priority,
                enabled=entity.enabled,
                scope=PolicyScope(entity.scope),
                scope_id=entity.scope_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at
            ))
        
        self._policy_cache[cache_key] = policies
        return policies
    
    async def _evaluate_against_policies(
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
