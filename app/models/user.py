"""User model for authentication and authorization."""

import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TenantMixin


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"
    SERVICE = "service"


class UserStatus(str, enum.Enum):
    """User status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base, TenantMixin):
    """User model for authentication and authorization."""
    
    __tablename__ = "user"
    
    # Basic user info
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Role and status
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserRole.VIEWER)
    status = Column(Enum(UserStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserStatus.ACTIVE)
    
    # Authentication
    mfa_secret = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", backref="users")

