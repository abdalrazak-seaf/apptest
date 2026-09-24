"""Login flow: request a code, verify it, refresh, and log out."""

import re
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import Settings
from api.integrations.sms import MockSmsProvider
from api.models.enums import UserRole
from api.models.user import OtpRequest, RefreshToken, User
from api.testing import UserFactory

PHONE = "0501234567"
E164 = "+966501234567"


def sent_message(sms: MockSmsProvider, phone: str = E164) -> str:
    """The body of the last SMS sent to `phone`."""
    message = sms.last_for(phone)
    assert message is not None, f"no SMS was sent to {phone}"
    return message.message


def code_from(sms: MockSmsProvider, phone: str = E164) -> str:
    body = sent_message(sms, phone)
    match = re.search(r"\b(\d{6})\b", body)
    assert match, body
    return match.group(1)


async def login(client: AsyncClient, sms: MockSmsProvider, phone: str = PHONE) -> dict[str, Any]:
    request = await client.post("/auth/otp/request", json={"phone": phone})
    assert request.status_code == 200, request.text
    verify = await client.post(
        "/auth/otp/verify",
        json={"phone": phone, "code": code_from(sms, request.json()["phone"])},
    )
    assert verify.status_code == 200, verify.text
    tokens: dict[str, Any] = verify.json()
    return tokens


