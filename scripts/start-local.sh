#!/bin/bash

# Start script for Bitrix24 Messenger Connector with local services

set -e

echo "Starting Bitrix24 Messenger Connector with local services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "Please edit .env file with your configuration before running again."
    exit 1
fi

# Check if local services are running
echo "Checking local services..."

# Check PostgreSQL
if ! pg_isready -h localhost -p 5432 -U user -d bitrix_messenger > /dev/null 2>&1; then
    echo "Warning: PostgreSQL is not running or not accessible at localhost:5432"
    echo "Please ensure PostgreSQL is running and create database 'bitrix_messenger' with user 'user'"
    echo "You can create the database with:"
    echo "  createdb -U postgres bitrix_messenger"
    echo "  psql -U postgres -c \"CREATE USER user WITH PASSWORD 'password';\""
    echo "  psql -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE bitrix_messenger TO user;\""
fi

# Check Redis
if ! redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
    echo "Warning: Redis is not running or not accessible at localhost:6379"
    echo "Please start Redis server"
fi

# Check RabbitMQ
if ! curl -s http://localhost:15672 > /dev/null 2>&1; then
    echo "Warning: RabbitMQ is not running or not accessible at localhost:5672"
    echo "Please start RabbitMQ server"
fi

# Start application services
echo "Starting application services..."
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Run database migrations
echo "Running database migrations..."
docker-compose -f docker-compose.local.yml exec app poetry run alembic upgrade head

echo "Application services started successfully!"
echo ""
echo "Access points:"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Admin Console: http://localhost:8000/api/v1/admin/"
echo ""
echo "Make sure your local services are running:"
echo "  - PostgreSQL: localhost:5432 (database: bitrix_messenger, user: user)"
echo "  - Redis: localhost:6379"
echo "  - RabbitMQ: localhost:5672 (Management UI: http://localhost:15672)"
echo ""
echo "To stop services, run: docker-compose -f docker-compose.local.yml down"
