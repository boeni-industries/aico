"""
Ethics Data Models

Dataclasses for ethics system.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EthicsDecisionsCache:
    """Ethics decisions cache model - matches ethics_decisions_cache table."""
    cache_id: str
    user_id: str
    target_type: str
    target_id: str
    decision: str
    cached_at: str
    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None
    confidence: float = 1.0
    expires_at: Optional[str] = None
    hit_count: int = 0
    last_hit_at: Optional[str] = None


@dataclass
class EthicsGateAudit:
    """Ethics gate audit model - matches ethics_gate_audit table."""
    audit_id: str
    user_id: str
    gate_type: str
    target_type: str
    target_id: str
    decision: str
    timestamp: str
    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None
    confidence: float = 1.0
    override_by: Optional[str] = None
    override_reason: Optional[str] = None


@dataclass
class EthicsPolicyRule:
    """Ethics policy rule model - matches ethics_policy_rules table."""
    rule_id: str
    rule_name: str
    rule_type: str
    priority: int
    condition_json: str
    action: str
    created_at: str
    updated_at: str
    enabled: bool = True
    description: Optional[str] = None


@dataclass
class EthicsValueProfile:
    """Ethics value profile model - matches ethics_value_profiles table."""
    profile_id: str
    user_id: str
    value_weights_json: str
    created_at: str
    updated_at: str
    profile_name: Optional[str] = None
    is_active: bool = True
