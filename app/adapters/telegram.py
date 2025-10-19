"""Telegram Bot API adapter."""

import httpx
import logging
from typing import Dict, Any, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .base import BaseChannelAdapter

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseChannelAdapter):
    """Telegram Bot API adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("bot_token")
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
        self.dispatcher = Dispatcher() if self.bot else None
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup message handlers."""
        if not self.dispatcher:
            return
        
        @self.dispatcher.message()
        async def handle_message(message: types.Message):
            """Handle incoming message."""
            try:
                # Process message
                normalized_message = await self.process_webhook({
                    "update_id": message.message_id,
                    "message": {
                        "message_id": message.message_id,
                        "from": {
                            "id": message.from_user.id,
                            "is_bot": message.from_user.is_bot,
                            "first_name": message.from_user.first_name,
                            "last_name": message.from_user.last_name,
                            "username": message.from_user.username,
                            "language_code": message.from_user.language_code
                        },
                        "chat": {
                            "id": message.chat.id,
                            "type": message.chat.type,
                            "title": getattr(message.chat, 'title', None),
                            "username": getattr(message.chat, 'username', None)
                        },
                        "date": message.date,
                        "text": message.text,
                        "photo": [{"file_id": photo.file_id} for photo in message.photo] if message.photo else None,
                        "document": {
                            "file_id": message.document.file_id,
                            "file_name": message.document.file_name,
                            "mime_type": message.document.mime_type
                        } if message.document else None
                    }
                })
                
                logger.info(f"Processed Telegram message: {normalized_message}")
                
            except Exception as e:
                logger.error(f"Failed to handle Telegram message: {str(e)}")
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str, 
        media_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send message to Telegram chat."""
        if not self.bot:
            raise ValueError("Bot not initialized")
        
        try:
            if media_url:
                # Send media with caption
                if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    message = await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=media_url,
                        caption=text,
                        **kwargs
                    )
                else:
                    message = await self.bot.send_document(
                        chat_id=chat_id,
                        document=media_url,
                        caption=text,
                        **kwargs
                    )
            else:
                # Send text message
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs
                )
            
            return {
                "success": True,
                "message_id": message.message_id,
                "chat_id": message.chat.id,
                "date": message.date
            }
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get chat information."""
        if not self.bot:
            raise ValueError("Bot not initialized")
        
        try:
            chat = await self.bot.get_chat(chat_id)
            return {
                "id": chat.id,
                "type": chat.type,
                "title": getattr(chat, 'title', None),
                "username": getattr(chat, 'username', None),
                "first_name": getattr(chat, 'first_name', None),
                "last_name": getattr(chat, 'last_name', None)
            }
        except Exception as e:
            logger.error(f"Failed to get Telegram chat info: {str(e)}")
            return {"error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook."""
        try:
            # Extract message data
            message_data = payload.get("message", {})
            if not message_data:
                return {"error": "No message in payload"}
            
            # Extract contact info
            from_user = message_data.get("from", {})
            chat = message_data.get("chat", {})
            
            contact_info = {
                "chat_id": str(chat.get("id")),
                "username": from_user.get("username"),
                "first_name": from_user.get("first_name"),
                "last_name": from_user.get("last_name"),
                "phone": None  # Telegram doesn't provide phone in messages
            }
            
            # Extract message content
            message_content = {
                "text": message_data.get("text"),
                "media_url": None,
                "media_type": None,
                "media_meta": {}
            }
            
            # Handle media
            if message_data.get("photo"):
                photo = message_data["photo"][-1]  # Get highest resolution
                message_content["media_url"] = f"https://api.telegram.org/file/bot{self.bot_token}/{photo['file_id']}"
                message_content["media_type"] = "photo"
                message_content["media_meta"] = {
                    "file_id": photo["file_id"],
                    "width": photo.get("width"),
                    "height": photo.get("height")
                }
            elif message_data.get("document"):
                doc = message_data["document"]
                message_content["media_url"] = f"https://api.telegram.org/file/bot{self.bot_token}/{doc['file_id']}"
                message_content["media_type"] = "document"
                message_content["media_meta"] = {
                    "file_id": doc["file_id"],
                    "file_name": doc.get("file_name"),
                    "mime_type": doc.get("mime_type"),
                    "file_size": doc.get("file_size")
                }
            
            # Create normalized message
            normalized_message = self.normalize_message(payload)
            normalized_message.update({
                "contact_info": contact_info,
                "message_content": message_content,
                "timestamp": message_data.get("date"),
                "external_msg_id": str(message_data.get("message_id"))
            })
            
            return normalized_message
            
        except Exception as e:
            logger.error(f"Failed to process Telegram webhook: {str(e)}")
            return {"error": str(e)}
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Setup webhook for receiving messages."""
        if not self.bot:
            raise ValueError("Bot not initialized")
        
        try:
            await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "edited_message", "channel_post", "edited_channel_post"]
            )
            logger.info(f"Telegram webhook set up: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Telegram webhook: {str(e)}")
            return False
    
    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        if not self.bot:
            raise ValueError("Bot not initialized")
        
        try:
            await self.bot.delete_webhook()
            logger.info("Telegram webhook deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Telegram webhook: {str(e)}")
            return False
    
    async def get_file_url(self, file_id: str) -> str:
        """Get file URL from Telegram."""
        if not self.bot:
            raise ValueError("Bot not initialized")
        
        try:
            file = await self.bot.get_file(file_id)
            return f"https://api.telegram.org/file/bot{self.bot_token}/{file.file_path}"
        except Exception as e:
            logger.error(f"Failed to get Telegram file URL: {str(e)}")
            raise
    
    async def close(self):
        """Close bot connection."""
        if self.bot:
            await self.bot.session.close()
