#!/bin/bash

# Run script for Bitrix24 Messenger Connector application

set -e

echo "🚀 Starting Bitrix24 Messenger Connector..."

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
    print_warning ".env file not found. Creating from template..."
    if [ -f "env.local.example" ]; then
        cp env.local.example .env
        print_success "Created .env file from env.local.example"
        print_warning "Please edit .env file with your configuration before running again."
        exit 1
    else
        print_error "No .env template found. Please create .env file manually."
        exit 1
    fi
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is not installed. Please install Poetry first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d ".venv" ] && [ ! -d "$HOME/.cache/pypoetry/virtualenvs" ]; then
    print_status "Installing dependencies with Poetry..."
    poetry install
    print_success "Dependencies installed successfully"
fi

# Check local services
print_status "Checking local services..."

# Check PostgreSQL
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    print_error "PostgreSQL is not running on localhost:5432"
    print_warning "Please start PostgreSQL: sudo systemctl start postgresql"
    exit 1
fi

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    print_error "Redis is not running on localhost:6379"
    print_warning "Please start Redis: sudo systemctl start redis-server"
    exit 1
fi

# Check RabbitMQ
if ! curl -s http://localhost:15672 > /dev/null 2>&1; then
    print_error "RabbitMQ is not running on localhost:5672"
    print_warning "Please start RabbitMQ: sudo systemctl start rabbitmq-server"
    exit 1
fi

print_success "All local services are running"

# Check if database exists and run migrations
print_status "Checking database and running migrations..."

# Try to connect to database and run migrations
if poetry run alembic current > /dev/null 2>&1; then
    print_status "Running database migrations..."
    poetry run alembic upgrade head
    print_success "Database migrations completed"
else
    print_warning "Database not initialized. Please run setup script first:"
    echo "  ./scripts/setup-local-db.sh"
    exit 1
fi

# Kill any existing uvicorn processes
print_status "Stopping any existing application instances..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 2

# Check if port 8000 is free
if lsof -ti:8000 > /dev/null 2>&1; then
    print_warning "Port 8000 is still in use. Trying to free it..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the application
print_status "Starting FastAPI application..."
print_success "Application will be available at:"
echo "  🌐 API: http://localhost:8000"
echo "  📚 Docs: http://localhost:8000/docs"
echo "  🎛️  Admin: http://localhost:8000/api/v1/admin/"
echo "  ❤️  Health: http://localhost:8000/health"
echo ""
print_status "Press Ctrl+C to stop the application"
echo ""

# Start the application with auto-reload
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
