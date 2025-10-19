"""Webhook service for processing incoming webhooks."""

import hashlib
import json
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.webhook_event import WebhookEvent, WebhookSource
from ..models.message import Message, MessageStatus
from ..services.message_service import MessageService


class WebhookService:
    """Service for processing webhook events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_service = MessageService(db)
    
    def _generate_dedup_key(self, source: str, payload: Dict[str, Any]) -> str:
        """Generate deduplication key for webhook event."""
        # Use source-specific logic to generate unique key
        if source == "bitrix":
            # For Bitrix webhooks, use event type and entity ID
            event_type = payload.get("event", "")
            entity_id = payload.get("data", {}).get("FIELDS", {}).get("ID", "")
            key_data = f"{source}:{event_type}:{entity_id}"
        else:
            # For channel webhooks, use message ID or update ID
            message_id = payload.get("message", {}).get("message_id") or payload.get("update_id")
            key_data = f"{source}:{message_id}"
        
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def process_bitrix_webhook(self, payload: Dict[str, Any], webhook_secret: Optional[str] = None) -> UUID:
        """Process incoming Bitrix24 webhook."""
        # Find tenant by webhook secret or payload
        tenant_id = await self._find_tenant_by_bitrix_webhook(payload, webhook_secret)
        if not tenant_id:
            raise ValueError("Could not determine tenant for Bitrix24 webhook")
        
        # Generate deduplication key
        dedup_key = self._generate_dedup_key("bitrix", payload)
        
        # Check if event already processed
        existing_event = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.dedup_key == dedup_key)
        )
        if existing_event.scalar_one_or_none():
            return existing_event.scalar_one().id
        
        # Create webhook event record
        event = WebhookEvent(
            tenant_id=tenant_id,
            source=WebhookSource.BITRIX,
            event_type=payload.get("event", "unknown"),
            payload=payload,
            dedup_key=dedup_key
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        # Process the event based on type
        await self._process_bitrix_event(event)
        
        return event.id
    
    async def process_channel_webhook(self, channel_type: str, payload: Dict[str, Any]) -> UUID:
        """Process incoming channel webhook."""
        # Find tenant by channel type and payload
        tenant_id = await self._find_tenant_by_channel_webhook(channel_type, payload)
        if not tenant_id:
            raise ValueError(f"Could not determine tenant for {channel_type} webhook")
        
        # Generate deduplication key
        dedup_key = self._generate_dedup_key(channel_type, payload)
        
        # Check if event already processed
        existing_event = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.dedup_key == dedup_key)
        )
        if existing_event.scalar_one_or_none():
            return existing_event.scalar_one().id
        
        # Create webhook event record
        event = WebhookEvent(
            tenant_id=tenant_id,
            source=WebhookSource.CHANNEL,
            event_type=f"{channel_type}_message",
            payload=payload,
            dedup_key=dedup_key
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        # Process the event based on channel type
        await self._process_channel_event(channel_type, event)
        
        return event.id
    
    async def _process_bitrix_event(self, event: WebhookEvent) -> None:
        """Process Bitrix24 event based on type."""
        event_type = event.event_type
        payload = event.payload
        
        if event_type == "ONIMBOTMESSAGEADD":
            # Operator replied to customer
            await self._handle_operator_message(payload)
        elif event_type == "ONIMOPENLINESESSIONSTART":
            # OpenLines session started
            await self._handle_session_start(payload)
        elif event_type == "ONIMOPENLINESESSIONFINISH":
            # OpenLines session finished
            await self._handle_session_finish(payload)
        elif event_type == "ONCRMLEADADD":
            # New lead created
            await self._handle_lead_add(payload)
        elif event_type == "ONCRMCONTACTADD":
            # New contact created
            await self._handle_contact_add(payload)
        
        # Mark event as processed
        event.processed_at = event.created_at
        await self.db.commit()
    
    async def _process_channel_event(self, channel_type: str, event: WebhookEvent) -> None:
        """Process channel event based on type."""
        if channel_type == "telegram":
            await self._handle_telegram_message(event)
        elif channel_type == "whatsapp":
            await self._handle_whatsapp_message(event)
        
        # Mark event as processed
        event.processed_at = event.created_at
        await self.db.commit()
    
    async def _handle_operator_message(self, payload: Dict[str, Any]) -> None:
        """Handle operator message from Bitrix24."""
        # TODO: Implement operator message handling
        # Extract message data and send to appropriate channel
        pass
    
    async def _handle_session_start(self, payload: Dict[str, Any]) -> None:
        """Handle OpenLines session start."""
        # TODO: Implement session start handling
        pass
    
    async def _handle_session_finish(self, payload: Dict[str, Any]) -> None:
        """Handle OpenLines session finish."""
        # TODO: Implement session finish handling
        pass
    
    async def _handle_lead_add(self, payload: Dict[str, Any]) -> None:
        """Handle new lead creation."""
        # TODO: Implement lead add handling
        pass
    
    async def _handle_contact_add(self, payload: Dict[str, Any]) -> None:
        """Handle new contact creation."""
        # TODO: Implement contact add handling
        pass
    
    async def _handle_telegram_message(self, event: WebhookEvent) -> None:
        """Handle Telegram message."""
        try:
            # Extract message data from Telegram webhook
            message_data = event.payload.get("message", {})
            if not message_data:
                return
            
            # Get channel info (we need to find the channel by tenant)
            # For now, we'll use a placeholder tenant_id
            tenant_id = event.tenant_id
            
            # Create normalized message data
            normalized_data = {
                "direction": "INBOUND",
                "messenger": "telegram",
                "chat_id": str(message_data.get("chat", {}).get("id")),
                "external_msg_id": str(message_data.get("message_id")),
                "text": message_data.get("text"),
                "media_url": None,
                "media_meta": {}
            }
            
            # Handle media if present
            bot_token = await self._get_bot_token(tenant_id)
            if message_data.get("photo") and bot_token:
                photo = message_data["photo"][-1]  # Get highest resolution
                normalized_data["media_url"] = f"https://api.telegram.org/file/bot{bot_token}/{photo['file_id']}"
                normalized_data["media_meta"] = {
                    "file_id": photo["file_id"],
                    "width": photo.get("width"),
                    "height": photo.get("height")
                }
            elif message_data.get("document") and bot_token:
                doc = message_data["document"]
                normalized_data["media_url"] = f"https://api.telegram.org/file/bot{bot_token}/{doc['file_id']}"
                normalized_data["media_meta"] = {
                    "file_id": doc["file_id"],
                    "file_name": doc.get("file_name"),
                    "mime_type": doc.get("mime_type"),
                    "file_size": doc.get("file_size")
                }
            
            # Create message record
            message = await self.message_service.create_message(tenant_id, normalized_data)
            
            # Route to Bitrix24 OpenLines
            await self._route_to_bitrix(tenant_id, message)
            
        except Exception as e:
            print(f"Error handling Telegram message: {str(e)}")
    
    async def _find_tenant_by_channel_webhook(self, channel_type: str, payload: Dict[str, Any]) -> Optional[UUID]:
        """Find tenant by channel webhook payload."""
        from ..models.channel import Channel, ChannelType
        
        if channel_type == "telegram":
            # For Telegram, we can try to identify the bot by checking webhook signatures
            # or by looking at the message content and matching with known channels
            
            # Method 1: Check if we have only one active Telegram channel
            result = await self.db.execute(
                select(Channel).where(
                    Channel.type == ChannelType.TELEGRAM,
                    Channel.state == "active"
                )
            )
            channels = result.scalars().all()
            
            if len(channels) == 1:
                # If there's only one active Telegram channel, use it
                return channels[0].tenant_id
            elif len(channels) > 1:
                # If multiple channels, we need a better way to identify
                # For now, return the first one, but log a warning
                print(f"Warning: Multiple active Telegram channels found, using first one")
                return channels[0].tenant_id
                
        elif channel_type == "whatsapp":
            # Similar logic for WhatsApp
            result = await self.db.execute(
                select(Channel).where(
                    Channel.type == ChannelType.WHATSAPP,
                    Channel.state == "active"
                )
            )
            channels = result.scalars().all()
            if channels:
                return channels[0].tenant_id
        
        return None
    
    async def _find_tenant_by_bitrix_webhook(self, payload: Dict[str, Any], webhook_secret: Optional[str] = None) -> Optional[UUID]:
        """Find tenant by Bitrix24 webhook payload or secret."""
        from ..models.tenant import Tenant
        
        # Method 1: Try to find by webhook secret
        if webhook_secret:
            # Store webhook secrets in tenant.settings
            result = await self.db.execute(
                select(Tenant).where(
                    Tenant.settings["webhook_secret"].astext == webhook_secret
                )
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant.id
        
        # Method 2: Try to extract domain from payload
        # Bitrix24 webhooks sometimes contain domain information
        domain = payload.get("domain") or payload.get("data", {}).get("domain")
        if domain:
            result = await self.db.execute(
                select(Tenant).where(Tenant.bitrix_portal == domain)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant.id
        
        # Method 3: For now, return the first active tenant
        # In production, you should implement proper tenant identification
        result = await self.db.execute(
            select(Tenant).where(Tenant.is_active == True)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant.id
        
        return None
    
    async def _get_bot_token(self, tenant_id: UUID) -> Optional[str]:
        """Get bot token for tenant from channel config."""
        from ..models.channel import Channel, ChannelType
        
        # Find active Telegram channel for this tenant
        result = await self.db.execute(
            select(Channel).where(
                Channel.tenant_id == tenant_id,
                Channel.type == ChannelType.TELEGRAM,
                Channel.state == "active"
            )
        )
        channel = result.scalar_one_or_none()
        
        if channel and channel.config:
            return channel.config.get("bot_token")
        
        return None
    
    async def _route_to_bitrix(self, tenant_id: UUID, message: Message) -> None:
        """Route message to Bitrix24 OpenLines."""
        try:
            from .bitrix_openlines import BitrixOpenLinesService
            
            # Create OpenLines service
            openlines_service = BitrixOpenLinesService(self.db)
            
            # Prepare message data for OpenLines
            message_data = {
                "external_msg_id": message.external_msg_id,
                "chat_id": message.chat_id,
                "user_id": message.chat_id,  # For Telegram, user_id is same as chat_id
                "text": message.text,
                "timestamp": message.created_at.isoformat(),
                "files": []
            }
            
            # Add media file if present
            if message.media_url:
                message_data["files"].append({
                    "url": message.media_url,
                    "type": message.media_meta.get("mime_type", "image"),
                    "name": message.media_meta.get("file_name", "file")
                })
            
            # Send to OpenLines
            result = await openlines_service.send_message_to_openlines(tenant_id, message_data)
            
            # Update message with OpenLines session info
            if result.get("session_id"):
                # TODO: Store session_id in message or dialog
                pass
            
            print(f"Message routed to Bitrix24: {result}")
            
        except Exception as e:
            print(f"Error routing to Bitrix24: {str(e)}")
            # Update message status to failed
            await self.message_service.update_message_status(
                tenant_id, 
                str(message.id), 
                MessageStatus.FAILED, 
                str(e)
            )
    
    async def _handle_whatsapp_message(self, event: WebhookEvent) -> None:
        """Handle WhatsApp message."""
        # TODO: Implement WhatsApp message processing
        # Extract message data, normalize, and route to Bitrix
        pass

