"""Message model for storing all messages."""

import enum
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin


class MessageDirection(str, enum.Enum):
    """Message direction."""
    
    INBOUND = "in"
    OUTBOUND = "out"


class MessageStatus(str, enum.Enum):
    """Message delivery status."""
    
    RECEIVED = "received"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Message(Base, TenantMixin):
    """Message model for storing all messages."""
    
    __tablename__ = "message"
    
    # Dialog reference
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("dialog.id"), nullable=False)
    
    # Message direction and channel info
    direction = Column(Enum(MessageDirection), nullable=False)
    messenger = Column(String(50), nullable=False)
    channel_id = Column(UUID(as_uuid=True), nullable=False)
    chat_id = Column(String(255), nullable=False)
    
    # External message identification
    external_msg_id = Column(String(255), nullable=False)
    dedup_key = Column(String(255), nullable=False, unique=True)  # For idempotency
    
    # Message content
    text = Column(Text, nullable=True)
    media_url = Column(String(500), nullable=True)
    media_meta = Column(JSONB, default=dict, nullable=False)
    
    # Delivery status and timestamps
    status = Column(Enum(MessageStatus), nullable=False, default=MessageStatus.RECEIVED)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    fail_reason = Column(Text, nullable=True)
    
    # Relationships
    dialog = relationship("Dialog", backref="messages")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_message_tenant_dialog", "tenant_id", "dialog_id"),
        Index("ix_message_tenant_external_msg", "tenant_id", "external_msg_id"),
        Index("ix_message_tenant_dedup_key", "tenant_id", "dedup_key"),
        Index("ix_message_tenant_status", "tenant_id", "status"),
        Index("ix_message_tenant_messenger_chat", "tenant_id", "messenger", "chat_id"),
        Index("ix_message_tenant_created_at", "tenant_id", "created_at"),
    )

