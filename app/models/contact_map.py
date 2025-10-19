"""Contact mapping model for linking messenger contacts to Bitrix entities."""

import enum
from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TenantMixin


class MessengerType(str, enum.Enum):
    """Messenger types."""
    
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VIBER = "viber"
    INSTAGRAM = "instagram"


class ContactMap(Base, TenantMixin):
    """Contact mapping between messenger contacts and Bitrix entities."""
    
    __tablename__ = "contact_map"
    
    # Messenger identification
    messenger = Column(Enum(MessengerType), nullable=False)
    chat_id = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    username = Column(String(255), nullable=True)
    
    # Bitrix entity references
    bitrix_contact_id = Column(String(50), nullable=True)
    bitrix_lead_id = Column(String(50), nullable=True)
    
    # Activity tracking
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("ix_contact_map_tenant_messenger_chat", "tenant_id", "messenger", "chat_id"),
        Index("ix_contact_map_tenant_phone", "tenant_id", "phone"),
        Index("ix_contact_map_tenant_username", "tenant_id", "username"),
        Index("ix_contact_map_tenant_bitrix_contact", "tenant_id", "bitrix_contact_id"),
    )

