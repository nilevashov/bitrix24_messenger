"""Application configuration using Pydantic Settings."""

from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    url: str = Field(default="postgresql+asyncpg://user:password@localhost:5432/bitrix_messenger")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    
    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    """Redis configuration."""
    
    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = Field(default=10)
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")


class RabbitMQSettings(BaseSettings):
    """RabbitMQ configuration."""
    
    url: str = Field(default="amqp://guest:guest@localhost:5672/")
    exchange: str = Field(default="bitrix_messenger")
    
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")


class MinIOSettings(BaseSettings):
    """MinIO/S3 configuration."""
    
    endpoint: str = Field(default="localhost:9000")
    access_key: str = Field(default="minioadmin")
    secret_key: str = Field(default="minioadmin")
    bucket: str = Field(default="bitrix-messenger")
    secure: bool = Field(default=False)
    
    model_config = SettingsConfigDict(env_prefix="MINIO_")


class SecuritySettings(BaseSettings):
    """Security configuration."""
    
    secret_key: str = Field(default="your-secret-key-change-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # JWT settings
    jwt_private_key: Optional[str] = Field(default=None)
    jwt_public_key: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class TelegramSettings(BaseSettings):
    """Telegram Bot configuration."""
    
    webhook_url: Optional[str] = Field(default=None)
    webhook_secret: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")


class WhatsAppSettings(BaseSettings):
    """WhatsApp configuration."""
    
    provider: str = Field(default="cloud_api")  # cloud_api, twilio, custom
    webhook_verify_token: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(env_prefix="WHATSAPP_")


class BitrixSettings(BaseSettings):
    """Bitrix24 configuration."""
    
    webhook_url: Optional[str] = Field(default=None)
    webhook_secret: Optional[str] = Field(default=None)
    
    model_config = SettingsConfigDict(env_prefix="BITRIX_")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    
    sentry_dsn: Optional[str] = Field(default=None)
    prometheus_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    
    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    
    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/api/v1")
    
    # CORS
    cors_origins: str = Field(default="http://localhost:3000")
    
    # Components
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    whatsapp: WhatsAppSettings = Field(default_factory=WhatsAppSettings)
    bitrix: BitrixSettings = Field(default_factory=BitrixSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()

