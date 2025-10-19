"""Webhook event model for tracking incoming webhooks."""

import enum
from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base, TenantMixin


class WebhookSource(str, enum.Enum):
    """Webhook source."""
    
    CHANNEL = "channel"
    BITRIX = "bitrix"


class WebhookEvent(Base, TenantMixin):
    """Webhook event model for tracking incoming webhooks."""
    
    __tablename__ = "webhook_event"
    
    # Event identification
    source = Column(Enum(WebhookSource), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, default=dict, nullable=False)
    
    # Deduplication
    dedup_key = Column(String(255), nullable=False, unique=True)
    
    # Processing status
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_webhook_event_tenant_source", "tenant_id", "source"),
        Index("ix_webhook_event_tenant_dedup_key", "tenant_id", "dedup_key"),
        Index("ix_webhook_event_tenant_processed", "tenant_id", "processed_at"),
        Index("ix_webhook_event_tenant_created_at", "tenant_id", "created_at"),
    )

