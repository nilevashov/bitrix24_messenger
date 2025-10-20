"""Webhook service for processing incoming webhooks."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.factory import ChannelAdapterFactory
from ..models.channel import Channel, ChannelState, ChannelType
from ..models.contact_map import ContactMap, MessengerType
from ..models.deal_link import DealLink
from ..models.message import Message, MessageStatus
from ..models.webhook_event import WebhookEvent, WebhookSource
from ..services.bitrix_openlines import BitrixOpenLinesService
from ..services.message_service import MessageService


class WebhookService:
    """Service for processing webhook events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_service = MessageService(db)
    
    def _generate_dedup_key(
        self,
        source: str,
        payload: Dict[str, Any],
        *,
        channel_id: Optional[UUID] = None
    ) -> str:
        """Generate deduplication key for webhook event."""
        if source == "bitrix":
            event_type = payload.get("event", "")
            entity_id = payload.get("data", {}).get("FIELDS", {}).get("ID", "")
            key_data = f"{source}:{event_type}:{entity_id}"
        else:
            message_id = (
                payload.get("message", {}).get("message_id")
                or payload.get("edited_message", {}).get("message_id")
                or payload.get("update_id")
                or payload.get("id")
            )
            key_data = f"{source}:{message_id or uuid4()}"

        if channel_id:
            key_data = f"{key_data}:{channel_id}"

        return hashlib.sha256(str(key_data).encode()).hexdigest()
    
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
    
    async def process_channel_webhook(
        self,
        channel_type: str,
        payload: Dict[str, Any],
        *,
        channel_token: Optional[str] = None
    ) -> UUID:
        """Process incoming channel webhook."""
        channel = await self._resolve_channel_from_webhook(channel_type, payload, channel_token)
        if not channel:
            raise ValueError(f"Could not determine tenant for {channel_type} webhook")

        tenant_id = channel.tenant_id
        dedup_key = self._generate_dedup_key(channel_type, payload, channel_id=channel.id)
        
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
            dedup_key=dedup_key,
            channel_id=channel.id,
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        # Process the event based on channel type
        await self._process_channel_event(channel_type, event, channel)
        
        return event.id
    
    async def _process_bitrix_event(self, event: WebhookEvent) -> None:
        """Process Bitrix24 event based on type."""
        event_type = event.event_type
        normalized_type = event_type.upper()

        if normalized_type == "ONIMBOTMESSAGEADD":
            await self._handle_operator_message(event)
        elif normalized_type == "ONIMOPENLINESESSIONSTART":
            await self._handle_session_start(event)
        elif normalized_type == "ONIMOPENLINESESSIONFINISH":
            await self._handle_session_finish(event)
        elif normalized_type == "ONCRMLEADADD":
            await self._handle_lead_add(event)
        elif normalized_type == "ONCRMCONTACTADD":
            await self._handle_contact_add(event)
        elif normalized_type in {"ONCRMDEALADD", "ONCRMDEALUPDATE"}:
            await self._handle_deal_change(event)
        elif normalized_type == "ONCRMDEALDELETE":
            await self._handle_deal_delete(event)

        event.processed_at = datetime.utcnow()
        await self.db.commit()
    
    async def _process_channel_event(self, channel_type: str, event: WebhookEvent, channel: Channel) -> None:
        """Process channel event based on type."""
        resolved_type = channel_type.lower()

        if resolved_type == ChannelType.TELEGRAM.value:
            await self._handle_telegram_message(event, channel)
        elif resolved_type == ChannelType.WHATSAPP.value:
            await self._handle_whatsapp_message(event, channel)

        event.processed_at = datetime.utcnow()
        await self.db.commit()
    
    async def _handle_operator_message(self, event: WebhookEvent) -> None:
        service = BitrixOpenLinesService(self.db)
        await service.handle_operator_message(event.tenant_id, event.payload)

    async def _handle_session_start(self, event: WebhookEvent) -> None:
        service = BitrixOpenLinesService(self.db)
        await service.handle_session_start(event.tenant_id, event.payload)

    async def _handle_session_finish(self, event: WebhookEvent) -> None:
        service = BitrixOpenLinesService(self.db)
        await service.handle_session_finish(event.tenant_id, event.payload)

    async def _handle_lead_add(self, event: WebhookEvent) -> None:
        await self._upsert_contact_entity(event.tenant_id, event.payload, entity_type="lead")

    async def _handle_contact_add(self, event: WebhookEvent) -> None:
        await self._upsert_contact_entity(event.tenant_id, event.payload, entity_type="contact")

    async def _handle_deal_change(self, event: WebhookEvent) -> None:
        await self._upsert_deal_link(event.tenant_id, event.payload)

    async def _handle_deal_delete(self, event: WebhookEvent) -> None:
        await self._deactivate_deal_link(event.tenant_id, event.payload)
    
    async def _handle_telegram_message(self, event: WebhookEvent, channel: Channel) -> None:
        adapter = ChannelAdapterFactory.create_adapter(channel.type.value, channel.config or {})
        adapter.channel_id = channel.id
        adapter.tenant_id = event.tenant_id

        normalized = await adapter.process_webhook(event.payload)
        if not normalized or normalized.get("error"):
            raise ValueError(f"Failed to normalize Telegram message: {normalized}")

        contact_info = normalized.get("contact_info") or {}
        message_content = normalized.get("message_content") or {}
        chat_id = contact_info.get("chat_id")

        if not chat_id:
            raise ValueError("Telegram webhook missing chat_id")

        message_payload: Dict[str, Any] = {
            "direction": "INBOUND",
            "messenger": channel.type.value,
            "channel_id": str(channel.id),
            "chat_id": str(chat_id),
            "external_msg_id": normalized.get("external_msg_id"),
            "text": message_content.get("text"),
            "media_url": message_content.get("media_url"),
            "media_meta": message_content.get("media_meta") or {},
            "status": MessageStatus.RECEIVED,
        }

        message = await self.message_service.create_message(event.tenant_id, message_payload)
        await self._upsert_contact_map(event.tenant_id, channel, contact_info)
        await self._route_to_bitrix(event.tenant_id, channel, message, contact_info)
    async def _resolve_channel_from_webhook(
        self,
        channel_type: str,
        payload: Dict[str, Any],
        channel_token: Optional[str]
    ) -> Optional[Channel]:
        try:
            resolved_type = ChannelType(channel_type.lower())
        except ValueError as exc:
            raise ValueError(f"Unsupported channel type: {channel_type}") from exc

        query = select(Channel).where(
            Channel.type == resolved_type,
            Channel.state == ChannelState.ACTIVE,
        )

        if channel_token:
            query = query.where(Channel.config["webhook_secret"].astext == channel_token)
            result = await self.db.execute(query.limit(1))
            channel = result.scalar_one_or_none()
            if not channel:
                raise ValueError("Invalid channel webhook secret provided")
            return channel

        result = await self.db.execute(query.limit(2))
        channels = result.scalars().all()
        if len(channels) == 1:
            return channels[0]
        if len(channels) > 1:
            raise ValueError("Multiple active channels found. Use dedicated webhook secret in URL.")
        return None
    async def _find_tenant_by_bitrix_webhook(self, payload: Dict[str, Any], webhook_secret: Optional[str] = None) -> Optional[UUID]:
        from ..models.tenant import Tenant

        if webhook_secret:
            result = await self.db.execute(
                select(Tenant).where(Tenant.settings["webhook_secret"].astext == webhook_secret)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant.id

        domain = payload.get("domain") or payload.get("data", {}).get("domain")
        if domain:
            result = await self.db.execute(select(Tenant).where(Tenant.bitrix_portal == domain))
            tenant = result.scalar_one_or_none()
            if tenant:
                return tenant.id

        result = await self.db.execute(select(Tenant).where(Tenant.is_active == True))
        tenant = result.scalar_one_or_none()
        if tenant:
            return tenant.id
        return None

    async def _route_to_bitrix(
        self,
        tenant_id: UUID,
        channel: Channel,
        message: Message,
        contact_info: Optional[Dict[str, Any]] = None
    ) -> None:
        try:
            openlines_service = BitrixOpenLinesService(self.db)
            await openlines_service.send_message_to_openlines(
                tenant_id,
                channel,
                message,
                contact_info or {},
            )
        except Exception as exc:
            await self.message_service.update_message_status(
                tenant_id,
                str(message.id),
                MessageStatus.FAILED,
                str(exc),
            )
            raise

    async def _handle_whatsapp_message(self, event: WebhookEvent, channel: Channel) -> None:
        raise NotImplementedError("WhatsApp webhook processing is not implemented yet")

    async def _upsert_contact_map(
        self,
        tenant_id: UUID,
        channel: Channel,
        contact_info: Dict[str, Any]
    ) -> None:
        chat_id = contact_info.get("chat_id")
        if not chat_id:
            return

        try:
            messenger_type = MessengerType(channel.type.value)
        except ValueError:
            return

        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.messenger == messenger_type,
                ContactMap.chat_id == str(chat_id),
            )
        )
        contact = result.scalar_one_or_none()
        now = datetime.utcnow()
        if contact:
            contact.last_seen_at = now
            if contact_info.get("username"):
                contact.username = contact_info.get("username")
            if contact_info.get("phone"):
                contact.phone = contact_info.get("phone")
        else:
            contact = ContactMap(
                tenant_id=tenant_id,
                messenger=messenger_type,
                chat_id=str(chat_id),
                phone=contact_info.get("phone"),
                username=contact_info.get("username"),
                last_seen_at=now,
            )
            self.db.add(contact)

        await self.db.commit()

    async def _upsert_contact_entity(
        self,
        tenant_id: UUID,
        payload: Dict[str, Any],
        *,
        entity_type: str
    ) -> None:
        fields = payload.get("data", {}).get("FIELDS", {})
        entity_id = fields.get("ID")
        if not entity_id:
            return

        phone = None
        phone_values = fields.get("PHONE") or []
        if isinstance(phone_values, list) and phone_values:
            phone = phone_values[0].get("VALUE")

        if not phone:
            return

        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.phone == phone,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return

        if entity_type == "lead":
            contact.bitrix_lead_id = str(entity_id)
        else:
            contact.bitrix_contact_id = str(entity_id)

        contact.last_seen_at = datetime.utcnow()
        await self.db.commit()

    async def _upsert_deal_link(self, tenant_id: UUID, payload: Dict[str, Any]) -> None:
        fields = payload.get("data", {}).get("FIELDS", {})
        deal_id = fields.get("ID") or fields.get("id") or payload.get("data", {}).get("ID")
        if not deal_id:
            return

        contact_id = (
            fields.get("CONTACT_ID")
            or payload.get("data", {}).get("CONTACT_ID")
        )

        contact_ids = fields.get("CONTACT_IDS") or payload.get("data", {}).get("CONTACT_IDS")
        if not contact_id and isinstance(contact_ids, (list, tuple)) and contact_ids:
            contact_id = contact_ids[0]

        result = await self.db.execute(
            select(DealLink).where(
                DealLink.tenant_id == tenant_id,
                DealLink.bitrix_deal_id == str(deal_id),
            )
        )
        link = result.scalar_one_or_none()

        now = datetime.utcnow()

        if not contact_id:
            if link:
                link.is_active = False
                link.updated_at = now
                await self.db.commit()
            return

        if link:
            link.bitrix_contact_id = str(contact_id)
            link.is_active = True
            link.updated_at = now
        else:
            link = DealLink(
                tenant_id=tenant_id,
                bitrix_contact_id=str(contact_id),
                bitrix_deal_id=str(deal_id),
                is_active=True,
                updated_at=now,
            )
            self.db.add(link)

        await self.db.commit()

    async def _deactivate_deal_link(self, tenant_id: UUID, payload: Dict[str, Any]) -> None:
        deal_id = (
            payload.get("data", {}).get("FIELDS", {}).get("ID")
            or payload.get("data", {}).get("ID")
            or payload.get("data", {}).get("FIELDS", {}).get("id")
        )
        if not deal_id:
            return

        result = await self.db.execute(
            select(DealLink).where(
                DealLink.tenant_id == tenant_id,
                DealLink.bitrix_deal_id == str(deal_id),
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            return

        link.is_active = False
        link.updated_at = datetime.utcnow()
        await self.db.commit()



