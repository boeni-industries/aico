"""
Consent Domain Models

Rich domain models for consent management entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ConsentScope(str, Enum):
    """Consent scope enumeration."""
    GLOBAL = "global"
    FEATURE = "feature"
    DATA_TYPE = "data_type"


class ConsentUserConsent(BaseModel):
    """User consent domain model."""
    consent_id: str
    user_id: str
    consent_type: str
    scope: ConsentScope
    granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class ConsentAuditLog(BaseModel):
    """Consent audit log domain model."""
    audit_id: str
    consent_id: str
    user_id: str
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class ConsentRecord(BaseModel):
    """Consent record domain model."""
    record_id: str
    user_id: str
    consent_type: str
    status: str
    version: int = 1
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
