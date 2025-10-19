"""Dialog model for conversation sessions."""

import enum
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin


class DialogStatus(str, enum.Enum):
    """Dialog status."""
    
    OPEN = "open"
    CLOSED = "closed"
    PAUSED = "paused"


class Dialog(Base, TenantMixin):
    """Dialog model for conversation sessions."""
    
    __tablename__ = "dialog"
    
    # Channel and messenger info
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channel.id"), nullable=False)
    messenger = Column(String(50), nullable=False)  # telegram, whatsapp, etc.
    chat_id = Column(String(255), nullable=False)
    
    # Bitrix integration
    bitrix_dialog_id = Column(String(50), nullable=True)  # OpenLines session ID
    
    # Dialog state
    status = Column(Enum(DialogStatus), nullable=False, default=DialogStatus.OPEN)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Operator assignment
    operator_user_id = Column(String(50), nullable=True)  # Bitrix user ID
    
    # Relationships
    channel = relationship("Channel", backref="dialogs")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_dialog_tenant_channel", "tenant_id", "channel_id"),
        Index("ix_dialog_tenant_messenger_chat", "tenant_id", "messenger", "chat_id"),
        Index("ix_dialog_tenant_status", "tenant_id", "status"),
        Index("ix_dialog_tenant_bitrix_dialog", "tenant_id", "bitrix_dialog_id"),
    )

