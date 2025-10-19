# Bitrix24 Messenger Connector

Omnichannel messenger connector for Bitrix24 with guaranteed delivery, CRM binding, queues, message history, and status tracking.

## Features

- **Multi-channel support**: Telegram Bot API, WhatsApp (via external providers)
- **Bitrix24 integration**: OpenLines connector and CRM timeline modes
- **Guaranteed delivery**: Message queues with retry logic and dead letter queues
- **CRM binding**: Automatic contact/lead/deal association
- **Media handling**: MinIO/S3 storage with Bitrix Disk integration
- **Multi-tenant**: Isolated data per tenant
- **Admin console**: Configuration and monitoring interface

## Architecture

```
Messengers ←→ Channel Adapters → Ingress API → Message Router → Bitrix Integration
     ↓              ↓              ↓              ↓              ↓
Object Storage ←→ PostgreSQL ←→ Redis Cache ←→ RabbitMQ ←→ Admin Console
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, FastStream
- **Database**: PostgreSQL with SQLAlchemy
- **Message Queue**: RabbitMQ
- **Cache**: Redis
- **Storage**: MinIO/S3
- **Monitoring**: Prometheus, Loki, Grafana, Sentry

## Quick Start

### Option 1: With Docker (All services in containers)

1. Clone the repository and navigate to the project directory:
```bash
cd bitrix24-messenger
```

2. Copy environment configuration:
```bash
cp env.example .env
# Edit .env with your configuration
```

3. Start all services:
```bash
./scripts/start.sh
```

This will:
- Start PostgreSQL, Redis, RabbitMQ, MinIO, and monitoring services
- Run database migrations
- Start the main application and message router

4. Access the services:
- **API Documentation**: http://localhost:8000/docs
- **Admin Console**: http://localhost:8000/api/v1/admin/
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

5. To stop services:
```bash
./scripts/stop.sh
```

### Option 2: With Local Services (Recommended for development)

If you have PostgreSQL, Redis, and RabbitMQ installed locally:

#### Quick Start (Recommended)
```bash
# 1. Setup database (one time only)
./scripts/setup-local-db.sh

# 2. Quick run application
./run.sh
```

#### Advanced Usage
```bash
# 1. Setup database (one time only)
./scripts/setup-local-db.sh

# 2. Copy environment configuration
cp env.local.example .env
# Edit .env with your configuration

# 3. Start application only
./scripts/run-app.sh

# 4. Start router worker (in another terminal)
./scripts/run-router.sh

# 5. Or start everything at once
./scripts/start-all.sh
```

#### Service Management
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

#### Access Points
- **API Documentation**: http://localhost:8000/docs
- **Admin Console**: http://localhost:8000/api/v1/admin/
- **Health Check**: http://localhost:8000/health
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

## Configuration

### Environment Variables

Key configuration options in `.env`:

- `DB_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `RABBITMQ_URL`: RabbitMQ connection string
- `MINIO_*`: MinIO/S3 configuration
- `SECURITY_SECRET_KEY`: JWT secret key
- `TELEGRAM_*`: Telegram Bot configuration
- `WHATSAPP_*`: WhatsApp provider configuration
- `BITRIX_*`: Bitrix24 webhook configuration

### Bitrix24 Setup

1. Create a Bitrix24 application in the marketplace
2. Configure OAuth redirect URL: `https://your-domain.com/api/v1/bitrix/install`
3. Set webhook URL: `https://your-domain.com/api/v1/webhooks/bitrix`
4. Configure webhook events for OpenLines and CRM

### Channel Setup

#### Telegram
1. Create a bot via @BotFather
2. Get bot token
3. Add channel in admin console
4. Configure webhook URL: `https://your-domain.com/api/v1/webhooks/channels/telegram`

#### WhatsApp
1. Choose provider (Cloud API, Twilio, or custom)
2. Configure provider credentials
3. Add channel in admin console
4. Set up webhook in provider dashboard

## Development

### Local Development

1. Install Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
2. Install dependencies: `poetry install`
3. Start services: `docker-compose up -d postgres redis rabbitmq minio`
4. Run migrations: `poetry run alembic upgrade head`
5. Start application: `poetry run uvicorn app.main:app --reload`

### Code Quality

- **Code formatting**: `poetry run black . && poetry run isort .`
- **Type checking**: `poetry run mypy .`
- **Testing**: `poetry run pytest`
- **Linting**: `poetry run flake8 .`

### Database Migrations

- **Create migration**: `poetry run alembic revision --autogenerate -m "description"`
- **Apply migrations**: `poetry run alembic upgrade head`
- **Rollback**: `poetry run alembic downgrade -1`

## API Endpoints

### Webhooks
- `POST /api/v1/webhooks/bitrix` - Bitrix24 webhooks
- `POST /api/v1/webhooks/channels/{type}` - Channel webhooks
- `POST /api/v1/messages/send` - Send message

### Admin
- `GET /api/v1/admin/` - Admin console
- `GET /api/v1/admin/stats` - Dashboard statistics
- `GET /api/v1/admin/channels` - List channels
- `POST /api/v1/admin/channels` - Create channel

### Bitrix24
- `POST /api/v1/bitrix/install` - OAuth installation
- `POST /api/v1/bitrix/refresh-token` - Refresh OAuth token
- `GET /api/v1/bitrix/status` - Integration status

## Monitoring

The system includes comprehensive monitoring:

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **Structured Logging**: JSON logs with correlation IDs
- **Health Checks**: Service health monitoring
- **Error Tracking**: Sentry integration (optional)

## Security

- **JWT Authentication**: RS256 with refresh tokens
- **RBAC**: Role-based access control
- **HMAC Verification**: Webhook signature validation
- **TLS**: All communications encrypted
- **GDPR Compliance**: PII encryption and data retention policies

## License

Private project - All rights reserved.

