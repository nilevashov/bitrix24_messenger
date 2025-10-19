"""Tenant service for multi-tenancy management."""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.tenant import Tenant
from ..api.schemas import PaginatedResponse


class TenantService:
    """Service for tenant management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by domain."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.domain == domain)
        )
        return result.scalar_one_or_none()
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(**tenant_data)
        
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return tenant
    
    async def update_tenant(self, tenant_id: str, tenant_data: Dict[str, Any]) -> Optional[Tenant]:
        """Update tenant."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        for key, value in tenant_data.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return tenant
    
    async def list_tenants(self, page: int = 1, size: int = 20) -> PaginatedResponse:
        """List tenants with pagination."""
        offset = (page - 1) * size
        
        # Get total count
        count_result = await self.db.execute(select(Tenant))
        total = len(count_result.scalars().all())
        
        # Get paginated results
        result = await self.db.execute(
            select(Tenant)
            .offset(offset)
            .limit(size)
        )
        tenants = result.scalars().all()
        
        return PaginatedResponse(
            items=[tenant for tenant in tenants],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    async def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate tenant."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.is_active = False
        await self.db.commit()
        
        return True

