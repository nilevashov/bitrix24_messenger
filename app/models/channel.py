"""Channel model for messenger channels."""

import enum
from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, TenantMixin


class ChannelType(str, enum.Enum):
    """Supported channel types."""
    
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VIBER = "viber"
    INSTAGRAM = "instagram"


class ChannelState(str, enum.Enum):
    """Channel state."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Channel(Base, TenantMixin):
    """Channel model for messenger channels."""
    
    __tablename__ = "channel"
    
    # Channel identification
    type = Column(Enum(ChannelType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    name = Column(String(255), nullable=False)
    state = Column(Enum(ChannelState, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ChannelState.INACTIVE)
    
    # Channel configuration (bot tokens, provider credentials, etc.)
    config = Column(JSONB, default=dict, nullable=False)
    
    # External channel ID (bot ID, phone number, etc.)
    external_channel_id = Column(String(255), nullable=True)
    
    # Additional metadata
    meta = Column(JSONB, default=dict, nullable=False)

