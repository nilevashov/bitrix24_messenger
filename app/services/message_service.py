"""Message service for handling message operations."""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
        """Create a new message."""
        message = Message(
            tenant_id=tenant_id,
            **message_data
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
        """Send message to channel."""
        # TODO: Implement message sending logic
        # This would involve:
        # 1. Creating message record
        # 2. Routing to appropriate channel adapter
        # 3. Updating status based on delivery result
        
        # For now, just create a placeholder message
        message = Message(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Extract from context
            **message_data
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
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

