import pytest
from pydantic import ValidationError

from api.core.config import _DEV_JWT_SECRET, Settings


def test_local_defaults_are_usable() -> None:
    settings = Settings(app_env="local")
    assert settings.sms_provider == "mock"
    assert not settings.is_production


def test_production_refuses_the_development_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret=_DEV_JWT_SECRET)


def test_production_refuses_to_expose_otp_codes() -> None:
    with pytest.raises(ValidationError, match="OTP_EXPOSE_CODE"):
        Settings(app_env="production", jwt_secret="a-real-secret-" + "c" * 32, otp_expose_code=True)


def test_production_refuses_a_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(app_env="production", jwt_secret="short", sms_provider="mock")


def test_production_refuses_the_mock_sms_provider() -> None:
    with pytest.raises(ValidationError, match="SMS_PROVIDER"):
        Settings(app_env="production", jwt_secret="a-real-secret-" + "c" * 32, sms_provider="mock")
