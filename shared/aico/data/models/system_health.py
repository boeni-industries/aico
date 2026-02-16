"""SQLAlchemy models for system health monitoring tables."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SystemHealthCheck(Base):
    """Model for system_health_checks table."""
    
    __tablename__ = "system_health_checks"
    __table_args__ = (
        CheckConstraint("status IN ('ok', 'issues', 'error')", name="check_status_values"),
        Index("idx_health_checks_check_id", "check_id"),
        Index("idx_health_checks_started_at", "started_at"),
        {"schema": "aico_core"}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    check_id = Column(String(100), nullable=False)
    parent_check_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    issue_count = Column(Integer, default=0)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "check_id": self.check_id,
            "parent_check_id": self.parent_check_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "issue_count": self.issue_count,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemIssue(Base):
    """Model for system_issues table."""
    
    __tablename__ = "system_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('warning', 'error', 'critical')", name="check_severity_values"),
        CheckConstraint("status IN ('active', 'resolving', 'resolved')", name="check_issue_status_values"),
        Index("idx_issues_status", "status"),
        Index("idx_issues_severity", "severity"),
        Index("idx_issues_detected_at", "detected_at"),
        Index("idx_issues_service", "service"),
        {"schema": "aico_core"}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    issue_id = Column(String(100), unique=True, nullable=False)
    severity = Column(String(20), nullable=False)
    service = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active")
    metrics = Column(JSONB, nullable=True)
    impact = Column(JSONB, nullable=True)
    remediation = Column(JSONB, nullable=True)
    related_checks = Column(ARRAY(Text), nullable=True)
    perceptual_event_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "issue_id": self.issue_id,
            "severity": self.severity,
            "service": self.service,
            "title": self.title,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status,
            "metrics": self.metrics,
            "impact": self.impact,
            "remediation": self.remediation,
            "related_checks": self.related_checks,
            "perceptual_event_id": str(self.perceptual_event_id) if self.perceptual_event_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
