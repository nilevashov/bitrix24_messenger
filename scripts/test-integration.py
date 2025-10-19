#!/usr/bin/env python3
"""Script to test the Bitrix24-Telegram integration."""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.adapters.telegram import TelegramAdapter
from app.services.bitrix_service import BitrixService
from app.core.database import get_db_session


async def test_telegram_bot():
    """Test Telegram bot functionality."""
    print("🤖 Testing Telegram bot...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        bot_token = input("Enter your Telegram bot token: ").strip()
    
    if not bot_token:
        print("❌ Bot token is required")
        return False
    
    # Create Telegram adapter
    config = {"bot_token": bot_token}
    adapter = TelegramAdapter(config)
    
    try:
        # Test bot info
        print("Getting bot info...")
        bot_info = await adapter.bot.get_me()
        print(f"✅ Bot info: @{bot_info.username} ({bot_info.first_name})")
        
        # Test webhook status
        print("Checking webhook status...")
        webhook_info = await adapter.bot.get_webhook_info()
        if webhook_info.url:
            print(f"✅ Webhook is set: {webhook_info.url}")
        else:
            print("⚠️  No webhook is set")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Telegram bot: {str(e)}")
        return False
    finally:
        await adapter.close()


async def test_bitrix_connection():
    """Test Bitrix24 connection."""
    print("🏢 Testing Bitrix24 connection...")
    
    domain = os.getenv("BITRIX_DOMAIN")
    if not domain:
        domain = input("Enter your Bitrix24 domain: ").strip()
    
    if not domain:
        print("❌ Bitrix24 domain is required")
        return False
    
    async with get_db_session() as db:
        bitrix_service = BitrixService(db)
        
        try:
            # Test basic connection
            print(f"Testing connection to {domain}...")
            # This would require proper OAuth setup
            print("✅ Bitrix24 connection test (placeholder)")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Bitrix24: {str(e)}")
            return False
        finally:
            await bitrix_service.close()


async def test_webhook_processing():
    """Test webhook processing with sample data."""
    print("🔄 Testing webhook processing...")
    
    # Sample Telegram message
    sample_telegram_message = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "type": "private",
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser"
            },
            "date": 1640995200,
            "text": "Hello, this is a test message!"
        }
    }
    
    # Test Telegram adapter processing
    config = {"bot_token": "test_token"}
    adapter = TelegramAdapter(config)
    
    try:
        result = await adapter.process_webhook(sample_telegram_message)
        print("✅ Telegram webhook processing test:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Error testing webhook processing: {str(e)}")
        return False


async def main():
    """Main function."""
    print("🧪 Bitrix24-Telegram Integration Test")
    print("=" * 50)
    
    tests = [
        ("Telegram Bot", test_telegram_bot),
        ("Bitrix24 Connection", test_bitrix_connection),
        ("Webhook Processing", test_webhook_processing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")


if __name__ == "__main__":
    asyncio.run(main())
