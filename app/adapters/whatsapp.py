"""WhatsApp adapter with support for multiple providers."""

import httpx
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .base import BaseChannelAdapter

logger = logging.getLogger(__name__)


class WhatsAppProvider(ABC):
    """Base class for WhatsApp providers."""
    
    @abstractmethod
    async def send_message(
        self, 
        to: str, 
        text: str, 
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message via provider."""
        pass
    
    @abstractmethod
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook from provider."""
        pass


class CloudAPIProvider(WhatsAppProvider):
    """WhatsApp Cloud API provider."""
    
    def __init__(self, config: Dict[str, Any]):
        self.access_token = config.get("access_token")
        self.phone_number_id = config.get("phone_number_id")
        self.verify_token = config.get("verify_token")
        self.base_url = "https://graph.facebook.com/v18.0"
    
    async def send_message(
        self, 
        to: str, 
        text: str, 
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message via Cloud API."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        if media_url:
            # Send media message
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "image" if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif')) else "document",
                "image" if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif')) else "document": {
                    "link": media_url,
                    "caption": text
                }
            }
        else:
            # Send text message
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {
                    "body": text
                }
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to send WhatsApp message via Cloud API: {str(e)}")
                return {"error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Cloud API webhook."""
        try:
            # Extract message data
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return {"error": "No messages in payload"}
            
            message = messages[0]
            contacts = value.get("contacts", [{}])[0]
            
            # Extract contact info
            contact_info = {
                "chat_id": message.get("from"),
                "phone": message.get("from"),
                "username": None,
                "first_name": contacts.get("profile", {}).get("name"),
                "last_name": None
            }
            
            # Extract message content
            message_content = {
                "text": None,
                "media_url": None,
                "media_type": None,
                "media_meta": {}
            }
            
            # Handle different message types
            if "text" in message:
                message_content["text"] = message["text"]["body"]
            elif "image" in message:
                image = message["image"]
                message_content["media_url"] = image.get("link")
                message_content["media_type"] = "image"
                message_content["media_meta"] = {
                    "id": image.get("id"),
                    "mime_type": image.get("mime_type"),
                    "sha256": image.get("sha256")
                }
            elif "document" in message:
                doc = message["document"]
                message_content["media_url"] = doc.get("link")
                message_content["media_type"] = "document"
                message_content["media_meta"] = {
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "mime_type": doc.get("mime_type"),
                    "sha256": doc.get("sha256")
                }
            
            return {
                "contact_info": contact_info,
                "message_content": message_content,
                "timestamp": message.get("timestamp"),
                "external_msg_id": message.get("id")
            }
            
        except Exception as e:
            logger.error(f"Failed to process WhatsApp Cloud API webhook: {str(e)}")
            return {"error": str(e)}


class TwilioProvider(WhatsAppProvider):
    """Twilio WhatsApp provider."""
    
    def __init__(self, config: Dict[str, Any]):
        self.account_sid = config.get("account_sid")
        self.auth_token = config.get("auth_token")
        self.from_number = config.get("from_number")
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
    
    async def send_message(
        self, 
        to: str, 
        text: str, 
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message via Twilio."""
        url = f"{self.base_url}/Messages.json"
        auth = (self.account_sid, self.auth_token)
        
        data = {
            "From": f"whatsapp:{self.from_number}",
            "To": f"whatsapp:{to}",
            "Body": text
        }
        
        if media_url:
            data["MediaUrl"] = media_url
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, auth=auth)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to send WhatsApp message via Twilio: {str(e)}")
                return {"error": str(e)}
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Twilio webhook."""
        try:
            # Extract message data
            message_sid = payload.get("MessageSid")
            from_number = payload.get("From", "").replace("whatsapp:", "")
            to_number = payload.get("To", "").replace("whatsapp:", "")
            body = payload.get("Body", "")
            media_url = payload.get("MediaUrl0")
            
            # Extract contact info
            contact_info = {
                "chat_id": from_number,
                "phone": from_number,
                "username": None,
                "first_name": None,
                "last_name": None
            }
            
            # Extract message content
            message_content = {
                "text": body,
                "media_url": media_url,
                "media_type": "image" if media_url else None,
                "media_meta": {}
            }
            
            return {
                "contact_info": contact_info,
                "message_content": message_content,
                "timestamp": payload.get("DateCreated"),
                "external_msg_id": message_sid
            }
            
        except Exception as e:
            logger.error(f"Failed to process WhatsApp Twilio webhook: {str(e)}")
            return {"error": str(e)}


class WhatsAppAdapter(BaseChannelAdapter):
    """WhatsApp adapter with multiple provider support."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = config.get("provider", "cloud_api")
        self.provider = self._create_provider(config)
    
    def _create_provider(self, config: Dict[str, Any]) -> WhatsAppProvider:
        """Create provider instance based on configuration."""
        if self.provider_type == "cloud_api":
            return CloudAPIProvider(config)
        elif self.provider_type == "twilio":
            return TwilioProvider(config)
        else:
            raise ValueError(f"Unsupported WhatsApp provider: {self.provider_type}")
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str, 
        media_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send message to WhatsApp."""
        try:
            result = await self.provider.send_message(chat_id, text, media_url)
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id") if self.provider_type == "cloud_api" else result.get("sid"),
                "chat_id": chat_id
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get chat information."""
        # WhatsApp doesn't provide chat info API
        return {
            "id": chat_id,
            "type": "whatsapp",
            "phone": chat_id
        }
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook."""
        try:
            result = await self.provider.process_webhook(payload)
            
            if "error" in result:
                return {"error": result["error"]}
            
            # Create normalized message
            normalized_message = self.normalize_message(payload)
            normalized_message.update(result)
            
            return normalized_message
            
        except Exception as e:
            logger.error(f"Failed to process WhatsApp webhook: {str(e)}")
            return {"error": str(e)}
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Setup webhook for receiving messages."""
        # Webhook setup is typically done through provider's dashboard
        logger.info(f"WhatsApp webhook should be configured at: {webhook_url}")
        return True
    
    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        # Webhook deletion is typically done through provider's dashboard
        logger.info("WhatsApp webhook should be deleted through provider dashboard")
        return True
    
    def verify_webhook(self, payload: Dict[str, Any], verify_token: str) -> bool:
        """Verify webhook signature (for Cloud API)."""
        if self.provider_type != "cloud_api":
            return True
        
        hub_mode = payload.get("hub.mode")
        hub_verify_token = payload.get("hub.verify_token")
        hub_challenge = payload.get("hub.challenge")
        
        return hub_mode == "subscribe" and hub_verify_token == verify_token
