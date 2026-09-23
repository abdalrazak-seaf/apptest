"""Application settings. Every value comes from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads .env from the current dir or the repo root (apps run from apps/<name>).
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "[APP_NAME]"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://thiqa:thiqa@localhost:5432/thiqa"
    redis_url: str = "redis://localhost:6379/0"

    storage_provider: Literal["s3", "memory"] = "s3"
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: SecretStr = SecretStr("minioadmin")
    s3_bucket_media: str = "thiqa-media"

    # Seconds allowed for each dependency check in /health/ready.
    health_check_timeout_s: float = Field(default=2.0, gt=0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
