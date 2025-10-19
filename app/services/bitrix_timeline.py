"""Bitrix24 CRM Timeline integration service."""

import httpx
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..models.tenant import Tenant
from ..models.contact_map import ContactMap
from ..models.deal_link import DealLink
from ..models.message import Message, MessageDirection, MessageStatus


class BitrixTimelineService:
    """Service for Bitrix24 CRM Timeline integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def send_message_to_timeline(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message to CRM timeline."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured")
        
        # Find or create contact
        contact_id = await self._find_or_create_contact(tenant_id, message_data)
        
        # Determine target entity (contact, lead, or deal)
        target_entity = await self._determine_target_entity(tenant_id, contact_id, message_data)
        
        # Create timeline comment
        comment_result = await self._create_timeline_comment(
            tenant, 
            target_entity, 
            message_data
        )
        
        return {
            "success": True,
            "contact_id": contact_id,
            "target_entity": target_entity,
            "comment_id": comment_result.get("result")
        }
    
    async def _find_or_create_contact(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> str:
        """Find or create contact in Bitrix24."""
        # Check if contact mapping exists
        contact_map = await self._get_contact_map(tenant_id, message_data)
        
        if contact_map and contact_map.bitrix_contact_id:
            return contact_map.bitrix_contact_id
        
        # Search for existing contact by phone
        phone = message_data.get("contact_info", {}).get("phone")
        if phone:
            existing_contact = await self._search_contact_by_phone(tenant_id, phone)
            if existing_contact:
                # Update contact mapping
                if contact_map:
                    contact_map.bitrix_contact_id = existing_contact["ID"]
                else:
                    contact_map = ContactMap(
                        tenant_id=tenant_id,
                        messenger=message_data.get("messenger", "telegram"),
                        chat_id=message_data.get("contact_info", {}).get("chat_id"),
                        phone=phone,
                        bitrix_contact_id=existing_contact["ID"]
                    )
                    self.db.add(contact_map)
                
                await self.db.commit()
                return existing_contact["ID"]
        
        # Create new contact
        new_contact = await self._create_contact(tenant_id, message_data)
        
        # Update or create contact mapping
        if contact_map:
            contact_map.bitrix_contact_id = new_contact["ID"]
        else:
            contact_map = ContactMap(
                tenant_id=tenant_id,
                messenger=message_data.get("messenger", "telegram"),
                chat_id=message_data.get("contact_info", {}).get("chat_id"),
                phone=phone,
                bitrix_contact_id=new_contact["ID"]
            )
            self.db.add(contact_map)
        
        await self.db.commit()
        return new_contact["ID"]
    
    async def _determine_target_entity(
        self, 
        tenant_id: UUID, 
        contact_id: str, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine target entity for timeline comment."""
        # Check for active deals
        active_deal = await self._get_active_deal(tenant_id, contact_id)
        
        if active_deal:
            return {
                "type": "deal",
                "id": active_deal.bitrix_deal_id,
                "title": f"Deal {active_deal.bitrix_deal_id}"
            }
        
        # Default to contact
        return {
            "type": "contact",
            "id": contact_id,
            "title": f"Contact {contact_id}"
        }
    
    async def _create_timeline_comment(
        self, 
        tenant: Tenant, 
        target_entity: Dict[str, Any], 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create timeline comment in Bitrix24."""
        api_url = f"https://{tenant.bitrix_portal}/rest/1/{tenant.bitrix_oauth_access}/crm.timeline.comment.add"
        
        # Prepare comment text
        messenger = message_data.get("messenger", "telegram").title()
        text = message_data.get("message_content", {}).get("text", "")
        
        comment_text = f"[{messenger}] {text}" if text else f"[{messenger}] Media message"
        
        # Handle media attachments
        files = []
        media_url = message_data.get("message_content", {}).get("media_url")
        if media_url:
            # TODO: Download and upload media to Bitrix Disk
            # For now, just include the URL in the comment
            comment_text += f"\n\nMedia: {media_url}"
        
        payload = {
            "fields": {
                "ENTITY_ID": target_entity["id"],
                "ENTITY_TYPE": target_entity["type"],
                "COMMENT": comment_text,
                "FILES": files
            }
        }
        
        try:
            response = await self.client.post(api_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to create timeline comment: {str(e)}")
    
    async def _get_contact_map(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Optional[ContactMap]:
        """Get contact mapping."""
        contact_info = message_data.get("contact_info", {})
        chat_id = contact_info.get("chat_id")
        messenger = message_data.get("messenger", "telegram")
        
        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.messenger == messenger,
                ContactMap.chat_id == chat_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _search_contact_by_phone(
        self, 
        tenant_id: UUID, 
        phone: str
    ) -> Optional[Dict[str, Any]]:
        """Search for contact by phone in Bitrix24."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            return None
        
        api_url = f"https://{tenant.bitrix_portal}/rest/1/{tenant.bitrix_oauth_access}/crm.contact.list"
        
        params = {
            "filter": {
                "PHONE": phone
            },
            "select": ["ID", "NAME", "LAST_NAME", "PHONE"]
        }
        
        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status()
            result = response.json()
            
            contacts = result.get("result", [])
            return contacts[0] if contacts else None
            
        except httpx.HTTPError:
            return None
    
    async def _create_contact(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new contact in Bitrix24."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured")
        
        api_url = f"https://{tenant.bitrix_portal}/rest/1/{tenant.bitrix_oauth_access}/crm.contact.add"
        
        contact_info = message_data.get("contact_info", {})
        
        fields = {
            "NAME": contact_info.get("first_name", ""),
            "LAST_NAME": contact_info.get("last_name", ""),
            "PHONE": [{"VALUE": contact_info.get("phone", ""), "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "MESSENGER",
            "SOURCE_DESCRIPTION": f"From {message_data.get('messenger', 'telegram').title()}"
        }
        
        payload = {"fields": fields}
        
        try:
            response = await self.client.post(api_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to create contact: {str(e)}")
    
    async def _get_active_deal(
        self, 
        tenant_id: UUID, 
        contact_id: str
    ) -> Optional[DealLink]:
        """Get active deal for contact."""
        result = await self.db.execute(
            select(DealLink).where(
                DealLink.tenant_id == tenant_id,
                DealLink.bitrix_contact_id == contact_id,
                DealLink.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
