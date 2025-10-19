"""Audit log model for tracking system activities."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin


class AuditLog(Base, TenantMixin):
    """Audit log model for tracking system activities."""
    
    __tablename__ = "audit_log"
    
    # Actor information
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)
    details = Column(JSONB, default=dict, nullable=False)
    
    # Relationships
    actor = relationship("User", backref="audit_logs")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_audit_log_tenant_actor", "tenant_id", "actor_user_id"),
        Index("ix_audit_log_tenant_action", "tenant_id", "action"),
        Index("ix_audit_log_tenant_created_at", "tenant_id", "created_at"),
    )

