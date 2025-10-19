"""Channel adapter factory."""

from typing import Dict, Any, Type
from .base import BaseChannelAdapter
from .telegram import TelegramAdapter
from .whatsapp import WhatsAppAdapter


class ChannelAdapterFactory:
    """Factory for creating channel adapters."""
    
    _adapters: Dict[str, Type[BaseChannelAdapter]] = {
        "telegram": TelegramAdapter,
        "whatsapp": WhatsAppAdapter,
    }
    
    @classmethod
    def create_adapter(cls, channel_type: str, config: Dict[str, Any]) -> BaseChannelAdapter:
        """Create channel adapter instance."""
        if channel_type not in cls._adapters:
            raise ValueError(f"Unsupported channel type: {channel_type}")
        
        adapter_class = cls._adapters[channel_type]
        return adapter_class(config)
    
    @classmethod
    def register_adapter(cls, channel_type: str, adapter_class: Type[BaseChannelAdapter]) -> None:
        """Register new adapter type."""
        cls._adapters[channel_type] = adapter_class
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported channel types."""
        return list(cls._adapters.keys())
