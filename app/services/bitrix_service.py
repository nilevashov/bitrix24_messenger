"""Bitrix24 integration service."""

import httpx
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..models.tenant import Tenant


class BitrixService:
    """Service for Bitrix24 integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def install_app(
        self, 
        tenant_id: UUID, 
        code: str, 
        domain: str, 
        member_id: str
    ) -> Dict[str, Any]:
        """Install Bitrix24 application and get OAuth tokens."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Exchange code for tokens
        token_url = f"https://{domain}/oauth/token/"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": tenant.bitrix_app_id,
            "client_secret": tenant.bitrix_secret,
            "code": code,
            "scope": "crm,im,imopenlines,disk"
        }
        
        try:
            response = await self.client.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()
            
            # Update tenant with tokens
            tenant.bitrix_oauth_access = tokens["access_token"]
            tenant.bitrix_oauth_refresh = tokens["refresh_token"]
            tenant.oauth_expires_at = tokens.get("expires_in")
            
            await self.db.commit()
            
            return tokens
            
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to exchange code for tokens: {str(e)}")
    
    async def refresh_token(self, tenant_id: UUID) -> Dict[str, Any]:
        """Refresh Bitrix24 OAuth token."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_refresh:
            raise ValueError("No refresh token available")
        
        refresh_url = f"https://{tenant.bitrix_portal}/oauth/token/"
        refresh_data = {
            "grant_type": "refresh_token",
            "client_id": tenant.bitrix_app_id,
            "client_secret": tenant.bitrix_secret,
            "refresh_token": tenant.bitrix_oauth_refresh
        }
        
        try:
            response = await self.client.post(refresh_url, data=refresh_data)
            response.raise_for_status()
            tokens = response.json()
            
            # Update tenant with new tokens
            tenant.bitrix_oauth_access = tokens["access_token"]
            tenant.bitrix_oauth_refresh = tokens["refresh_token"]
            tenant.oauth_expires_at = tokens.get("expires_in")
            
            await self.db.commit()
            
            return tokens
            
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to refresh token: {str(e)}")
    
    async def get_integration_status(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get Bitrix24 integration status."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return {"status": "not_configured"}
        
        status = {
            "tenant_id": str(tenant_id),
            "domain": tenant.bitrix_portal,
            "app_configured": bool(tenant.bitrix_app_id and tenant.bitrix_secret),
            "oauth_configured": bool(tenant.bitrix_oauth_access),
            "openlines_enabled": tenant.openlines_enabled,
            "timeline_enabled": tenant.timeline_enabled,
            "is_active": tenant.is_active
        }
        
        # Test API connection if tokens are available
        if tenant.bitrix_oauth_access:
            try:
                await self._test_api_connection(tenant)
                status["api_connection"] = "ok"
            except Exception as e:
                status["api_connection"] = f"error: {str(e)}"
        else:
            status["api_connection"] = "not_configured"
        
        return status
    
    async def _test_api_connection(self, tenant: Tenant) -> None:
        """Test API connection to Bitrix24."""
        api_url = f"https://{tenant.bitrix_portal}/rest/1/{tenant.bitrix_oauth_access}/user.current"
        
        try:
            response = await self.client.get(api_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ValueError(f"API connection failed: {str(e)}")
    
    async def send_to_openlines(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message to Bitrix24 OpenLines."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured")
        
        # TODO: Implement OpenLines message sending
        # This would involve calling imconnector.receiveMessage API
        
        return {"success": True, "message": "Sent to OpenLines"}
    
    async def send_to_timeline(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message to Bitrix24 CRM timeline."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured")
        
        # TODO: Implement timeline message sending
        # This would involve calling crm.timeline.comment.add API
        
        return {"success": True, "message": "Sent to timeline"}
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

