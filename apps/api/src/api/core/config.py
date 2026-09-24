"""Application settings. Every value comes from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105 - placeholder, refused in production
# HS256 keys shorter than the hash output weaken the signature (RFC 7518 §3.2).
MIN_JWT_SECRET_BYTES = 32


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

    # --- Authentication -------------------------------------------------
    # Signs access and refresh tokens. Must be set to a strong random value outside local dev.
    jwt_secret: SecretStr = SecretStr(_DEV_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_ttl_s: int = Field(default=15 * 60, gt=0)
    refresh_token_ttl_s: int = Field(default=30 * 24 * 3600, gt=0)

    # True only when the app sits behind a proxy that overwrites X-Forwarded-For.
    # When false the header is ignored, so a client cannot spoof its IP to dodge rate limits.
    trust_proxy_headers: bool = False

    # --- OTP login ------------------------------------------------------
    sms_provider: Literal["mock"] = "mock"
    otp_length: int = Field(default=6, ge=4, le=8)
    otp_ttl_s: int = Field(default=5 * 60, gt=0)
    otp_max_attempts: int = Field(default=5, gt=0)
    # A phone may request this many codes per window; the same cap applies per client IP.
    otp_requests_per_window: int = Field(default=5, gt=0)
    otp_window_s: int = Field(default=3600, gt=0)
    # Local dev only: return the code in the API response so you can log in without SMS.
    otp_expose_code: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _refuse_insecure_production(self) -> "Settings":
        """Fail fast rather than run production with development credentials."""
        if not self.is_production:
            return self
        secret = self.jwt_secret.get_secret_value()
        if secret == _DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong random value in production")
        if len(secret.encode()) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes in production"
            )
        if self.otp_expose_code:
            raise ValueError("OTP_EXPOSE_CODE must be false in production")
        if self.sms_provider == "mock":
            raise ValueError("SMS_PROVIDER must not be the mock provider in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
