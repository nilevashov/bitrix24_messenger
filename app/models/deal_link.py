"""Deal link model for tracking active deals per contact."""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TenantMixin


class DealLink(Base, TenantMixin):
    """Deal link for tracking active deals per contact."""
    
    __tablename__ = "deal_link"
    
    # Bitrix entity references
    bitrix_contact_id = Column(String(50), nullable=False)
    bitrix_deal_id = Column(String(50), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Activity tracking
    updated_at = Column(DateTime(timezone=True), nullable=False)
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_deal_link_tenant_contact", "tenant_id", "bitrix_contact_id"),
        Index("ix_deal_link_tenant_deal", "tenant_id", "bitrix_deal_id"),
        Index("ix_deal_link_tenant_contact_active", "tenant_id", "bitrix_contact_id", "is_active"),
    )