class TestRequestCode:
    async def test_sends_a_code_and_normalizes_the_number(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        response = await client.post("/auth/otp/request", json={"phone": "٠٥٠١٢٣٤٥٦٧"})
        assert response.status_code == 200
        assert response.json()["phone"] == E164
        assert response.json()["expires_in_s"] > 0
        assert sms.last_for(E164) is not None

    async def test_does_not_return_the_code_by_default(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        response = await client.post("/auth/otp/request", json={"phone": PHONE})
        assert response.json()["debug_code"] is None

    async def test_the_message_is_arabic_by_default_and_english_on_request(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        assert "رمز الدخول" in sent_message(sms)

        await client.post("/auth/otp/request", json={"phone": "0509999999", "language": "en"})
        assert "login code" in sent_message(sms, "+966509999999")

    async def test_rejects_a_number_that_is_not_a_saudi_mobile(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        response = await client.post("/auth/otp/request", json={"phone": "+971501234567"})
        assert response.status_code == 400
        assert response.json() == {"code": "phone_invalid"}
        assert sms.sent == []

    async def test_stores_the_code_hashed(
        self, client: AsyncClient, sms: MockSmsProvider, session: AsyncSession
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        otp = (await session.execute(select(OtpRequest))).scalars().one()
        assert otp.code_hash != code_from(sms)
        assert len(otp.code_hash) == 64

    async def test_a_new_code_invalidates_the_previous_one(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        first_code = code_from(sms)
        await client.post("/auth/otp/request", json={"phone": PHONE})

        response = await client.post("/auth/otp/verify", json={"phone": PHONE, "code": first_code})
        assert response.status_code == 401
        assert response.json()["code"] == "otp_invalid"

    async def test_rate_limits_repeated_requests_for_one_number(
        self, client: AsyncClient, settings: Settings
    ) -> None:
        for _ in range(settings.otp_requests_per_window):
            assert (
                await client.post("/auth/otp/request", json={"phone": PHONE})
            ).status_code == 200

        blocked = await client.post("/auth/otp/request", json={"phone": PHONE})
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "otp_rate_limited"
        assert int(blocked.headers["Retry-After"]) > 0


class TestVerifyCode:
    async def test_creates_the_account_on_first_login(
        self, client: AsyncClient, sms: MockSmsProvider, session: AsyncSession
    ) -> None:
        tokens = await login(client, sms)
        assert tokens["token_type"] == "bearer"
        assert tokens["user"]["phone"] == E164
        assert tokens["user"]["role"] == UserRole.BUYER
        assert tokens["user"]["preferred_language"] == "ar"

        user = (await session.execute(select(User).where(User.phone == E164))).scalar_one()
        assert user.last_login_at is not None

    async def test_signing_in_again_reuses_the_same_account(
        self, client: AsyncClient, sms: MockSmsProvider, session: AsyncSession
    ) -> None:
        first = await login(client, sms)
        second = await login(client, sms)
        assert first["user"]["id"] == second["user"]["id"]
        assert first["refresh_token"] != second["refresh_token"]

    async def test_rejects_a_wrong_code(self, client: AsyncClient, sms: MockSmsProvider) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        response = await client.post("/auth/otp/verify", json={"phone": PHONE, "code": "000000"})
        assert response.status_code == 401
        assert response.json() == {"code": "otp_invalid"}

    async def test_rejects_a_code_for_a_different_number(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        code = code_from(sms)
        await client.post("/auth/otp/request", json={"phone": "0509999999"})

        response = await client.post("/auth/otp/verify", json={"phone": "0509999999", "code": code})
        assert response.status_code == 401

    async def test_a_code_cannot_be_used_twice(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        code = code_from(sms)
        assert (
            await client.post("/auth/otp/verify", json={"phone": PHONE, "code": code})
        ).status_code == 200

        replay = await client.post("/auth/otp/verify", json={"phone": PHONE, "code": code})
        assert replay.status_code == 401

    async def test_gives_up_after_too_many_wrong_attempts(
        self, client: AsyncClient, sms: MockSmsProvider, settings: Settings
    ) -> None:
        await client.post("/auth/otp/request", json={"phone": PHONE})
        code = code_from(sms)
        for _ in range(settings.otp_max_attempts):
            await client.post("/auth/otp/verify", json={"phone": PHONE, "code": "999999"})

        response = await client.post("/auth/otp/verify", json={"phone": PHONE, "code": code})
        assert response.status_code == 401, "the correct code must stop working too"

    async def test_rejects_a_code_when_none_was_requested(self, client: AsyncClient) -> None:
        response = await client.post("/auth/otp/verify", json={"phone": PHONE, "code": "123456"})
        assert response.status_code == 401

    async def test_a_disabled_account_cannot_log_in(
        self,
        client: AsyncClient,
        sms: MockSmsProvider,
        session: AsyncSession,
        make_user: UserFactory,
    ) -> None:
        user = await make_user(phone=E164)
        user.is_active = False
        await session.commit()

        await client.post("/auth/otp/request", json={"phone": PHONE})
        response = await client.post(
            "/auth/otp/verify", json={"phone": PHONE, "code": code_from(sms)}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "account_disabled"


class TestRefreshAndLogout:
    async def test_rotates_the_refresh_token(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        tokens = await login(client, sms)
        response = await client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        rotated = response.json()
        assert rotated["refresh_token"] != tokens["refresh_token"]
        assert rotated["user"]["id"] == tokens["user"]["id"]

    async def test_reusing_a_rotated_token_signs_the_user_out_everywhere(
        self, client: AsyncClient, sms: MockSmsProvider, session: AsyncSession
    ) -> None:
        tokens = await login(client, sms)
        rotated = (
            await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        ).json()

        replay = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert replay.status_code == 401
        assert replay.json()["code"] == "refresh_token_invalid"

        # The token issued by the replayed rotation is revoked as well.
        after = await client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
        assert after.status_code == 401

        stored = (await session.execute(select(RefreshToken))).scalars().all()
        assert all(token.revoked_at is not None for token in stored)

    async def test_rejects_an_unknown_refresh_token(self, client: AsyncClient) -> None:
        response = await client.post("/auth/refresh", json={"refresh_token": "x" * 40})
        assert response.status_code == 401

    async def test_logout_revokes_only_that_device(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        first = await login(client, sms)
        second = await login(client, sms)

        assert (
            await client.post("/auth/logout", json={"refresh_token": first["refresh_token"]})
        ).status_code == 200

        assert (
            await client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        ).status_code == 401
        assert (
            await client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
        ).status_code == 200

    async def test_logout_all_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post("/auth/logout-all")
        assert response.status_code == 401
        assert response.json()["code"] == "not_authenticated"

    async def test_logout_all_revokes_every_device(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        first = await login(client, sms)
        second = await login(client, sms)

        response = await client.post(
            "/auth/logout-all", headers={"Authorization": f"Bearer {second['access_token']}"}
        )
        assert response.status_code == 200

        for tokens in (first, second):
            assert (
                await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            ).status_code == 401


class TestAccessTokens:
    async def test_a_valid_token_identifies_the_user(
        self, client: AsyncClient, sms: MockSmsProvider
    ) -> None:
        tokens = await login(client, sms)
        response = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == tokens["user"]["id"]

    @pytest.mark.parametrize(
        "header",
        [
            {"Authorization": "Bearer not-a-token"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic abc"},
        ],
    )
    async def test_a_bad_authorization_header_is_rejected(
        self, client: AsyncClient, header: dict[str, str]
    ) -> None:
        assert (await client.get("/users/me", headers=header)).status_code == 401
