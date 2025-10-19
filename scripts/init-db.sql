-- Initialize database for Bitrix24 Messenger Connector

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database if not exists (this will be handled by Docker)
-- CREATE DATABASE bitrix_messenger;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE bitrix_messenger TO user;

