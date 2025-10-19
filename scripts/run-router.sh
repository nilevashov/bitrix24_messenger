#!/bin/bash

# Run script for FastStream Router Worker

set -e

echo "🔄 Starting FastStream Router Worker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it first."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is not installed. Please install Poetry first."
    exit 1
fi

# Check local services
print_status "Checking local services..."

# Check PostgreSQL
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    print_error "PostgreSQL is not running on localhost:5432"
    exit 1
fi

# Check RabbitMQ
if ! curl -s http://localhost:15672 > /dev/null 2>&1; then
    print_error "RabbitMQ is not running on localhost:5672"
    exit 1
fi

print_success "All required services are running"

# Kill any existing router processes
print_status "Stopping any existing router instances..."
pkill -f "python -m app.workers.router" 2>/dev/null || true
sleep 2

# Start the router
print_status "Starting FastStream Router Worker..."
print_success "Router will process messages from RabbitMQ queues"
echo ""
print_status "Press Ctrl+C to stop the router"
echo ""

# Start the router
poetry run python -m app.workers.router
