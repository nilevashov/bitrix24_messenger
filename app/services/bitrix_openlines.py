"""Bitrix24 OpenLines integration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.channel import Channel, ChannelType
from ..models.contact_map import ContactMap, MessengerType
from ..models.dialog import Dialog, DialogStatus
from ..models.deal_link import DealLink
from ..models.message import Message
from ..models.tenant import Tenant
from ..services.message_service import MessageService
from .bitrix_service import BitrixService


class BitrixOpenLinesService:
    """Service for Bitrix24 OpenLines integration."""

    CONNECTOR_ALIASES = {
        ChannelType.TELEGRAM: "telegrambot",
        ChannelType.WHATSAPP: "whatsapp",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def send_message_to_openlines(
        self,
        tenant_id: UUID,
        channel: Channel,
        message: Message,
        contact_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send inbound messenger message to Bitrix24 OpenLines."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant or not tenant.bitrix_oauth_access:
            raise ValueError("Bitrix24 not configured for tenant")

        dialog = await self._get_dialog(tenant_id, message.dialog_id)
        if not dialog:
            raise ValueError("Dialog not found for message")

        connector_code = self._determine_connector_code(channel)
        line_id = self._determine_line_id(channel, tenant)
        if not line_id:
            raise ValueError("OpenLines line identifier is not configured for channel")

        payload = self._build_openlines_payload(
            connector_code,
            line_id,
            message,
            contact_info,
        )

        data = await self._call_bitrix_method(tenant, "imconnector.receiveMessage", payload)
        result = data.get("result") or {}

        session_id = result.get("session_id") or result.get("SESSION_ID")
        if session_id:
            if not dialog.bitrix_dialog_id:
                dialog.bitrix_dialog_id = str(session_id)
            dialog.status = DialogStatus.OPEN
            await self.db.commit()

        return {
            "success": True,
            "session_id": session_id,
            "dialog_id": str(dialog.id),
        }

    async def handle_operator_message(
        self,
        tenant_id: UUID,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle operator message from Bitrix24 OpenLines."""
        fields = event_data.get("data", {}).get("FIELDS", {})
        session_id = fields.get("SESSION_ID")
        if not session_id:
            return {"error": "Missing session identifier"}

        dialog = await self._get_dialog_by_session_id(tenant_id, str(session_id))
        if not dialog:
            return {"error": "Dialog not found"}

        message_service = MessageService(self.db)
        text = fields.get("MESSAGE") or ""
        files = fields.get("FILES") or []

        media_url: Optional[str] = None
        media_meta: Dict[str, Any] = {}
        if files:
            file_entry = files[0] or {}
            media_url = file_entry.get("FILE_LINK") or file_entry.get("URL")
            media_meta = {
                "file_id": file_entry.get("FILE_ID"),
                "file_name": file_entry.get("FILE_NAME"),
                "mime_type": file_entry.get("CONTENT_TYPE") or file_entry.get("FILE_TYPE"),
                "file_size": file_entry.get("FILE_SIZE"),
            }

        outbound_payload: Dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "dialog_id": str(dialog.id),
            "channel_id": str(dialog.channel_id),
            "chat_id": dialog.chat_id,
            "text": text,
        }
        if media_url:
            outbound_payload["media_url"] = media_url
            outbound_payload["media_meta"] = {k: v for k, v in media_meta.items() if v is not None}

        external_id = fields.get("IM_MESSAGE_ID") or fields.get("ID")
        if external_id:
            outbound_payload["external_msg_id"] = str(external_id)

        message_id = await message_service.send_message(outbound_payload)
        await self._mark_dialog_active(dialog, operator_id=fields.get("USER_ID"))

        return {
            "success": True,
            "message_id": str(message_id),
            "dialog_id": str(dialog.id),
        }

    async def handle_session_start(
        self,
        tenant_id: UUID,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle OpenLines session start."""
        fields = event_data.get("data", {}).get("FIELDS", {})
        session_id = fields.get("SESSION_ID")
        if not session_id:
            return {"error": "Missing session identifier"}

        dialog = await self._get_dialog_by_session_id(tenant_id, str(session_id))
        if dialog:
            await self._mark_dialog_active(dialog, operator_id=fields.get("USER_ID"))
            return {"success": True, "session_id": str(session_id), "dialog_id": str(dialog.id)}

        channel = await self._find_channel_for_session(
            tenant_id,
            fields.get("CONNECTOR_ID"),
            fields.get("CONFIG_ID"),
        )
        if not channel:
            return {"error": "Unable to resolve channel for session"}

        chat_id = await self._resolve_chat_id_for_session(tenant_id, fields, channel)
        if not chat_id:
            return {"error": "Unable to determine chat_id for session"}

        dialog = Dialog(
            tenant_id=tenant_id,
            channel_id=channel.id,
            messenger=channel.type.value,
            chat_id=chat_id,
            bitrix_dialog_id=str(session_id),
            status=DialogStatus.OPEN,
            opened_at=datetime.utcnow(),
            operator_user_id=str(fields.get("USER_ID")) if fields.get("USER_ID") else None,
        )
        self.db.add(dialog)
        await self.db.commit()
        await self.db.refresh(dialog)

        return {"success": True, "session_id": str(session_id), "dialog_id": str(dialog.id)}

    async def handle_session_finish(
        self,
        tenant_id: UUID,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle OpenLines session finish."""
        fields = event_data.get("data", {}).get("FIELDS", {})
        session_id = fields.get("SESSION_ID")
        if not session_id:
            return {"error": "Missing session identifier"}

        dialog = await self._get_dialog_by_session_id(tenant_id, str(session_id))
        if not dialog:
            return {"error": "Dialog not found"}

        dialog.status = DialogStatus.CLOSED
        dialog.closed_at = datetime.utcnow()
        await self.db.commit()

        return {"success": True, "session_id": str(session_id), "dialog_id": str(dialog.id)}

    async def _call_bitrix_method(
        self,
        tenant: Tenant,
        method: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = f"https://{tenant.bitrix_portal}/rest/{method}"
        params = {"auth": tenant.bitrix_oauth_access}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, json=payload)
            data = response.json()

            if response.status_code == 401 or data.get("error") == "INVALID_TOKEN":
                bitrix_service = BitrixService(self.db)
                tokens = await bitrix_service.refresh_token(tenant.id)
                await bitrix_service.client.aclose()
                params["auth"] = tokens["access_token"]
                response = await client.post(url, params=params, json=payload)
                data = response.json()

            response.raise_for_status()

        if data.get("error"):
            message = data.get("error_description") or data.get("error")
            raise ValueError(f"Bitrix API error: {message}")

        return data

    async def _get_dialog(self, tenant_id: UUID, dialog_id: UUID) -> Optional[Dialog]:
        result = await self.db.execute(
            select(Dialog).where(
                Dialog.tenant_id == tenant_id,
                Dialog.id == dialog_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_dialog_by_session_id(
        self,
        tenant_id: UUID,
        session_id: str
    ) -> Optional[Dialog]:
        result = await self.db.execute(
            select(Dialog).where(
                Dialog.tenant_id == tenant_id,
                Dialog.bitrix_dialog_id == str(session_id),
            )
        )
        return result.scalar_one_or_none()

    async def _mark_dialog_active(
        self,
        dialog: Dialog,
        *,
        operator_id: Optional[Any] = None
    ) -> None:
        dialog.status = DialogStatus.OPEN
        dialog.operator_user_id = str(operator_id) if operator_id else dialog.operator_user_id
        await self.db.commit()

    async def _find_channel_for_session(
        self,
        tenant_id: UUID,
        connector_id: Optional[str],
        config_id: Optional[Any]
    ) -> Optional[Channel]:
        query = select(Channel).where(Channel.tenant_id == tenant_id)

        if connector_id:
            query = query.where(Channel.config["openlines_connector"].astext == connector_id)
        if config_id:
            query = query.where(Channel.config["openlines_line_id"].astext == str(config_id))

        result = await self.db.execute(query.limit(1))
        channel = result.scalar_one_or_none()
        if channel:
            return channel

        # Fallback: derive from connector_id mapping
        try:
            channel_type = ChannelType(connector_id or "")
        except ValueError:
            channel_type = self._connector_to_channel_type(connector_id)

        if channel_type:
            result = await self.db.execute(
                select(Channel).where(
                    Channel.tenant_id == tenant_id,
                    Channel.type == channel_type,
                )
            )
            return result.scalar_one_or_none()

        return None

    def _connector_to_channel_type(self, connector_id: Optional[str]) -> Optional[ChannelType]:
        if not connector_id:
            return None
        connector_id = connector_id.lower()
        for channel_type, alias in self.CONNECTOR_ALIASES.items():
            if alias == connector_id:
                return channel_type
        try:
            return ChannelType(connector_id)
        except ValueError:
            return None

    def _determine_connector_code(self, channel: Channel) -> str:
        if channel.config and channel.config.get("openlines_connector"):
            return channel.config["openlines_connector"]
        return self.CONNECTOR_ALIASES.get(channel.type, channel.type.value)

    def _determine_line_id(self, channel: Channel, tenant: Tenant) -> Optional[str]:
        if channel.config:
            line_id = channel.config.get("openlines_line_id")
            if line_id:
                return str(line_id)
        settings = tenant.settings or {}
        openlines_settings = settings.get("openlines") or {}
        line_id = openlines_settings.get("default_line_id")
        return str(line_id) if line_id else None

    async def _resolve_chat_id_for_session(
        self,
        tenant_id: UUID,
        fields: Dict[str, Any],
        channel: Channel,
    ) -> Optional[str]:
        chat_id = self._extract_chat_id(fields)
        if chat_id:
            return chat_id

        messenger_type = self._channel_to_messenger(channel)
        if not messenger_type:
            return None

        # Try to resolve by CRM-bound contact identifiers
        contact_ids = await self._collect_related_contacts(tenant_id, fields)
        for contact_id in contact_ids:
            chat_id = await self._lookup_chat_id_by_contact(tenant_id, messenger_type, contact_id)
            if chat_id:
                return chat_id

        lead_ids = self._collect_related_leads(fields)
        for lead_id in lead_ids:
            chat_id = await self._lookup_chat_id_by_lead(tenant_id, messenger_type, lead_id)
            if chat_id:
                return chat_id

        phone = fields.get("USER_PHONE") or fields.get("PHONE")
        if phone:
            chat_id = await self._lookup_chat_id_by_phone(tenant_id, messenger_type, phone)
            if chat_id:
                return chat_id

        return None

    def _extract_chat_id(self, fields: Dict[str, Any]) -> Optional[str]:
        user_code = fields.get("USER_CODE") or ""
        if "|" in user_code:
            return user_code.split("|")[-1]
        chat_id = fields.get("CHAT_ID") or fields.get("USER_ID")
        return str(chat_id) if chat_id else None

    def _channel_to_messenger(self, channel: Channel) -> Optional[MessengerType]:
        try:
            return MessengerType(channel.type.value)
        except ValueError:
            return None

    async def _collect_related_contacts(
        self,
        tenant_id: UUID,
        fields: Dict[str, Any],
    ) -> list[str]:
        contact_ids: set[str] = set()
        for entity_type, entity_id in self._iter_crm_entities(fields):
            if entity_type == "CONTACT" and entity_id:
                contact_ids.add(entity_id)
            elif entity_type == "DEAL" and entity_id:
                contact_id = await self._resolve_contact_from_deal(tenant_id, entity_id)
                if contact_id:
                    contact_ids.add(contact_id)
        direct_contact = fields.get("CRM_ENTITY_CONTACT") or fields.get("CONTACT_ID")
        if direct_contact:
            contact_ids.add(str(direct_contact))
        return list(contact_ids)

    def _collect_related_leads(self, fields: Dict[str, Any]) -> list[str]:
        lead_ids: set[str] = set()
        for entity_type, entity_id in self._iter_crm_entities(fields):
            if entity_type == "LEAD" and entity_id:
                lead_ids.add(entity_id)
        direct_lead = fields.get("CRM_ENTITY_LEAD") or fields.get("LEAD_ID")
        if direct_lead:
            lead_ids.add(str(direct_lead))
        return list(lead_ids)

    def _iter_crm_entities(
        self,
        fields: Dict[str, Any],
    ) -> list[tuple[str, str]]:
        entities: list[tuple[str, str]] = []
        pairs = [
            ("CRM_ENTITY_TYPE", "CRM_ENTITY_ID"),
            ("CRM_ENTITY_PRIMARY_TYPE", "CRM_ENTITY_PRIMARY"),
            ("CRM_ENTITY_SECONDARY_TYPE", "CRM_ENTITY_SECONDARY"),
        ]
        for type_key, id_key in pairs:
            entity_type = fields.get(type_key)
            entity_id = fields.get(id_key)
            if isinstance(entity_id, (list, tuple)):
                for value in entity_id:
                    entities.append((str(entity_type or "").upper(), str(value)))
            elif entity_type and entity_id:
                entities.append((str(entity_type).upper(), str(entity_id)))

        additional = fields.get("CRM_ENTITIES")
        if isinstance(additional, list):
            for entity in additional:
                entity_type = entity.get("ENTITY_TYPE") or entity.get("TYPE")
                entity_id = entity.get("ENTITY_ID") or entity.get("ID")
                if entity_type and entity_id:
                    entities.append((str(entity_type).upper(), str(entity_id)))

        return entities

    async def _lookup_chat_id_by_contact(
        self,
        tenant_id: UUID,
        messenger_type: MessengerType,
        contact_id: str,
    ) -> Optional[str]:
        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.messenger == messenger_type,
                ContactMap.bitrix_contact_id == str(contact_id),
            )
        )
        mapping = result.scalar_one_or_none()
        return mapping.chat_id if mapping else None

    async def _lookup_chat_id_by_lead(
        self,
        tenant_id: UUID,
        messenger_type: MessengerType,
        lead_id: str,
    ) -> Optional[str]:
        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.messenger == messenger_type,
                ContactMap.bitrix_lead_id == str(lead_id),
            )
        )
        mapping = result.scalar_one_or_none()
        return mapping.chat_id if mapping else None

    async def _lookup_chat_id_by_phone(
        self,
        tenant_id: UUID,
        messenger_type: MessengerType,
        phone: str,
    ) -> Optional[str]:
        result = await self.db.execute(
            select(ContactMap).where(
                ContactMap.tenant_id == tenant_id,
                ContactMap.messenger == messenger_type,
                ContactMap.phone == phone,
            )
        )
        mapping = result.scalar_one_or_none()
        return mapping.chat_id if mapping else None

    async def _resolve_contact_from_deal(
        self,
        tenant_id: UUID,
        deal_id: str,
    ) -> Optional[str]:
        result = await self.db.execute(
            select(DealLink).where(
                DealLink.tenant_id == tenant_id,
                DealLink.bitrix_deal_id == str(deal_id),
                DealLink.is_active == True,
            )
        )
        link = result.scalar_one_or_none()
        if link:
            return link.bitrix_contact_id

        return None

    async def _upsert_deal_link(
        self,
        tenant_id: UUID,
        contact_id: str,
        deal_id: str,
    ) -> None:
        result = await self.db.execute(
            select(DealLink).where(
                DealLink.tenant_id == tenant_id,
                DealLink.bitrix_deal_id == str(deal_id),
            )
        )
        link = result.scalar_one_or_none()
        now = datetime.utcnow()

        if link:
            link.bitrix_contact_id = contact_id
            link.is_active = True
            link.updated_at = now
        else:
            link = DealLink(
                tenant_id=tenant_id,
                bitrix_contact_id=contact_id,
                bitrix_deal_id=deal_id,
                is_active=True,
                updated_at=now,
            )
            self.db.add(link)

        await self.db.commit()

    def _build_openlines_payload(
        self,
        connector_code: str,
        line_id: str,
        message: Message,
        contact_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        files: list[Dict[str, Any]] = []
        if message.media_url:
            file_descriptor = {
                "url": message.media_url,
                "name": message.media_meta.get("file_name") or "file",
            }
            if message.media_meta.get("mime_type"):
                file_descriptor["type"] = message.media_meta["mime_type"]
            files.append(file_descriptor)

        message_block: Dict[str, Any] = {
            "USER_ID": str(contact_info.get("user_id") or contact_info.get("chat_id") or message.chat_id),
            "CHAT_ID": message.chat_id,
            "ID": message.external_msg_id,
            "MESSAGE": message.text or "",
            "DATE": message.created_at.isoformat(),
        }
        if files:
            message_block["FILES"] = files
        if contact_info:
            message_block["EXTRA"] = {"CONTACT": contact_info}

        return {
            "CONNECTOR": connector_code,
            "LINE": line_id,
            "MESSAGES": [message_block],
        }
