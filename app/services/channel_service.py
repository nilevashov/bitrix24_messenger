"""Channel service for managing messenger channels."""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.channel import Channel, ChannelType, ChannelState
from ..api.schemas import PaginatedResponse


class ChannelService:
    """Service for channel management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_channel(self, tenant_id: UUID, channel_id: str) -> Optional[Channel]:
        """Get channel by ID within tenant."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == channel_id,
                Channel.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_channel_by_type(self, tenant_id: UUID, channel_type: ChannelType) -> Optional[Channel]:
        """Get active channel by type within tenant."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.tenant_id == tenant_id,
                Channel.type == channel_type,
                Channel.state == ChannelState.ACTIVE
            )
        )
        return result.scalar_one_or_none()
    
    async def create_channel(self, tenant_id: UUID, channel_data: Dict[str, Any]) -> Channel:
        """Create a new channel."""
        channel = Channel(
            tenant_id=tenant_id,
            **channel_data
        )
        
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        
        return channel
    
    async def update_channel(
        self, 
        tenant_id: UUID, 
        channel_id: str, 
        channel_data: Dict[str, Any]
    ) -> Optional[Channel]:
        """Update channel."""
        channel = await self.get_channel(tenant_id, channel_id)
        if not channel:
            return None
        
        for key, value in channel_data.items():
            if hasattr(channel, key):
                setattr(channel, key, value)
        
        await self.db.commit()
        await self.db.refresh(channel)
        
        return channel
    
    async def list_channels(
        self, 
        tenant_id: UUID, 
        page: int = 1, 
        size: int = 20
    ) -> PaginatedResponse:
        """List channels with pagination."""
        offset = (page - 1) * size
        
        # Get total count
        count_result = await self.db.execute(
            select(Channel).where(Channel.tenant_id == tenant_id)
        )
        total = len(count_result.scalars().all())
        
        # Get paginated results
        result = await self.db.execute(
            select(Channel)
            .where(Channel.tenant_id == tenant_id)
            .offset(offset)
            .limit(size)
        )
        channels = result.scalars().all()
        
        # Convert channels to dictionaries for serialization
        channel_dicts = [
            {
                "id": str(channel.id),
                "tenant_id": str(channel.tenant_id),
                "type": channel.type.value if channel.type else None,
                "name": channel.name,
                "config": channel.config,
                "external_channel_id": channel.external_channel_id,
                "state": channel.state.value if channel.state else None,
                "created_at": channel.created_at.isoformat(),
                "updated_at": channel.updated_at.isoformat()
            }
            for channel in channels
        ]
        
        return PaginatedResponse(
            items=channel_dicts,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    async def activate_channel(self, tenant_id: UUID, channel_id: str) -> bool:
        """Activate channel."""
        channel = await self.get_channel(tenant_id, channel_id)
        if not channel:
            return False
        
        channel.state = ChannelState.ACTIVE
        await self.db.commit()
        
        return True
    
    async def deactivate_channel(self, tenant_id: UUID, channel_id: str) -> bool:
        """Deactivate channel."""
        channel = await self.get_channel(tenant_id, channel_id)
        if not channel:
            return False
        
        channel.state = ChannelState.INACTIVE
        await self.db.commit()
        
        return True
    
    async def delete_channel(self, tenant_id: UUID, channel_id: str) -> bool:
        """Delete channel."""
        channel = await self.get_channel(tenant_id, channel_id)
        if not channel:
            return False
        
        await self.db.delete(channel)
        await self.db.commit()
        
        return True

