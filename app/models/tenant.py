"""Tenant model for multi-tenancy support."""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class Tenant(Base):
    """Tenant model for multi-tenancy support."""
    
    __tablename__ = "tenant"
    
    # Basic tenant info
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    
    # Bitrix24 integration settings
    bitrix_portal = Column(String(255), nullable=False)  # portal.bitrix24.com
    bitrix_app_id = Column(String(255), nullable=True)
    bitrix_secret = Column(String(255), nullable=True)
    bitrix_oauth_access = Column(Text, nullable=True)
    bitrix_oauth_refresh = Column(Text, nullable=True)
    oauth_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Integration modes
    openlines_enabled = Column(Boolean, default=True, nullable=False)
    timeline_enabled = Column(Boolean, default=True, nullable=False)
    
    # Additional settings
    settings = Column(JSONB, default=dict, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)

