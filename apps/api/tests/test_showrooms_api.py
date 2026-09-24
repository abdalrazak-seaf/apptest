"""Showroom registration and staff management, including authorization failures."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enums import ShowroomStaffRole, UserRole
from api.models.geo import City
from api.models.showroom import ShowroomStaff
from api.models.user import User
from api.testing import AuthHeaders, UserFactory

CR = "1010101010"


async def create_showroom(
    client: AsyncClient, headers: dict[str, str], city: City, cr: str = CR
) -> dict[str, Any]:
    response = await client.post(
        "/showrooms",
        headers=headers,
        json={
            "name_ar": "معرض النخبة",
            "commercial_registration_number": cr,
            "city_id": str(city.id),
        },
    )
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


class TestRegistration:
    async def test_creates_a_showroom_and_makes_the_creator_its_owner(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        city: City,
        session: AsyncSession,
    ) -> None:
        user: User = await make_user()
        body = await create_showroom(client, auth_headers(user), city)

        assert body["name_ar"] == "معرض النخبة"
        assert body["verified"] is False, "verification is granted by an admin, not claimed"
        assert body["subscription_tier"] == "free"

        await session.refresh(user)
        assert user.role == UserRole.SHOWROOM_STAFF

        staff = (
            await client.get(f"/showrooms/{body['id']}/staff", headers=auth_headers(user))
        ).json()
        assert [s["role"] for s in staff] == [ShowroomStaffRole.OWNER]

    async def test_requires_authentication(self, client: AsyncClient, city: City) -> None:
        response = await client.post(
            "/showrooms",
            json={
                "name_ar": "معرض",
                "commercial_registration_number": CR,
                "city_id": str(city.id),
            },
        )
        assert response.status_code == 401

    async def test_normalizes_arabic_digits_in_the_registration_number(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        user: User = await make_user()
        body = await create_showroom(client, auth_headers(user), city, cr="١٠١٠١٠١٠١٠")
        stored = await client.get(f"/showrooms/{body['id']}")
        assert stored.status_code == 200

    async def test_rejects_a_malformed_registration_number(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        user: User = await make_user()
        response = await client.post(
            "/showrooms",
            headers=auth_headers(user),
            json={
                "name_ar": "معرض",
                "commercial_registration_number": "12345",
                "city_id": str(city.id),
            },
        )
        assert response.status_code == 422

    async def test_rejects_a_duplicate_registration_number(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        first: User = await make_user()
        await create_showroom(client, auth_headers(first), city)

        second: User = await make_user()
        response = await client.post(
            "/showrooms",
            headers=auth_headers(second),
            json={
                "name_ar": "معرض آخر",
                "commercial_registration_number": CR,
                "city_id": str(city.id),
            },
        )
        assert response.status_code == 409
        assert response.json()["code"] == "commercial_registration_taken"

    async def test_rejects_an_unknown_city(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        user: User = await make_user()
        response = await client.post(
            "/showrooms",
            headers=auth_headers(user),
            json={
                "name_ar": "معرض",
                "commercial_registration_number": CR,
                "city_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 404
        assert response.json()["code"] == "city_not_found"


class TestDetails:
    async def test_is_readable_without_signing_in(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        response = await client.get(f"/showrooms/{created['id']}")
        assert response.status_code == 200
        assert "commercial_registration_number" not in response.json()

    async def test_unknown_showroom_is_not_found(self, client: AsyncClient) -> None:
        response = await client.get(f"/showrooms/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["code"] == "showroom_not_found"

    async def test_the_owner_can_edit_it(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        response = await client.patch(
            f"/showrooms/{created['id']}",
            headers=auth_headers(owner),
            json={"name_ar": "معرض الصفوة"},
        )
        assert response.status_code == 200
        assert response.json()["name_ar"] == "معرض الصفوة"

    async def test_a_stranger_cannot_edit_it(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        stranger: User = await make_user()

        response = await client.patch(
            f"/showrooms/{created['id']}",
            headers=auth_headers(stranger),
            json={"name_ar": "استيلاء"},
        )
        assert response.status_code == 403

    async def test_an_agent_cannot_edit_it(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        city: City,
        session: AsyncSession,
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        agent: User = await make_user()
        session.add(
            ShowroomStaff(
                showroom_id=uuid.UUID(created["id"]),
                user_id=agent.id,
                role=ShowroomStaffRole.AGENT,
            )
        )
        await session.commit()

        response = await client.patch(
            f"/showrooms/{created['id']}",
            headers=auth_headers(agent),
            json={"name_ar": "تعديل"},
        )
        assert response.status_code == 403

    async def test_only_an_admin_can_verify(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)

        assert (
            await client.post(f"/showrooms/{created['id']}/verify", headers=auth_headers(owner))
        ).status_code == 403

        admin: User = await make_user(role=UserRole.ADMIN)
        response = await client.post(
            f"/showrooms/{created['id']}/verify", headers=auth_headers(admin)
        )
        assert response.status_code == 200
        assert response.json()["verified"] is True


class TestStaff:
    async def test_the_staff_list_is_private_to_the_showroom(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)

        assert (await client.get(f"/showrooms/{created['id']}/staff")).status_code == 401

        stranger: User = await make_user()
        assert (
            await client.get(f"/showrooms/{created['id']}/staff", headers=auth_headers(stranger))
        ).status_code == 403

    async def test_the_owner_adds_a_member_by_phone(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        city: City,
        session: AsyncSession,
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        member: User = await make_user(name="موظف")

        response = await client.post(
            f"/showrooms/{created['id']}/staff",
            headers=auth_headers(owner),
            json={"phone": member.phone, "role": "agent"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["role"] == ShowroomStaffRole.AGENT
        assert body["user"]["name"] == "موظف"
        assert "phone" not in body["user"], "staff lists never expose phone numbers"

        await session.refresh(member)
        assert member.role == UserRole.SHOWROOM_STAFF

    async def test_adding_an_unknown_phone_does_not_create_an_account(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        response = await client.post(
            f"/showrooms/{created['id']}/staff",
            headers=auth_headers(owner),
            json={"phone": "0509999999"},
        )
        assert response.status_code == 404
        assert response.json()["code"] == "user_not_found"

    async def test_the_same_person_cannot_be_added_twice(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        member: User = await make_user()
        payload = {"phone": member.phone}

        await client.post(
            f"/showrooms/{created['id']}/staff", headers=auth_headers(owner), json=payload
        )
        response = await client.post(
            f"/showrooms/{created['id']}/staff", headers=auth_headers(owner), json=payload
        )
        assert response.status_code == 409
        assert response.json()["code"] == "already_staff"

    async def test_an_agent_cannot_add_staff(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        agent: User = await make_user()
        await client.post(
            f"/showrooms/{created['id']}/staff",
            headers=auth_headers(owner),
            json={"phone": agent.phone, "role": "agent"},
        )
        other: User = await make_user()

        response = await client.post(
            f"/showrooms/{created['id']}/staff",
            headers=auth_headers(agent),
            json={"phone": other.phone},
        )
        assert response.status_code == 403

    async def test_the_owner_removes_a_member(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders, city: City
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        member: User = await make_user()
        added = (
            await client.post(
                f"/showrooms/{created['id']}/staff",
                headers=auth_headers(owner),
                json={"phone": member.phone},
            )
        ).json()

        response = await client.delete(
            f"/showrooms/{created['id']}/staff/{added['id']}", headers=auth_headers(owner)
        )
        assert response.status_code == 200

        remaining = (
            await client.get(f"/showrooms/{created['id']}/staff", headers=auth_headers(owner))
        ).json()
        assert [s["id"] for s in remaining] == [
            s["id"] for s in remaining if s["role"] == ShowroomStaffRole.OWNER
        ]

    async def test_the_last_owner_cannot_be_removed(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        city: City,
        session: AsyncSession,
    ) -> None:
        owner: User = await make_user()
        created = await create_showroom(client, auth_headers(owner), city)
        staff = (
            await client.get(f"/showrooms/{created['id']}/staff", headers=auth_headers(owner))
        ).json()

        response = await client.delete(
            f"/showrooms/{created['id']}/staff/{staff[0]['id']}", headers=auth_headers(owner)
        )
        assert response.status_code == 409
        assert response.json()["code"] == "last_owner"

    async def test_removing_staff_from_another_showroom_is_not_found(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        city: City,
        session: AsyncSession,
    ) -> None:
        owner: User = await make_user()
        first = await create_showroom(client, auth_headers(owner), city)
        second = await create_showroom(client, auth_headers(owner), city, cr="2020202020")

        staff_of_first = (
            await client.get(f"/showrooms/{first['id']}/staff", headers=auth_headers(owner))
        ).json()

        response = await client.delete(
            f"/showrooms/{second['id']}/staff/{staff_of_first[0]['id']}",
            headers=auth_headers(owner),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "staff_not_found"
