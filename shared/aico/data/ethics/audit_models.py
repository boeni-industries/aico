"""
Ethics Audit Data Models

Dataclasses for ethics gate audit entities.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EthicsGateAudit:
    """Ethics gate audit model - matches ethics_gate_audit table."""
    audit_id: str
    user_id: str
    target_type: str
    target_id: str
    decision: str
    created_at: str
    reasoning: Optional[str] = None
    policy_rules_applied: Optional[str] = None
    check_level: int = 1
    cached: int = 0
    processing_time_ms: Optional[int] = None
