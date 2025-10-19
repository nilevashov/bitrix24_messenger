"""Bitrix24 OpenLines integration service."""

import httpx
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..models.tenant import Tenant
from ..models.dialog import Dialog, DialogStatus
from ..models.message import Message, MessageDirection, MessageStatus


class BitrixOpenLinesService:
    """Service for Bitrix24 OpenLines integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def send_message_to_openlines(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message to OpenLines session."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured")
        
        # Check if dialog exists
        dialog = await self._get_or_create_dialog(tenant_id, message_data)
        
        # Send message via imconnector.receiveMessage
        api_url = f"https://{tenant.bitrix_portal}/rest/1/{tenant.bitrix_oauth_access}/imconnector.receiveMessage"
        
        payload = {
            "CONNECTOR": "telegram",  # TODO: Make dynamic based on channel type
            "MESSAGE": {
                "ID": message_data.get("external_msg_id"),
                "CHAT_ID": message_data.get("chat_id"),
                "USER_ID": message_data.get("user_id"),
                "TEXT": message_data.get("text"),
                "DATE": message_data.get("timestamp"),
                "FILES": message_data.get("files", [])
            }
        }
        
        try:
            response = await self.client.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Update dialog with OpenLines session ID
            if result.get("result") and not dialog.bitrix_dialog_id:
                dialog.bitrix_dialog_id = result["result"].get("session_id")
                await self.db.commit()
            
            return {
                "success": True,
                "session_id": result.get("result", {}).get("session_id"),
                "dialog_id": str(dialog.id)
            }
            
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to send message to OpenLines: {str(e)}")
    
    async def handle_operator_message(
        self, 
        tenant_id: UUID, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle operator message from OpenLines."""
        try:
            # Extract session and message data
            session_id = event_data.get("data", {}).get("FIELDS", {}).get("SESSION_ID")
            message_text = event_data.get("data", {}).get("FIELDS", {}).get("MESSAGE")
            operator_id = event_data.get("data", {}).get("FIELDS", {}).get("USER_ID")
            
            if not session_id:
                return {"error": "No session ID in event"}
            
            # Find dialog by OpenLines session ID
            dialog = await self._get_dialog_by_session_id(tenant_id, session_id)
            if not dialog:
                return {"error": "Dialog not found"}
            
            # Create outbound message record
            message = Message(
                tenant_id=tenant_id,
                dialog_id=dialog.id,
                direction=MessageDirection.OUTBOUND,
                messenger=dialog.messenger,
                channel_id=dialog.channel_id,
                chat_id=dialog.chat_id,
                external_msg_id=f"bitrix_{session_id}_{operator_id}",
                dedup_key=f"bitrix_{session_id}_{operator_id}_{message_text}",
                text=message_text,
                status=MessageStatus.QUEUED
            )
            
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            
            # TODO: Send message to channel via adapter
            # This would be handled by the message router
            
            return {
                "success": True,
                "message_id": str(message.id),
                "dialog_id": str(dialog.id)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to handle operator message: {str(e)}")
    
    async def handle_session_start(
        self, 
        tenant_id: UUID, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle OpenLines session start."""
        try:
            session_id = event_data.get("data", {}).get("FIELDS", {}).get("SESSION_ID")
            user_id = event_data.get("data", {}).get("FIELDS", {}).get("USER_ID")
            
            if not session_id:
                return {"error": "No session ID in event"}
            
            # Find or create dialog
            dialog = await self._get_dialog_by_session_id(tenant_id, session_id)
            if dialog:
                # Update existing dialog
                dialog.status = DialogStatus.OPEN
                dialog.operator_user_id = user_id
            else:
                # Create new dialog (this shouldn't happen normally)
                dialog = Dialog(
                    tenant_id=tenant_id,
                    channel_id=UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Get from context
                    messenger="telegram",  # TODO: Get from context
                    chat_id="unknown",  # TODO: Get from context
                    bitrix_dialog_id=session_id,
                    status=DialogStatus.OPEN,
                    operator_user_id=user_id
                )
                self.db.add(dialog)
            
            await self.db.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "dialog_id": str(dialog.id)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to handle session start: {str(e)}")
    
    async def handle_session_finish(
        self, 
        tenant_id: UUID, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle OpenLines session finish."""
        try:
            session_id = event_data.get("data", {}).get("FIELDS", {}).get("SESSION_ID")
            
            if not session_id:
                return {"error": "No session ID in event"}
            
            # Find dialog
            dialog = await self._get_dialog_by_session_id(tenant_id, session_id)
            if not dialog:
                return {"error": "Dialog not found"}
            
            # Update dialog status
            dialog.status = DialogStatus.CLOSED
            dialog.closed_at = dialog.updated_at
            
            await self.db.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "dialog_id": str(dialog.id)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to handle session finish: {str(e)}")
    
    async def _get_or_create_dialog(
        self, 
        tenant_id: UUID, 
        message_data: Dict[str, Any]
    ) -> Dialog:
        """Get or create dialog for message."""
        chat_id = message_data.get("chat_id")
        messenger = message_data.get("messenger", "telegram")
        channel_id = message_data.get("channel_id")
        
        # Try to find existing dialog
        result = await self.db.execute(
            select(Dialog).where(
                Dialog.tenant_id == tenant_id,
                Dialog.messenger == messenger,
                Dialog.chat_id == chat_id,
                Dialog.status == DialogStatus.OPEN
            )
        )
        dialog = result.scalar_one_or_none()
        
        if not dialog:
            # Create new dialog
            dialog = Dialog(
                tenant_id=tenant_id,
                channel_id=channel_id,
                messenger=messenger,
                chat_id=chat_id,
                status=DialogStatus.OPEN
            )
            self.db.add(dialog)
            await self.db.commit()
            await self.db.refresh(dialog)
        
        return dialog
    
    async def _get_dialog_by_session_id(
        self, 
        tenant_id: UUID, 
        session_id: str
    ) -> Optional[Dialog]:
        """Get dialog by OpenLines session ID."""
        result = await self.db.execute(
            select(Dialog).where(
                Dialog.tenant_id == tenant_id,
                Dialog.bitrix_dialog_id == session_id
            )
        )
        return result.scalar_one_or_none()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
