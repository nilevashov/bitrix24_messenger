"""Message service for handling message operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.factory import ChannelAdapterFactory
from ..models.channel import Channel, ChannelState, ChannelType
from ..models.dialog import Dialog, DialogStatus
from ..models.message import Message, MessageDirection, MessageStatus


class MessageService:
    """Service for message management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_message(self, tenant_id: UUID, message_id: str) -> Optional[Message]:
        """Get message by ID within tenant."""
        result = await self.db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_message(self, tenant_id: UUID, message_data: Dict[str, Any]) -> Message:
        """Create a new message record with dialog/channel resolution."""
        tenant_uuid = self._coerce_uuid(tenant_id)
        payload = dict(message_data)

        messenger = (payload.get("messenger") or "").lower()
        chat_id = payload.get("chat_id")
        if not chat_id:
            raise ValueError("chat_id is required to create message")

        channel = await self._resolve_channel(
            tenant_uuid,
            messenger,
            payload.get("channel_id")
        )

        dialog = await self._get_or_create_dialog(
            tenant_uuid,
            channel,
            messenger or channel.type.value,
            chat_id,
            payload.get("dialog_id")
        )

        direction = self._normalize_direction(payload.get("direction"))
        status = self._normalize_status(payload.get("status"), direction)

        external_msg_id = payload.get("external_msg_id") or str(uuid4())
        dedup_key = payload.get("dedup_key") or f"{channel.id}:{external_msg_id}"

        message = Message(
            tenant_id=tenant_uuid,
            dialog_id=dialog.id,
            direction=direction,
            messenger=channel.type.value,
            channel_id=channel.id,
            chat_id=chat_id,
            external_msg_id=external_msg_id,
            dedup_key=dedup_key,
            text=payload.get("text"),
            media_url=payload.get("media_url"),
            media_meta=payload.get("media_meta") or {},
            status=status,
            fail_reason=payload.get("fail_reason")
        )

        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        return message
    
    async def update_message_status(
        self, 
        tenant_id: UUID, 
        message_id: str, 
        status: MessageStatus,
        fail_reason: Optional[str] = None
    ) -> Optional[Message]:
        """Update message status."""
        message = await self.get_message(tenant_id, message_id)
        if not message:
            return None
        
        message.status = status
        if fail_reason:
            message.fail_reason = fail_reason
        
        # Update timestamps based on status
        from datetime import datetime
        now = datetime.utcnow()
        
        if status == MessageStatus.SENT:
            message.sent_at = now
        elif status == MessageStatus.DELIVERED:
            message.delivered_at = now
        elif status == MessageStatus.READ:
            message.read_at = now
        
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def send_message(self, message_data: Dict[str, Any]) -> UUID:
        """Send outbound message to channel via appropriate adapter."""
        if "tenant_id" not in message_data:
            raise ValueError("tenant_id is required to send message")

        payload = dict(message_data)
        tenant_uuid = self._coerce_uuid(payload.pop("tenant_id"))
        messenger = (payload.get("messenger") or "").lower()
        chat_id = payload.get("chat_id")
        if not chat_id:
            raise ValueError("chat_id is required to send message")

        channel = await self._resolve_channel(
            tenant_uuid,
            messenger,
            payload.get("channel_id"),
            require_active=True
        )
        messenger_value = messenger or channel.type.value

        dialog = await self._get_or_create_dialog(
            tenant_uuid,
            channel,
            messenger_value,
            chat_id,
            payload.get("dialog_id")
        )

        direction = MessageDirection.OUTBOUND
        status = MessageStatus.QUEUED

        external_msg_id = payload.get("external_msg_id") or str(uuid4())
        dedup_key = payload.get("dedup_key") or f"{channel.id}:{external_msg_id}"

        adapter_kwargs = payload.get("adapter_kwargs") or {}
        if not isinstance(adapter_kwargs, dict):
            raise ValueError("adapter_kwargs must be a dictionary if provided")

        message = Message(
            tenant_id=tenant_uuid,
            dialog_id=dialog.id,
            direction=direction,
            messenger=channel.type.value,
            channel_id=channel.id,
            chat_id=chat_id,
            external_msg_id=external_msg_id,
            dedup_key=dedup_key,
            text=payload.get("text"),
            media_url=payload.get("media_url"),
            media_meta=payload.get("media_meta") or {},
            status=status
        )

        self.db.add(message)
        await self.db.flush()

        adapter = ChannelAdapterFactory.create_adapter(channel.type.value, channel.config or {})
        adapter.channel_id = channel.id
        adapter.tenant_id = tenant_uuid

        send_result: Dict[str, Any]
        try:
            send_result = await adapter.send_message(
                chat_id=chat_id,
                text=payload.get("text") or "",
                media_url=payload.get("media_url"),
                **adapter_kwargs
            )
        except Exception as exc:  # pragma: no cover - adapter errors
            send_result = {"success": False, "error": str(exc)}

        if send_result.get("success"):
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            provider_msg_id = send_result.get("message_id")
            if provider_msg_id:
                message.external_msg_id = str(provider_msg_id)
                message.dedup_key = f"{channel.id}:{message.external_msg_id}"
        else:
            message.status = MessageStatus.FAILED
            message.fail_reason = send_result.get("error", "Unknown error")

        await self.db.commit()
        await self.db.refresh(message)

        if message.status == MessageStatus.FAILED:
            raise ValueError(f"Failed to send message: {message.fail_reason}")

        return message.id
    
    async def get_dialog_messages(
        self, 
        tenant_id: UUID, 
        dialog_id: str, 
        limit: int = 50
    ) -> list[Message]:
        """Get messages for a dialog."""
        result = await self.db.execute(
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.dialog_id == dialog_id
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    def _coerce_uuid(value: Any) -> UUID:
        """Ensure value is UUID instance."""
        if isinstance(value, UUID):
            return value
        return UUID(str(value))

    @staticmethod
    def _normalize_direction(direction: Any) -> MessageDirection:
        """Convert direction value to MessageDirection enum."""
        if isinstance(direction, MessageDirection):
            return direction
        if direction is None:
            return MessageDirection.INBOUND

        direction_str = str(direction).lower()
        if direction_str in {"in", "inbound"}:
            return MessageDirection.INBOUND
        if direction_str in {"out", "outbound"}:
            return MessageDirection.OUTBOUND
        raise ValueError(f"Unsupported message direction: {direction}")

    @staticmethod
    def _normalize_status(status: Any, direction: MessageDirection) -> MessageStatus:
        """Convert status value to MessageStatus enum."""
        if isinstance(status, MessageStatus):
            return status
        if status is None:
            return MessageStatus.RECEIVED if direction == MessageDirection.INBOUND else MessageStatus.QUEUED

        status_str = str(status).lower()
        for enum_member in MessageStatus:
            if enum_member.value == status_str:
                return enum_member
        raise ValueError(f"Unsupported message status: {status}")

    async def _resolve_channel(
        self,
        tenant_id: UUID,
        messenger: str,
        channel_id: Any = None,
        *,
        require_active: bool = False
    ) -> Channel:
        """Resolve channel for message based on provided data."""
        query = select(Channel).where(Channel.tenant_id == tenant_id)

        if channel_id:
            channel_uuid = self._coerce_uuid(channel_id)
            query = query.where(Channel.id == channel_uuid)
        else:
            if not messenger:
                raise ValueError("messenger is required when channel_id is not provided")
            try:
                channel_type = ChannelType(messenger.lower())
            except ValueError as exc:
                raise ValueError(f"Unsupported messenger type: {messenger}") from exc
            query = query.where(Channel.type == channel_type)

        if require_active:
            query = query.where(Channel.state == ChannelState.ACTIVE)

        result = await self.db.execute(query.limit(1))
        channel = result.scalar_one_or_none()
        if not channel:
            raise ValueError("Channel not found for message")

        return channel

    async def _get_or_create_dialog(
        self,
        tenant_id: UUID,
        channel: Channel,
        messenger: str,
        chat_id: str,
        dialog_id: Any = None
    ) -> Dialog:
        """Fetch existing dialog or create a new one for chat."""
        if dialog_id:
            dialog_uuid = self._coerce_uuid(dialog_id)
            result = await self.db.execute(
                select(Dialog).where(
                    Dialog.id == dialog_uuid,
                    Dialog.tenant_id == tenant_id
                )
            )
            dialog = result.scalar_one_or_none()
            if dialog:
                return dialog

        result = await self.db.execute(
            select(Dialog).where(
                Dialog.tenant_id == tenant_id,
                Dialog.channel_id == channel.id,
                Dialog.chat_id == chat_id,
                Dialog.status == DialogStatus.OPEN
            )
        )
        dialog = result.scalar_one_or_none()

        if dialog:
            return dialog

        dialog = Dialog(
            tenant_id=tenant_id,
            channel_id=channel.id,
            messenger=messenger or channel.type.value,
            chat_id=chat_id,
            status=DialogStatus.OPEN,
            opened_at=datetime.utcnow()
        )

        self.db.add(dialog)
        await self.db.flush()

        return dialog

