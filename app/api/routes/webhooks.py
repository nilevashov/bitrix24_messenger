"""Webhook endpoints for receiving events from channels and Bitrix24."""

import hashlib
import hmac
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.config import settings
from ...api.schemas import WebhookEnvelope, WebhookResponse
from ...services.webhook_service import WebhookService
from ...services.message_service import MessageService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature using HMAC-SHA256."""
    if not secret:
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@router.post("/bitrix", response_model=WebhookResponse)
async def bitrix_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """Receive webhooks from Bitrix24."""
    # Get raw body
    body = await request.body()
    
    # Verify signature if configured
    if settings.bitrix.webhook_secret:
        signature = request.headers.get("X-Bitrix-Signature", "")
        if not verify_webhook_signature(body, signature, settings.bitrix.webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Process webhook
    webhook_service = WebhookService(db)
    try:
        # Extract webhook secret from headers
        webhook_secret = request.headers.get("X-Bitrix-Signature", "")
        event_id = await webhook_service.process_bitrix_webhook(payload, webhook_secret)
        return WebhookResponse(
            success=True,
            message="Webhook processed successfully",
            event_id=event_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/channels/{channel_type}", response_model=WebhookResponse)
async def channel_webhook(
    channel_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """Receive webhooks from messenger channels (Telegram, WhatsApp, etc.)."""
    # Get raw body
    body = await request.body()
    
    # Verify signature if configured
    signature = request.headers.get("X-Signature", "")
    webhook_secret = None
    
    if channel_type == "telegram" and settings.telegram.webhook_secret:
        webhook_secret = settings.telegram.webhook_secret
    elif channel_type == "whatsapp" and settings.whatsapp.webhook_verify_token:
        webhook_secret = settings.whatsapp.webhook_verify_token
    
    if webhook_secret and not verify_webhook_signature(body, signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Process webhook
    webhook_service = WebhookService(db)
    try:
        event_id = await webhook_service.process_channel_webhook(channel_type, payload)
        return WebhookResponse(
            success=True,
            message="Webhook processed successfully",
            event_id=event_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/messages/send")
async def send_message(
    message_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """Send message from CRM to channel (for custom scenarios)."""
    message_service = MessageService(db)
    try:
        message_id = await message_service.send_message(message_data)
        return WebhookResponse(
            success=True,
            message="Message sent successfully",
            event_id=message_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

