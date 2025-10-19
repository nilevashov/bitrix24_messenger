# Scripts Documentation

This document describes all available scripts for running the Bitrix24 Messenger Connector.

## Quick Start Scripts

### `./run.sh` - Quick Application Start
The simplest way to start the application.

```bash
./run.sh
```

**What it does:**
- Checks for .env file (creates from template if missing)
- Stops any existing processes
- Starts FastAPI application with auto-reload
- Shows access URLs

**Use when:** You want to quickly start just the API application.

## Setup Scripts

### `./scripts/setup-local-db.sh` - Database Setup
Sets up the local PostgreSQL database.

```bash
./scripts/setup-local-db.sh
```

**What it does:**
- Creates `bitrix_messenger` database
- Creates `user` with password `password`
- Grants necessary privileges
- Creates required extensions (uuid-ossp, pgcrypto)

**Use when:** First time setup or when you need to recreate the database.

## Application Scripts

### `./scripts/run-app.sh` - Start FastAPI Application
Starts the main FastAPI application with full checks.

```bash
./scripts/run-app.sh
```

**What it does:**
- Checks all local services (PostgreSQL, Redis, RabbitMQ)
- Runs database migrations
- Starts FastAPI application with auto-reload
- Provides colored output and status messages

**Use when:** You want to start the API with full service validation.

### `./scripts/run-router.sh` - Start FastStream Router
Starts the FastStream message router worker.

```bash
./scripts/run-router.sh
```

**What it does:**
- Checks required services (PostgreSQL, RabbitMQ)
- Starts FastStream router worker
- Processes messages from RabbitMQ queues

**Use when:** You want to start the message processing worker.

## Service Management Scripts

### `./scripts/start-all.sh` - Complete Service Management
Manages all services with advanced features.

```bash
# Start all services
./scripts/start-all.sh start

# Stop all services
./scripts/start-all.sh stop

# Restart all services
./scripts/start-all.sh restart

# Check service status
./scripts/start-all.sh status

# View logs
./scripts/start-all.sh logs app
./scripts/start-all.sh logs router
```

**What it does:**
- Starts/stops app and router services in background
- Manages process IDs and logs
- Provides service status monitoring
- Logs are saved to `logs/` directory

**Use when:** You want full control over all services with background execution.

## Docker Scripts

### `./scripts/start.sh` - Full Docker Setup
Starts all services in Docker containers.

```bash
./scripts/start.sh
```

**What it does:**
- Starts PostgreSQL, Redis, RabbitMQ, MinIO in Docker
- Runs database migrations
- Starts application and router in Docker
- Includes monitoring services (Prometheus, Grafana)

**Use when:** You want to run everything in Docker without local services.

### `./scripts/start-local.sh` - Docker with Local Services
Starts only application in Docker, uses local services.

```bash
./scripts/start-local.sh
```

**What it does:**
- Uses your local PostgreSQL, Redis, RabbitMQ
- Starts only application and router in Docker
- Connects to local services via `host.docker.internal`

**Use when:** You have local services but want to run the app in Docker.

### `./scripts/stop.sh` - Stop Docker Services
Stops all Docker services.

```bash
./scripts/stop.sh
```

## Script Features

### Color-coded Output
All scripts use colored output for better readability:
- 🔵 **Blue**: Information messages
- 🟢 **Green**: Success messages  
- 🟡 **Yellow**: Warning messages
- 🔴 **Red**: Error messages

### Service Health Checks
Scripts automatically check:
- PostgreSQL connectivity
- Redis connectivity
- RabbitMQ connectivity
- Port availability
- Process status

### Log Management
- Background services log to `logs/` directory
- Process IDs saved for management
- Real-time log viewing with `start-all.sh logs`

### Error Handling
- Graceful error messages
- Service dependency validation
- Automatic cleanup on failure

## Recommended Workflows

### Development Workflow
```bash
# 1. One-time setup
./scripts/setup-local-db.sh

# 2. Daily development
./run.sh
```

### Production-like Testing
```bash
# 1. Start all services in background
./scripts/start-all.sh start

# 2. Monitor services
./scripts/start-all.sh status

# 3. View logs
./scripts/start-all.sh logs app

# 4. Stop when done
./scripts/start-all.sh stop
```

### Docker Development
```bash
# 1. Full Docker environment
./scripts/start.sh

# 2. Or Docker app with local services
./scripts/start-local.sh
```

## Troubleshooting

### Port Already in Use
```bash
# Kill processes on port 8000
lsof -ti:8000 | xargs kill -9

# Or use the scripts which handle this automatically
```

### Service Not Starting
```bash
# Check service status
./scripts/start-all.sh status

# View logs for errors
./scripts/start-all.sh logs app
./scripts/start-all.sh logs router
```

### Database Issues
```bash
# Recreate database
./scripts/setup-local-db.sh

# Check PostgreSQL is running
systemctl status postgresql
```

### Missing Dependencies
```bash
# Install Poetry dependencies
poetry install

# Check Poetry is installed
poetry --version
```
