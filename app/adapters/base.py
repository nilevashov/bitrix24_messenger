"""Base adapter class for channel integrations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID


class BaseChannelAdapter(ABC):
    """Base class for channel adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channel_id: Optional[UUID] = None
        self.tenant_id: Optional[UUID] = None
    
    @abstractmethod
    async def send_message(
        self, 
        chat_id: str, 
        text: str, 
        media_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send message to channel."""
        pass
    
    @abstractmethod
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get chat information."""
        pass
    
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook."""
        pass
    
    @abstractmethod
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Setup webhook for receiving messages."""
        pass
    
    @abstractmethod
    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        pass
    
    def normalize_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize message from channel format to internal format."""
        return {
            "channel_id": str(self.channel_id),
            "tenant_id": str(self.tenant_id),
            "raw_message": raw_message,
            "normalized_at": self._get_current_timestamp()
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def _extract_contact_info(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact information from raw message."""
        return {
            "chat_id": None,
            "phone": None,
            "username": None,
            "first_name": None,
            "last_name": None
        }
    
    def _extract_message_content(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message content from raw message."""
        return {
            "text": None,
            "media_url": None,
            "media_type": None,
            "media_meta": {}
        }
