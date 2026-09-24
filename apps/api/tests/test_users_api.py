"""Profile, role switching, and the PDPL export/delete endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enums import Language, UserRole
from api.models.geo import City
from api.models.user import User
from api.testing import AuthHeaders, UserFactory


class TestProfile:
    async def test_returns_the_signed_in_user(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user(name="عبدالله")
        response = await client.get("/users/me", headers=auth_headers(user))
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "عبدالله"
        assert body["phone"] == user.phone, "your own phone is visible to you"

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        assert (await client.get("/users/me")).status_code == 401

    async def test_updates_name_language_and_city(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        user: User = await make_user()
        response = await client.patch(
            "/users/me",
            headers=auth_headers(user),
            json={"name": "سارة", "preferred_language": "en", "city_id": str(city.id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "سارة"
        assert body["preferred_language"] == Language.EN
        assert body["city_id"] == str(city.id)

    async def test_rejects_an_unreasonably_short_name(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user()
        response = await client.patch("/users/me", headers=auth_headers(user), json={"name": "a"})
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    async def test_a_partial_update_leaves_other_fields_alone(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user(name="خالد")
        response = await client.patch(
            "/users/me", headers=auth_headers(user), json={"preferred_language": "en"}
        )
        assert response.json()["name"] == "خالد"


class TestRoles:
    async def test_a_buyer_can_become_a_seller(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user()
        response = await client.put(
            "/users/me/role", headers=auth_headers(user), json={"role": "seller"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.SELLER

    @pytest.mark.parametrize("role", ["admin", "showroom_staff"])
    async def test_privileged_roles_cannot_be_self_assigned(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, role: str
    ) -> None:
        user: User = await make_user()
        response = await client.put(
            "/users/me/role", headers=auth_headers(user), json={"role": role}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "role_not_self_assignable"

    async def test_an_unknown_role_is_rejected(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user()
        response = await client.put(
            "/users/me/role", headers=auth_headers(user), json={"role": "superuser"}
        )
        assert response.status_code == 422


class TestPublicProfile:
    async def test_never_exposes_the_phone_number(
        self, client: AsyncClient, make_user: UserFactory
    ) -> None:
        other: User = await make_user(name="بائع")
        response = await client.get(f"/users/{other.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "بائع"
        assert "phone" not in body
        assert other.phone not in response.text

    async def test_is_readable_without_signing_in(
        self, client: AsyncClient, make_user: UserFactory
    ) -> None:
        other: User = await make_user()
        assert (await client.get(f"/users/{other.id}")).status_code == 200

    async def test_unknown_user_is_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/users/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert response.json()["code"] == "user_not_found"


class TestPdpl:
    async def test_export_contains_the_users_own_data(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user(name="فيصل")
        response = await client.get("/users/me/export", headers=auth_headers(user))
        assert response.status_code == 200
        body = response.json()
        assert body["profile"]["phone"] == user.phone
        assert body["profile"]["name"] == "فيصل"
        assert "login_sessions" in body

    async def test_export_requires_authentication(self, client: AsyncClient) -> None:
        assert (await client.get("/users/me/export")).status_code == 401

    async def test_delete_erases_personal_details_and_blocks_login(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        session: AsyncSession,
    ) -> None:
        user: User = await make_user(name="نورة")
        original_phone = user.phone

        response = await client.delete("/users/me", headers=auth_headers(user))
        assert response.status_code == 200

        await session.refresh(user)
        assert user.name is None
        assert user.phone != original_phone
        assert not user.is_active
        assert user.deleted_at is not None

        # The access token stops working immediately.
        assert (await client.get("/users/me", headers=auth_headers(user))).status_code == 401

    async def test_delete_requires_authentication(self, client: AsyncClient) -> None:
        assert (await client.delete("/users/me")).status_code == 401
