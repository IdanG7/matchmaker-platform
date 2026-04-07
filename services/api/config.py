"""
Configuration management for the API service.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service
    service_name: str = "api"
    environment: str = "development"
    debug: bool = False

    # CORS allowed origins (comma-separated list, or "*" for any — only allowed in development)
    cors_allowed_origins: str = "*"

    # Server
    host: str = "0.0.0.0"  # nosec B104 - binding to all interfaces is intentional
    port: int = 8080

    # Database
    database_url: str = "postgresql://gameuser:gamepass@localhost:5432/gamedb"

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 50

    # NATS
    nats_url: str = "nats://localhost:4222"

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    # Fail-fast: refuse to run in production with the default JWT secret.
    if (
        settings.environment.lower() not in ("development", "dev", "test", "testing")
        and settings.jwt_secret_key == "your-secret-key-change-in-production"
    ):
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a strong, unique value outside of development"
        )
    return settings
