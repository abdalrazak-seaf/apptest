import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from api.core.config import Settings
from api.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp_code,
    hash_refresh_token,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", jwt_secret="unit-test-secret-" + "a" * 32)


def test_access_token_round_trip(settings: Settings) -> None:
    user_id = uuid.uuid4()
    claims = decode_access_token(
        settings, create_access_token(settings, user_id=user_id, role="seller")
    )
    assert claims.user_id == user_id
    assert claims.role == "seller"


def test_rejects_a_token_signed_with_another_secret(settings: Settings) -> None:
    other = Settings(app_env="test", jwt_secret="different-secret-" + "b" * 32)
    token = create_access_token(other, user_id=uuid.uuid4(), role="buyer")
    with pytest.raises(InvalidTokenError):
        decode_access_token(settings, token)


def test_rejects_an_expired_token(settings: Settings) -> None:
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "buyer",
            "typ": "access",
            "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(settings, expired)


def test_rejects_a_token_of_the_wrong_type(settings: Settings) -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "buyer",
            "typ": "refresh",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(settings, token)


def test_none_algorithm_is_not_accepted(settings: Settings) -> None:
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "admin", "typ": "access", "exp": 9999999999},
        key="",
        algorithm="none",
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(settings, unsigned)


def test_otp_codes_are_numeric_and_the_requested_length() -> None:
    codes = {generate_otp_code(6) for _ in range(50)}
    assert all(len(c) == 6 and c.isdigit() for c in codes)
    assert len(codes) > 1, "codes must not be predictable"


def test_otp_hash_is_bound_to_the_phone_number(settings: Settings) -> None:
    same = hash_otp_code(settings, phone="+966500000001", code="123456")
    assert same == hash_otp_code(settings, phone="+966500000001", code="123456")
    assert same != hash_otp_code(settings, phone="+966500000002", code="123456")
    assert same != hash_otp_code(settings, phone="+966500000001", code="123457")


def test_refresh_tokens_are_unique_and_stored_hashed() -> None:
    tokens = {generate_refresh_token() for _ in range(20)}
    assert len(tokens) == 20
    token = tokens.pop()
    digest = hash_refresh_token(token)
    assert digest != token
    assert len(digest) == 64
