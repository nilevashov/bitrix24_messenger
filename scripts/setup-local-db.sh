#!/bin/bash

# Setup script for local PostgreSQL database

set -e

echo "Setting up local PostgreSQL database for Bitrix24 Messenger Connector..."

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "Error: PostgreSQL is not running. Please start PostgreSQL and try again."
    exit 1
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql is not installed. Please install PostgreSQL client tools."
    exit 1
fi

# Create database
echo "Creating database 'bitrix_messenger'..."
createdb -U postgres bitrix_messenger 2>/dev/null || echo "Database 'bitrix_messenger' already exists"

# Create user
echo "Creating user 'user'..."
psql -U postgres -c "CREATE USER \"user\" WITH PASSWORD 'password';" 2>/dev/null || echo "User 'user' already exists"

# Grant privileges
echo "Granting privileges..."
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE bitrix_messenger TO \"user\";"
psql -U postgres -c "ALTER USER \"user\" CREATEDB;"

# Create extensions
echo "Creating extensions..."
psql -U postgres -d bitrix_messenger -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -U postgres -d bitrix_messenger -c "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"

echo "Database setup completed successfully!"
echo ""
echo "Database connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: bitrix_messenger"
echo "  User: user"
echo "  Password: password"
echo ""
echo "You can now run the application with: ./scripts/start-local.sh"
