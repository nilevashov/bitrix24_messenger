#!/usr/bin/env python3
"""Script to setup Telegram webhook for receiving messages."""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.adapters.telegram import TelegramAdapter
from app.core.config import settings


async def setup_telegram_webhook():
    """Setup Telegram webhook."""
    print("Setting up Telegram webhook...")
    
    # Get bot token from environment or prompt user
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        bot_token = input("Enter your Telegram bot token: ").strip()
    
    if not bot_token:
        print("Error: Bot token is required")
        return False
    
    # Get webhook URL (now tenant-agnostic)
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        webhook_url = input("Enter your webhook URL (e.g., https://yourdomain.com/api/v1/webhooks/channels/telegram): ").strip()
    
    if not webhook_url:
        print("Error: Webhook URL is required")
        return False
    
    print(f"ℹ️  Note: Webhook URL is now tenant-agnostic")
    print(f"   The system will automatically determine the tenant from the webhook content")
    
    # Create Telegram adapter
    config = {"bot_token": bot_token}
    adapter = TelegramAdapter(config)
    
    try:
        # Setup webhook
        success = await adapter.setup_webhook(webhook_url)
        
        if success:
            print(f"✅ Telegram webhook setup successfully!")
            print(f"Webhook URL: {webhook_url}")
            print(f"Bot token: {bot_token[:10]}...{bot_token[-4:]}")
            
            # Test webhook
            print("\nTesting webhook...")
            # You can add a test message here if needed
            
            return True
        else:
            print("❌ Failed to setup Telegram webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up webhook: {str(e)}")
        return False
    finally:
        await adapter.close()


async def delete_telegram_webhook():
    """Delete Telegram webhook."""
    print("Deleting Telegram webhook...")
    
    # Get bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        bot_token = input("Enter your Telegram bot token: ").strip()
    
    if not bot_token:
        print("Error: Bot token is required")
        return False
    
    # Create Telegram adapter
    config = {"bot_token": bot_token}
    adapter = TelegramAdapter(config)
    
    try:
        # Delete webhook
        success = await adapter.delete_webhook()
        
        if success:
            print("✅ Telegram webhook deleted successfully!")
            return True
        else:
            print("❌ Failed to delete Telegram webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting webhook: {str(e)}")
        return False
    finally:
        await adapter.close()


async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        await delete_telegram_webhook()
    else:
        await setup_telegram_webhook()


if __name__ == "__main__":
    asyncio.run(main())
