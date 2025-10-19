#!/bin/bash

# Bitrix24-Telegram Integration Setup Script
# This script helps you set up the complete integration

set -e

echo "🚀 Bitrix24-Telegram Integration Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_info "Starting integration setup..."

# Step 1: Check environment variables
echo ""
echo "📋 Step 1: Environment Variables"
echo "================================"

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    print_warning "TELEGRAM_BOT_TOKEN not set"
    read -p "Enter your Telegram bot token: " TELEGRAM_BOT_TOKEN
    export TELEGRAM_BOT_TOKEN
fi

if [ -z "$BITRIX_DOMAIN" ]; then
    print_warning "BITRIX_DOMAIN not set"
    read -p "Enter your Bitrix24 domain (e.g., your-portal.bitrix24.com): " BITRIX_DOMAIN
    export BITRIX_DOMAIN
fi

if [ -z "$BITRIX_APP_ID" ]; then
    print_warning "BITRIX_APP_ID not set"
    read -p "Enter your Bitrix24 application ID: " BITRIX_APP_ID
    export BITRIX_APP_ID
fi

if [ -z "$BITRIX_APP_SECRET" ]; then
    print_warning "BITRIX_APP_SECRET not set"
    read -p "Enter your Bitrix24 application secret: " BITRIX_APP_SECRET
    export BITRIX_APP_SECRET
fi

if [ -z "$WEBHOOK_URL" ]; then
    print_warning "WEBHOOK_URL not set"
    read -p "Enter your webhook URL (e.g., https://yourdomain.com/api/v1/webhooks): " WEBHOOK_URL
    export WEBHOOK_URL
fi

print_status "Environment variables configured"

# Step 2: Setup Telegram webhook
echo ""
echo "🤖 Step 2: Telegram Bot Setup"
echo "============================="

print_info "Setting up Telegram webhook..."
python3 scripts/setup-telegram-webhook.py

if [ $? -eq 0 ]; then
    print_status "Telegram webhook setup completed"
else
    print_error "Failed to setup Telegram webhook"
    exit 1
fi

# Step 3: Setup Bitrix24 webhook
echo ""
echo "🏢 Step 3: Bitrix24 Setup"
echo "========================="

print_info "Setting up Bitrix24 webhook..."
python3 scripts/setup-bitrix-webhook.py

if [ $? -eq 0 ]; then
    print_status "Bitrix24 webhook setup completed"
else
    print_error "Failed to setup Bitrix24 webhook"
    exit 1
fi

# Step 4: Test integration
echo ""
echo "🧪 Step 4: Integration Testing"
echo "=============================="

print_info "Running integration tests..."
python3 scripts/test-integration.py

if [ $? -eq 0 ]; then
    print_status "Integration tests passed"
else
    print_warning "Some integration tests failed - check the output above"
fi

# Step 5: Start the application
echo ""
echo "🚀 Step 5: Starting Application"
echo "==============================="

print_info "Starting the Bitrix24-Telegram connector..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    print_info "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
print_info "Starting application server..."
print_warning "The application will start in the background"
print_info "Access the admin panel at: http://localhost:8000/admin"
print_info "Default credentials: admin / admin123"

# Start the application in background
nohup python3 -m app.main > logs/app.log 2>&1 &
echo $! > logs/app.pid

print_status "Application started successfully!"
print_info "PID: $(cat logs/app.pid)"
print_info "Logs: tail -f logs/app.log"

# Final instructions
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
print_info "Next steps:"
echo "1. Open http://localhost:8000/admin in your browser"
echo "2. Login with admin / admin123"
echo "3. Go to Channels tab and add your Telegram channel"
echo "4. Go to Bitrix24 tab and configure your portal settings"
echo "5. Test the integration by sending a message to your bot"
echo ""
print_info "Useful commands:"
echo "- View logs: tail -f logs/app.log"
echo "- Stop app: kill \$(cat logs/app.pid)"
echo "- Test integration: python3 scripts/test-integration.py"
echo ""
print_status "Integration setup completed successfully! 🚀"
