"""Routing rule model for message routing configuration."""

import enum
from sqlalchemy import Column, String, Enum
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, TenantMixin


class RoutingTarget(str, enum.Enum):
    """Routing target."""
    
    OPENLINES = "openlines"
    TIMELINE = "timeline"


class AssignStrategy(str, enum.Enum):
    """Assignment strategy."""
    
    BY_CITY = "by_city"
    ROUND_ROBIN = "round_robin"
    FIXED = "fixed"


class RoutingRule(Base, TenantMixin):
    """Routing rule model for message routing configuration."""
    
    __tablename__ = "routing_rule"
    
    # Rule configuration
    name = Column(String(255), nullable=False)
    predicate = Column(JSONB, default=dict, nullable=False)  # Regexp rules, conditions
    
    # Routing target
    target = Column(Enum(RoutingTarget), nullable=False)
    
    # Assignment strategy
    assign_strategy = Column(Enum(AssignStrategy), nullable=False, default=AssignStrategy.ROUND_ROBIN)
    
    # Additional parameters
    params = Column(JSONB, default=dict, nullable=False)
    
    # Rule priority and status
    priority = Column(String(10), default="100", nullable=False)
    is_active = Column(String(10), default="true", nullable=False)

