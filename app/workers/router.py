"""FastStream router for message processing."""

import asyncio
import json
import logging
from typing import Dict, Any
from faststream import FastStream, Context
from faststream.rabbit import RabbitBroker, RabbitMessage
from faststream.rabbit.annotations import RabbitMessage as RabbitMessageAnnotation

from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..services.message_service import MessageService
from ..services.bitrix_service import BitrixService
from ..services.webhook_service import WebhookService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create RabbitMQ broker
broker = RabbitBroker(settings.rabbitmq.url)
app = FastStream(broker)


class MessageRouter:
    """Message router for processing and routing messages."""
    
    def __init__(self):
        self.message_service = None
        self.bitrix_service = None
        self.webhook_service = None
    
    async def initialize(self, db: AsyncSessionLocal):
        """Initialize services with database session."""
        self.message_service = MessageService(db)
        self.bitrix_service = BitrixService(db)
        self.webhook_service = WebhookService(db)
    
    async def process_inbound_message(self, message_data: Dict[str, Any]) -> None:
        """Process inbound message from channels."""
        try:
            logger.info(f"Processing inbound message: {message_data}")
            
            # Normalize message data
            normalized_message = await self._normalize_message(message_data)
            
            # Resolve contact and determine routing strategy
            routing_strategy = await self._determine_routing_strategy(normalized_message)
            
            # Route to Bitrix24
            if routing_strategy == "openlines":
                await self._route_to_openlines(normalized_message)
            elif routing_strategy == "timeline":
                await self._route_to_timeline(normalized_message)
            
            logger.info(f"Successfully processed inbound message: {normalized_message.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to process inbound message: {str(e)}", exc_info=True)
            raise
    
    async def process_outbound_message(self, message_data: Dict[str, Any]) -> None:
        """Process outbound message from Bitrix24."""
        try:
            logger.info(f"Processing outbound message: {message_data}")
            
            # Send to appropriate channel
            await self._send_to_channel(message_data)
            
            logger.info(f"Successfully processed outbound message: {message_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to process outbound message: {str(e)}", exc_info=True)
            raise
    
    async def process_status_update(self, status_data: Dict[str, Any]) -> None:
        """Process message status update."""
        try:
            logger.info(f"Processing status update: {status_data}")
            
            # Update message status in database
            await self._update_message_status(status_data)
            
            logger.info(f"Successfully processed status update: {status_data.get('message_id')}")
            
        except Exception as e:
            logger.error(f"Failed to process status update: {str(e)}", exc_info=True)
            raise
    
    async def process_media(self, media_data: Dict[str, Any]) -> None:
        """Process media file."""
        try:
            logger.info(f"Processing media: {media_data}")
            
            # Download and upload media
            await self._process_media_file(media_data)
            
            logger.info(f"Successfully processed media: {media_data.get('media_id')}")
            
        except Exception as e:
            logger.error(f"Failed to process media: {str(e)}", exc_info=True)
            raise
    
    async def _normalize_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize message data from different channels."""
        # TODO: Implement message normalization logic
        # This would extract common fields like:
        # - text content
        # - sender information
        # - timestamp
        # - media attachments
        # - channel-specific metadata
        
        return message_data
    
    async def _determine_routing_strategy(self, message_data: Dict[str, Any]) -> str:
        """Determine routing strategy (OpenLines vs Timeline)."""
        # TODO: Implement routing logic based on:
        # - Tenant configuration
        # - Contact status
        # - Active deals
        # - Routing rules
        
        # For now, default to OpenLines
        return "openlines"
    
    async def _route_to_openlines(self, message_data: Dict[str, Any]) -> None:
        """Route message to Bitrix24 OpenLines."""
        # TODO: Implement OpenLines routing
        # This would involve:
        # 1. Creating/updating OpenLines session
        # 2. Sending message via imconnector.receiveMessage
        # 3. Updating dialog status
        
        pass
    
    async def _route_to_timeline(self, message_data: Dict[str, Any]) -> None:
        """Route message to Bitrix24 CRM timeline."""
        # TODO: Implement timeline routing
        # This would involve:
        # 1. Finding or creating contact/lead
        # 2. Adding comment to timeline
        # 3. Uploading media to Bitrix Disk if needed
        
        pass
    
    async def _send_to_channel(self, message_data: Dict[str, Any]) -> None:
        """Send message to channel."""
        # TODO: Implement channel sending
        # This would involve:
        # 1. Determining target channel
        # 2. Using appropriate channel adapter
        # 3. Updating message status
        
        pass
    
    async def _update_message_status(self, status_data: Dict[str, Any]) -> None:
        """Update message status in database."""
        # TODO: Implement status update
        # This would involve:
        # 1. Finding message by ID
        # 2. Updating status and timestamps
        # 3. Logging status change
        
        pass
    
    async def _process_media_file(self, media_data: Dict[str, Any]) -> None:
        """Process media file (download, upload, etc.)."""
        # TODO: Implement media processing
        # This would involve:
        # 1. Downloading from source
        # 2. Uploading to MinIO/S3
        # 3. Updating message with media URL
        # 4. Uploading to Bitrix Disk if needed
        
        pass


# Global router instance
router = MessageRouter()


@broker.subscriber("msg.inbound.raw")
async def handle_inbound_raw(
    message: RabbitMessageAnnotation,
    ctx: Context[RabbitMessage]
) -> None:
    """Handle raw inbound messages from channels."""
    async with AsyncSessionLocal() as db:
        await router.initialize(db)
        
        try:
            message_data = json.loads(message.body.decode())
            await router.process_inbound_message(message_data)
        except Exception as e:
            logger.error(f"Failed to handle inbound raw message: {str(e)}")
            # TODO: Implement retry logic or send to DLQ


@broker.subscriber("msg.inbound.normalized")
async def handle_inbound_normalized(
    message: RabbitMessageAnnotation,
    ctx: Context[RabbitMessage]
) -> None:
    """Handle normalized inbound messages."""
    async with AsyncSessionLocal() as db:
        await router.initialize(db)
        
        try:
            message_data = json.loads(message.body.decode())
            await router.process_inbound_message(message_data)
        except Exception as e:
            logger.error(f"Failed to handle inbound normalized message: {str(e)}")


@broker.subscriber("msg.outbound.to_channel")
async def handle_outbound_to_channel(
    message: RabbitMessageAnnotation,
    ctx: Context[RabbitMessage]
) -> None:
    """Handle outbound messages to channels."""
    async with AsyncSessionLocal() as db:
        await router.initialize(db)
        
        try:
            message_data = json.loads(message.body.decode())
            await router.process_outbound_message(message_data)
        except Exception as e:
            logger.error(f"Failed to handle outbound message: {str(e)}")


@broker.subscriber("msg.status.update")
async def handle_status_update(
    message: RabbitMessageAnnotation,
    ctx: Context[RabbitMessage]
) -> None:
    """Handle message status updates."""
    async with AsyncSessionLocal() as db:
        await router.initialize(db)
        
        try:
            status_data = json.loads(message.body.decode())
            await router.process_status_update(status_data)
        except Exception as e:
            logger.error(f"Failed to handle status update: {str(e)}")


@broker.subscriber("msg.media.process")
async def handle_media_process(
    message: RabbitMessageAnnotation,
    ctx: Context[RabbitMessage]
) -> None:
    """Handle media processing."""
    async with AsyncSessionLocal() as db:
        await router.initialize(db)
        
        try:
            media_data = json.loads(message.body.decode())
            await router.process_media(media_data)
        except Exception as e:
            logger.error(f"Failed to handle media processing: {str(e)}")


if __name__ == "__main__":
    # Run the FastStream application
    asyncio.run(app.run())
