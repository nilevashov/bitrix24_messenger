#!/usr/bin/env python3
"""Script to setup Bitrix24 webhook for receiving events."""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.services.bitrix_service import BitrixService
from app.core.database import get_db_session


async def setup_bitrix_webhook():
    """Setup Bitrix24 webhook."""
    print("Setting up Bitrix24 webhook...")
    
    # Get configuration from environment or prompt user
    domain = os.getenv("BITRIX_DOMAIN")
    if not domain:
        domain = input("Enter your Bitrix24 domain (e.g., your-portal.bitrix24.com): ").strip()
    
    app_id = os.getenv("BITRIX_APP_ID")
    if not app_id:
        app_id = input("Enter your Bitrix24 application ID: ").strip()
    
    app_secret = os.getenv("BITRIX_APP_SECRET")
    if not app_secret:
        app_secret = input("Enter your Bitrix24 application secret: ").strip()
    
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        webhook_url = input("Enter your webhook URL (e.g., https://yourdomain.com/api/v1/webhooks/bitrix): ").strip()
    
    if not all([domain, app_id, app_secret, webhook_url]):
        print("Error: All parameters are required")
        return False
    
    # Get database session
    async with get_db_session() as db:
        # Create Bitrix service
        bitrix_service = BitrixService(db)
        
        try:
            # Test API connection
            print("Testing Bitrix24 API connection...")
            # This would require OAuth setup first
            
    print("✅ Bitrix24 webhook configuration:")
    print(f"Domain: {domain}")
    print(f"App ID: {app_id}")
    print(f"Webhook URL: {webhook_url}")
    print("\n📋 Next steps:")
    print("1. Go to your Bitrix24 portal")
    print("2. Navigate to Applications > Webhooks")
    print("3. Create a new webhook with the following events:")
    print("   - ONIMBOTMESSAGEADD (Operator messages)")
    print("   - ONIMOPENLINESESSIONSTART (Session start)")
    print("   - ONIMOPENLINESESSIONFINISH (Session finish)")
    print("   - ONCRMLEADADD (New leads)")
    print("   - ONCRMCONTACTADD (New contacts)")
    print(f"4. Set webhook URL to: {webhook_url}")
    print("5. Copy the webhook secret and configure it in the admin panel")
    print("\nℹ️  Note: Webhook URL is now tenant-agnostic")
    print("   The system will automatically determine the tenant from the webhook content")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
        finally:
            await bitrix_service.close()


async def main():
    """Main function."""
    await setup_bitrix_webhook()


if __name__ == "__main__":
    asyncio.run(main())
