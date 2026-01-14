"""
Consent Audit Data Models

Dataclasses for consent audit log entities.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConsentAuditLog:
    """Consent audit log model - matches consent_audit_log table."""
    audit_id: str
    consent_id: str
    user_id: str
    action: str
    created_at: str
    reason: Optional[str] = None
    metadata: Optional[str] = None
