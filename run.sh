#!/bin/bash

# Quick run script for Bitrix24 Messenger Connector

echo "🚀 Quick Start - Bitrix24 Messenger Connector"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found."
    if [ -f "env.local.example" ]; then
        echo "📝 Creating .env from template..."
        cp env.local.example .env
        echo "✅ Created .env file. Please edit it with your configuration."
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ Error: No .env template found. Please create .env file manually."
        exit 1
    fi
fi

# Kill any existing processes
echo "🛑 Stopping any existing processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1

# Start the application
echo "🚀 Starting application..."
echo ""
echo "📱 Access points:"
echo "   🌐 API: http://localhost:8000"
echo "   📚 Docs: http://localhost:8000/docs"
echo "   🎛️  Admin: http://localhost:8000/api/v1/admin/"
echo "   ❤️  Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the application
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
