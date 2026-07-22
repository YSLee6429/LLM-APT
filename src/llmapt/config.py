"""Application configuration loaded from environment variables."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from llmapt import __version__


class Environment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    """Human-readable or machine-readable log output."""

    CONSOLE = "console"
    JSON = "json"


class Settings(BaseSettings):
    """Validated process settings.

    Secrets are intentionally absent from source defaults. Provider credentials will be
    introduced through dedicated secret references rather than serialized configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLMAPT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LLM-APT"
    app_version: str = __version__
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.CONSOLE

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    database_url: str = "postgresql+asyncpg://llmapt:llmapt@localhost:5432/llmapt"
    broker_url: str = "amqp://llmapt:llmapt@localhost:5672//"
    redis_url: str = "redis://localhost:6379/0"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "llmapt-artifacts"

    runner_url: str = "http://runner:8080"
    runner_token: SecretStr = SecretStr("local-runner-change-me")
    runner_timeout_seconds: float = Field(default=35.0, gt=0, le=120)
    auth_secret: SecretStr = SecretStr("local-auth-secret-change-me")
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: SecretStr = SecretStr("llmapt-local-change-me")
    bootstrap_admin_display_name: str = "Local Administrator"
    access_token_ttl_minutes: int = Field(default=480, ge=15, le=10_080)
    guest_token_ttl_minutes: int = Field(default=120, ge=15, le=1_440)

    external_model_calls_enabled: bool = False
    model_provider_key: str = "external"
    model_provider_name: str = "openai-compatible"
    model_name: str = ""
    model_revision: str | None = None
    model_api_endpoint: str = ""
    model_api_key: SecretStr | None = None
    model_timeout_seconds: float = Field(default=60.0, gt=0, le=600)

    request_id_header: str = "X-Request-ID"

    @model_validator(mode="after")
    def reject_insecure_production_secrets(self) -> Settings:
        if self.environment is not Environment.PRODUCTION:
            return self
        insecure = {
            "runner_token": "local-runner-change-me",
            "auth_secret": "local-auth-secret-change-me",
            "bootstrap_admin_password": "llmapt-local-change-me",
        }
        for field_name, default_value in insecure.items():
            value = getattr(self, field_name).get_secret_value()
            if value == default_value or len(value) < 16:
                raise ValueError(f"{field_name} must be replaced for production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""

    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings for tests and controlled process reconfiguration."""

    get_settings.cache_clear()
