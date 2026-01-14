"""
Consent Data Models

Dataclasses for consent management.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ConsentUserConsent:
    """Consent user consent model - matches consent_user_consents table."""
    consent_id: str
    user_id: str
    consent_type: str
    scope: str
    granted: int
    granted_at: str
    created_at: str
    updated_at: str
    scope_identifier: Optional[str] = None
    expires_at: Optional[str] = None
    inherited_from: Optional[str] = None
    revoked_at: Optional[str] = None


@dataclass
class ConsentRecord:
    """Consent record model - matches consent_records table."""
    consent_id: str
    user_id: str
    consent_scope: str
    decision: str
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    context_json: Optional[Dict[str, Any]] = None


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
