"""Admin service for dashboard and management operations."""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from ..models.channel import Channel, ChannelState
from ..models.message import Message, MessageStatus
from ..models.dialog import Dialog, DialogStatus
from ..models.tenant import Tenant

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin operations and dashboard data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get dashboard statistics."""
        try:
            # Active channels count
            active_channels_result = await self.db.execute(
                select(func.count(Channel.id)).where(
                    Channel.tenant_id == tenant_id,
                    Channel.state == ChannelState.ACTIVE
                )
            )
            active_channels = active_channels_result.scalar() or 0
            
            # Messages today count
            today = datetime.utcnow().date()
            messages_today_result = await self.db.execute(
                select(func.count(Message.id)).where(
                    Message.tenant_id == tenant_id,
                    func.date(Message.created_at) == today
                )
            )
            messages_today = messages_today_result.scalar() or 0
            
            # Open dialogs count
            open_dialogs_result = await self.db.execute(
                select(func.count(Dialog.id)).where(
                    Dialog.tenant_id == tenant_id,
                    Dialog.status == DialogStatus.OPEN
                )
            )
            open_dialogs = open_dialogs_result.scalar() or 0
            
            # Failed messages count (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            failed_messages_result = await self.db.execute(
                select(func.count(Message.id)).where(
                    Message.tenant_id == tenant_id,
                    Message.status == MessageStatus.FAILED,
                    Message.created_at >= yesterday
                )
            )
            failed_messages = failed_messages_result.scalar() or 0
            
            return {
                "activeChannels": active_channels,
                "messagesToday": messages_today,
                "openDialogs": open_dialogs,
                "failedMessages": failed_messages
            }
        except Exception as e:
            logger.error(f"Error in get_dashboard_stats: {str(e)}")
            # Return default values if there's an error
            return {
                "activeChannels": 0,
                "messagesToday": 0,
                "openDialogs": 0,
                "failedMessages": 0
            }
    
    async def get_channels(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """Get channels for tenant."""
        result = await self.db.execute(
            select(Channel).where(Channel.tenant_id == tenant_id)
        )
        channels = result.scalars().all()
        
        channel_list = []
        for channel in channels:
            logger.info(f"Channel {channel.id}: config = {channel.config}")
            channel_dict = {
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
            channel_list.append(channel_dict)
        
        return channel_list
    
    async def create_channel(
        self, 
        tenant_id: UUID, 
        channel_data: Dict[str, Any]
    ) -> bool:
        """Create a new channel."""
        from ..models.channel import ChannelType, ChannelState
        
        # Debug logging
        print(f"DEBUG: Creating channel with data: {channel_data}")
        logger.info(f"Creating channel with data: {channel_data}")
        
        # Map frontend channel types to model types
        type_mapping = {
            "telegram": ChannelType.TELEGRAM,
            "whatsapp": ChannelType.WHATSAPP
        }
        
        channel_type = type_mapping.get(channel_data.get("type", "").lower())
        if not channel_type:
            raise ValueError(f"Unsupported channel type: {channel_data.get('type')}")
        
        # Prepare config based on channel type
        config = {}
        if channel_type == ChannelType.TELEGRAM and "bot_token" in channel_data:
            config["bot_token"] = channel_data["bot_token"]
            print(f"DEBUG: Bot token found: {channel_data['bot_token']}")
            logger.info(f"Bot token found: {channel_data['bot_token']}")
        else:
            print(f"DEBUG: No bot token found. Channel type: {channel_type}, Keys: {list(channel_data.keys())}")
            logger.info(f"No bot token found. Channel type: {channel_type}, Keys: {list(channel_data.keys())}")
        
        print(f"DEBUG: Final config: {config}")
        logger.info(f"Final config: {config}")
        
        # Create channel
        channel = Channel(
            tenant_id=tenant_id,
            type=channel_type,
            name=channel_data.get("name", ""),
            state=ChannelState.INACTIVE,  # Start as inactive
            config=config,
            external_channel_id=None
        )
        
        print(f"DEBUG: Channel object before save: config={channel.config}")
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        print(f"DEBUG: Channel created with ID: {channel.id}, config: {channel.config}")
        logger.info(f"Channel created with ID: {channel.id}, config: {channel.config}")
        return True
    
    async def toggle_channel(self, tenant_id: UUID, channel_id: str) -> bool:
        """Toggle channel status."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == channel_id,
                Channel.tenant_id == tenant_id
            )
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            return False
        
        # Toggle state
        if channel.state == ChannelState.ACTIVE:
            channel.state = ChannelState.INACTIVE
        else:
            channel.state = ChannelState.ACTIVE
        
        await self.db.commit()
        return True
    
    async def update_channel(
        self, 
        tenant_id: UUID, 
        channel_id: str, 
        channel_data: Dict[str, Any]
    ) -> bool:
        """Update channel."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == channel_id,
                Channel.tenant_id == tenant_id
            )
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            return False
        
        # Update channel fields
        if "name" in channel_data:
            channel.name = channel_data["name"]
        
        if "config" in channel_data:
            # Merge with existing config
            if not channel.config:
                channel.config = {}
            channel.config.update(channel_data["config"])
        
        await self.db.commit()
        return True
    
    async def delete_channel(self, tenant_id: UUID, channel_id: str) -> bool:
        """Delete channel."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == channel_id,
                Channel.tenant_id == tenant_id
            )
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            return False
        
        await self.db.delete(channel)
        await self.db.commit()
        return True
    
    async def get_recent_messages(
        self, 
        tenant_id: UUID, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages."""
        result = await self.db.execute(
            select(Message)
            .where(Message.tenant_id == tenant_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()
        
        return [
            {
                "id": str(message.id),
                "messenger": message.messenger,
                "direction": message.direction.value,
                "text": message.text or "",
                "status": message.status.value,
                "created_at": message.created_at.isoformat()
            }
            for message in messages
        ]
    
    async def get_bitrix_config(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get Bitrix24 configuration."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return {
                "domain": "",
                "app_id": "",
                "openlines_enabled": True,
                "timeline_enabled": True
            }
        
        return {
            "domain": tenant.bitrix_portal or "",
            "app_id": tenant.bitrix_app_id or "",
            "openlines_enabled": tenant.openlines_enabled,
            "timeline_enabled": tenant.timeline_enabled
        }
    
    async def save_bitrix_config(
        self, 
        tenant_id: UUID, 
        config_data: Dict[str, Any]
    ) -> bool:
        """Save Bitrix24 configuration."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return False
        
        # Update tenant configuration
        if "domain" in config_data:
            tenant.bitrix_portal = config_data["domain"]
        if "app_id" in config_data:
            tenant.bitrix_app_id = config_data["app_id"]
        if "openlines_enabled" in config_data:
            tenant.openlines_enabled = config_data["openlines_enabled"]
        if "timeline_enabled" in config_data:
            tenant.timeline_enabled = config_data["timeline_enabled"]
        
        await self.db.commit()
        return True
    
    async def save_settings(
        self, 
        tenant_id: UUID, 
        settings_data: Dict[str, Any]
    ) -> bool:
        """Save system settings."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return False
        
        # Update tenant settings
        if "settings" not in tenant.settings:
            tenant.settings = {}
        
        tenant.settings.update(settings_data)
        
        await self.db.commit()
        return True
    
    async def get_system_health(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get system health status."""
        # Check database connectivity
        db_healthy = True
        try:
            await self.db.execute(select(1))
        except Exception:
            db_healthy = False
        
        # Check message queue health (placeholder)
        queue_healthy = True
        
        # Check external services health (placeholder)
        bitrix_healthy = True
        
        return {
            "database": db_healthy,
            "message_queue": queue_healthy,
            "bitrix24": bitrix_healthy,
            "overall": db_healthy and queue_healthy and bitrix_healthy
        }
