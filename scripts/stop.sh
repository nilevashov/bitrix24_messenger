#!/bin/bash

# Stop script for Bitrix24 Messenger Connector

set -e

echo "Stopping Bitrix24 Messenger Connector..."

# Stop services
docker-compose down

echo "Services stopped successfully!"
