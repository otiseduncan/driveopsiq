"""
Application configuration settings.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Basic app settings
    app_name: str = "SyferStack Backend"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    
    # Security settings
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-12345678901234567890",
        description="Secret key for JWT token generation (override via SECRET_KEY)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiration in minutes")
    
    # Database settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./syferstack.db",
        description="Database connection URL",
    )
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Maximum overflow connections")
    database_pool_recycle: int = Field(default=300, description="Connection recycle seconds")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # CORS settings
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "https://app.syfernetics.com",
        ],
        description="Allowed CORS origins",
    )
    allowed_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="Allowed HTTP methods",
    )
    allowed_headers: list[str] = Field(
        default=["*"],
        description="Allowed headers",
    )
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1", "*.syfernetics.com", "*.syferstack.com"],
        description="Allowed hosts for TrustedHostMiddleware",
    )
    rate_limit_default: list[str] = Field(
        default=["100/minute"],
        description="Default rate limits applied per client",
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable or disable SlowAPI rate limiting",
    )
    
    # AI API settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    
    # Email settings (optional)
    smtp_host: Optional[str] = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_tls: bool = Field(default=True, description="Use TLS for SMTP")
    
    # File upload settings
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes (10MB)")
    upload_dir: str = Field(default="uploads", description="Upload directory")
    
    # Observability settings
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint instrumentation",
    )
    metrics_endpoint: str = Field(
        default="/metrics",
        description="Route path exposing Prometheus metrics",
    )
    
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: str | bool, _: ValidationInfo) -> bool:
        """Parse debug value from string or bool."""
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        """Parse allowed origins from comma-separated string or list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_hosts(cls, value: str | list[str]) -> list[str]:
        """Parse allowed hosts from comma-separated string or list."""
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value

    @field_validator("rate_limit_default", mode="before")
    @classmethod
    def parse_rate_limits(cls, value: str | list[str]) -> list[str]:
        """Parse rate limit strings from comma-separated string or list."""
        if isinstance(value, str):
            return [limit.strip() for limit in value.split(",") if limit.strip()]
        return value

    @field_validator("metrics_endpoint")
    @classmethod
    def normalize_metrics_endpoint(cls, value: str) -> str:
        """Ensure metrics endpoint path starts with a forward slash."""
        return value if value.startswith("/") else f"/{value}"
    
    @field_validator("upload_dir")
    @classmethod
    def normalize_upload_dir(cls, value: str) -> str:
        """Normalize upload directory path without forcing creation."""
        if "://" in value:
            return value
        return str(Path(value))
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or self.reload
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance
settings = get_settings()
