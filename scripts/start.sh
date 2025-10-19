#!/bin/bash

# Start script for Bitrix24 Messenger Connector

set -e

echo "Starting Bitrix24 Messenger Connector..."

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

# Start services
echo "Starting services with docker-compose..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "Running database migrations..."
docker-compose exec app poetry run alembic upgrade head

echo "Services started successfully!"
echo ""
echo "Access points:"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Admin Console: http://localhost:8000/api/v1/admin/"
echo "  - RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "To stop services, run: docker-compose down"
